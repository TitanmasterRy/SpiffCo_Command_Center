#pragma once

#include "CoreMinimal.h"
#include "HttpResultCallback.h"
#include "HttpRouteHandle.h"
#include "SpiffCoCommandRegistry.h"
#include "Subsystems/WorldSubsystem.h"
#include "SpiffCoBridgeSubsystem.generated.h"

class IHttpRouter;
struct FHttpServerRequest;

/**
 * Runs the bridge HTTP server for the lifetime of a game world.
 *
 * Endpoints (all JSON):
 *   GET  /health   -> {status, world, actions: [supported ids]}
 *   POST /execute  -> body {action, params?, enabled?}; 200 on success,
 *                     401 bad/missing X-SpiffCo-Token, 404 unknown world,
 *                     422 malformed body, 501 unsupported action,
 *                     500 handler failure (message in body).
 *
 * Only starts with authority (host / dedicated server), never on clients.
 * Handlers run on the game thread (FHttpServerModule ticks there), so command
 * implementations may touch game state directly.
 */
UCLASS()
class SPIFFCOBRIDGE_API USpiffCoBridgeSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;

private:
    // Signatures must match FHttpRequestHandler exactly (FHttpResultCallback,
    // not an equivalent TFunction spelling) for CreateUObject to bind.
    bool HandleExecute(const FHttpServerRequest& Request,
                       const FHttpResultCallback& OnComplete);
    bool HandleHealth(const FHttpServerRequest& Request,
                      const FHttpResultCallback& OnComplete);
    bool CheckAuth(const FHttpServerRequest& Request) const;

    TSharedPtr<IHttpRouter> Router;
    FHttpRouteHandle ExecuteRoute;
    FHttpRouteHandle HealthRoute;
    FTimerHandle InfiniteEquipTimer;
    FSpiffCoCommandRegistry Registry;
};
