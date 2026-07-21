#include "SpiffCoBridgeSubsystem.h"

#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "HttpPath.h"
#include "HttpServerModule.h"
#include "HttpServerRequest.h"
#include "HttpServerResponse.h"
#include "IHttpRouter.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "SpiffCoBridge.h"
#include "SpiffCoBridgeSettings.h"

namespace
{

TUniquePtr<FHttpServerResponse> JsonResponse(const int32 Code,
                                             const TSharedRef<FJsonObject>& Body)
{
    FString Payload;
    const auto Writer = TJsonWriterFactory<>::Create(&Payload);
    FJsonSerializer::Serialize(Body, Writer);
    TUniquePtr<FHttpServerResponse> Response =
        FHttpServerResponse::Create(Payload, TEXT("application/json"));
    Response->Code = static_cast<EHttpServerResponseCodes>(Code);
    return Response;
}

TUniquePtr<FHttpServerResponse> ErrorResponse(const int32 Code, const FString& Message)
{
    const TSharedRef<FJsonObject> Body = MakeShared<FJsonObject>();
    Body->SetStringField(TEXT("error"), Message);
    return JsonResponse(Code, Body);
}

FString HeaderValue(const FHttpServerRequest& Request, const FString& Name)
{
    for (const auto& Pair : Request.Headers)
    {
        if (Pair.Key.Equals(Name, ESearchCase::IgnoreCase) && Pair.Value.Num() > 0)
        {
            return Pair.Value[0];
        }
    }
    return FString();
}

} // namespace

void USpiffCoBridgeSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);

    const USpiffCoBridgeSettings* Settings = USpiffCoBridgeSettings::Get();
    if (!Settings->bEnabled)
    {
        return;
    }
    // Authority only: never open a command port on a connecting client.
    if (InWorld.GetNetMode() == NM_Client || !InWorld.IsGameWorld())
    {
        return;
    }
    if (Settings->AuthToken.IsEmpty())
    {
        UE_LOG(LogSpiffCoBridge, Warning,
               TEXT("SpiffCoBridge running WITHOUT an auth token — set AuthToken in "
                    "[/Script/SpiffCoBridge.SpiffCoBridgeSettings] unless this host is "
                    "on a fully trusted network"));
    }

    Router = FHttpServerModule::Get().GetHttpRouter(Settings->Port);
    if (!Router.IsValid())
    {
        UE_LOG(LogSpiffCoBridge, Error, TEXT("Could not bind HTTP router on port %d"),
               Settings->Port);
        return;
    }

    ExecuteRoute = Router->BindRoute(
        FHttpPath(TEXT("/execute")), EHttpServerRequestVerbs::VERB_POST,
        FHttpRequestHandler::CreateUObject(this, &USpiffCoBridgeSubsystem::HandleExecute));
    HealthRoute = Router->BindRoute(
        FHttpPath(TEXT("/health")), EHttpServerRequestVerbs::VERB_GET,
        FHttpRequestHandler::CreateUObject(this, &USpiffCoBridgeSubsystem::HandleHealth));

    FHttpServerModule::Get().StartAllListeners();
    UE_LOG(LogSpiffCoBridge, Log, TEXT("SpiffCoBridge listening on port %d (%d actions)"),
           Settings->Port, Registry.SupportedActions().Num());

    // Drive "infinite equipment" top-ups. Runs on the game thread, and is a no-op
    // (early return) whenever no player has such a toggle enabled.
    InWorld.GetTimerManager().SetTimer(
        InfiniteEquipTimer,
        [this]() { Registry.ServiceInfiniteEquipment(GetWorld()); },
        2.0f, /*loop*/ true);
}

void USpiffCoBridgeSubsystem::Deinitialize()
{
    if (const UWorld* World = GetWorld())
    {
        World->GetTimerManager().ClearTimer(InfiniteEquipTimer);
    }
    if (Router.IsValid())
    {
        if (ExecuteRoute.IsValid())
        {
            Router->UnbindRoute(ExecuteRoute);
        }
        if (HealthRoute.IsValid())
        {
            Router->UnbindRoute(HealthRoute);
        }
        Router.Reset();
    }
    Super::Deinitialize();
}

