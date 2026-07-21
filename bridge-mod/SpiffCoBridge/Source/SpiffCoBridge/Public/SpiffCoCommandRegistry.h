#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/** Everything a command handler needs to act on the running world. */
struct FSpiffCoCommandContext
{
    UWorld* World = nullptr;
    /** The `params` object from the request (never null; may be empty). */
    TSharedPtr<FJsonObject> Params;
    /** For toggle actions: the desired new state. Unset for button actions. */
    TOptional<bool> Enabled;
};

/** Outcome of one command execution. */
struct FSpiffCoCommandResult
{
    bool bSucceeded = false;
    FString Message;

    static FSpiffCoCommandResult Ok(const FString& Message = TEXT("ok"))
    {
        return {true, Message};
    }
    static FSpiffCoCommandResult Fail(const FString& Message) { return {false, Message}; }
};

using FSpiffCoCommandHandler = TFunction<FSpiffCoCommandResult(const FSpiffCoCommandContext&)>;

/**
 * Maps SpiffCo admin action ids (e.g. "player.fly") to game-side handlers.
 *
 * The id namespace is defined by the SpiffCo backend catalog
 * (backend/app/admin/catalog.py). Unregistered ids report as unsupported so the
 * backend surfaces an honest 501 instead of a silent no-op; coverage grows by
 * adding handlers in SpiffCoCommandRegistry.cpp, wave by wave.
 */
class SPIFFCOBRIDGE_API FSpiffCoCommandRegistry
{
public:
    FSpiffCoCommandRegistry();

    bool IsSupported(const FString& ActionId) const { return Handlers.Contains(ActionId); }

    /** Execute an action; must be called on the game thread. */
    FSpiffCoCommandResult Execute(const FString& ActionId,
                                  const FSpiffCoCommandContext& Context) const;

    /** Supported action ids (for GET /health capability reporting). */
    TArray<FString> SupportedActions() const;

    /**
     * Keep "infinite equipment" consumables (jetpack fuel, gas filters,
     * parachutes, ammo) topped up for players who have those toggles enabled.
     * Called on a short interval by the subsystem; must run on the game thread.
     */
    void ServiceInfiniteEquipment(UWorld* World) const;

private:
    void RegisterPlayerCommands();
    void RegisterWorldCommands();
    void RegisterFactoryCommands();
    void RegisterAchievementGuards();

    TMap<FString, FSpiffCoCommandHandler> Handlers;
};