bool USpiffCoBridgeSubsystem::CheckAuth(const FHttpServerRequest& Request) const
{
    const FString Expected = USpiffCoBridgeSettings::Get()->AuthToken;
    if (Expected.IsEmpty())
    {
        return true; // Auth disabled by configuration (trusted LAN).
    }
    return HeaderValue(Request, TEXT("X-SpiffCo-Token")) == Expected;
}

bool USpiffCoBridgeSubsystem::HandleHealth(
    const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
{
    if (!CheckAuth(Request))
    {
        OnComplete(ErrorResponse(401, TEXT("missing or invalid X-SpiffCo-Token")));
        return true;
    }
    const TSharedRef<FJsonObject> Body = MakeShared<FJsonObject>();
    Body->SetStringField(TEXT("status"), TEXT("ok"));
    Body->SetStringField(TEXT("world"), GetWorld() ? GetWorld()->GetMapName() : TEXT("none"));
    TArray<TSharedPtr<FJsonValue>> Actions;
    for (const FString& ActionId : Registry.SupportedActions())
    {
        Actions.Add(MakeShared<FJsonValueString>(ActionId));
    }
    Body->SetArrayField(TEXT("actions"), Actions);
    OnComplete(JsonResponse(200, Body));
    return true;
}

bool USpiffCoBridgeSubsystem::HandleExecute(
    const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
{
    if (!CheckAuth(Request))
    {
        OnComplete(ErrorResponse(401, TEXT("missing or invalid X-SpiffCo-Token")));
        return true;
    }

    const FUTF8ToTCHAR BodyText(
        reinterpret_cast<const ANSICHAR*>(Request.Body.GetData()), Request.Body.Num());
    TSharedPtr<FJsonObject> Body;
    const auto Reader =
        TJsonReaderFactory<>::Create(FString(BodyText.Length(), BodyText.Get()));
    if (!FJsonSerializer::Deserialize(Reader, Body) || !Body.IsValid())
    {
        OnComplete(ErrorResponse(422, TEXT("body must be a JSON object")));
        return true;
    }
    FString ActionId;
    if (!Body->TryGetStringField(TEXT("action"), ActionId) || ActionId.IsEmpty())
    {
        OnComplete(ErrorResponse(422, TEXT("missing 'action'")));
        return true;
    }
    if (!Registry.IsSupported(ActionId))
    {
        OnComplete(ErrorResponse(
            501, FString::Printf(TEXT("action '%s' not implemented by this bridge version"),
                                 *ActionId)));
        return true;
    }

    FSpiffCoCommandContext Context;
    Context.World = GetWorld();
    const TSharedPtr<FJsonObject>* ParamsField = nullptr;
    Context.Params = Body->TryGetObjectField(TEXT("params"), ParamsField)
                         ? *ParamsField
                         : MakeShared<FJsonObject>();
    bool bEnabled = false;
    if (Body->TryGetBoolField(TEXT("enabled"), bEnabled))
    {
        Context.Enabled = bEnabled;
    }

    const FSpiffCoCommandResult Result = Registry.Execute(ActionId, Context);
    UE_LOG(LogSpiffCoBridge, Log, TEXT("execute %s -> %s (%s)"), *ActionId,
           Result.bSucceeded ? TEXT("ok") : TEXT("FAILED"), *Result.Message);

    const TSharedRef<FJsonObject> Payload = MakeShared<FJsonObject>();
    Payload->SetStringField(TEXT("action"), ActionId);
    Payload->SetBoolField(TEXT("succeeded"), Result.bSucceeded);
    Payload->SetStringField(TEXT("message"), Result.Message);
    OnComplete(JsonResponse(Result.bSucceeded ? 200 : 500, Payload));
    return true;
}
