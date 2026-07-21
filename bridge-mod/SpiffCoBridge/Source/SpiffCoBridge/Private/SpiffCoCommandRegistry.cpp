// Wave-1 command implementations.
//
// NOTE ON GAME APIS: FactoryGame header signatures drift between game updates.
// Call sites below are written against the SML 3.8+ / Satisfactory 1.0 headers
// and the ones most likely to need adjustment at compile time are marked
// "ADJUST-ME". Everything funnels through small helpers so a signature change
// is a one-line fix.

#include "SpiffCoCommandRegistry.h"

#include "EngineUtils.h"
#include "GameFramework/PlayerState.h"
#include "SpiffCoBridge.h"
#include "UObject/UObjectIterator.h"

#include "FGCharacterPlayer.h"
#include "FGCharacterMovementComponent.h"
#include "FGCheatManager.h"
#include "FGInventoryComponent.h"
#include "FGPlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Creature/FGCreature.h"
#include "Equipment/FGAmmoType.h"
#include "Equipment/FGEquipment.h"
#include "Equipment/FGWeapon.h"
#include "Resources/FGItemDescriptor.h"

namespace
{

/**
 * Resolve the target player controller.
 *
 * When the request carries params.player (set by the admin panel's target
 * selector), the connected player with that name is used; otherwise the first
 * connected player (the host in single-player). Name matching is
 * case-insensitive against the player state's display name.
 */
AFGPlayerController* GetPlayer(const FSpiffCoCommandContext& Context)
{
    if (Context.World == nullptr)
    {
        return nullptr;
    }
    FString TargetName;
    if (Context.Params.IsValid())
    {
        Context.Params->TryGetStringField(TEXT("player"), TargetName);
    }
    if (!TargetName.IsEmpty())
    {
        for (FConstPlayerControllerIterator It = Context.World->GetPlayerControllerIterator();
             It; ++It)
        {
            AFGPlayerController* Controller = Cast<AFGPlayerController>(It->Get());
            if (Controller != nullptr && Controller->PlayerState != nullptr &&
                Controller->PlayerState->GetPlayerName().Equals(TargetName,
                                                                ESearchCase::IgnoreCase))
            {
                return Controller;
            }
        }
        return nullptr; // Named player not online — fail rather than hit someone else.
    }
    return Cast<AFGPlayerController>(Context.World->GetFirstPlayerController());
}

/** Uniform failure when a requested target player is not connected. */
FSpiffCoCommandResult NoPlayerResult(const FSpiffCoCommandContext& Context)
{
    FString TargetName;
    if (Context.Params.IsValid())
    {
        Context.Params->TryGetStringField(TEXT("player"), TargetName);
    }
    return FSpiffCoCommandResult::Fail(
        TargetName.IsEmpty()
            ? TEXT("no player character available")
            : FString::Printf(TEXT("player '%s' is not online"), *TargetName));
}

AFGCharacterPlayer* GetCharacter(const FSpiffCoCommandContext& Context)
{
    AFGPlayerController* Controller = GetPlayer(Context);
    return Controller ? Cast<AFGCharacterPlayer>(Controller->GetPawn()) : nullptr;
}

/** Cheat-manager failure with an accurate reason (offline target vs. no manager). */
FSpiffCoCommandResult CheatsUnavailable(const FSpiffCoCommandContext& Context)
{
    return GetPlayer(Context) == nullptr
               ? NoPlayerResult(Context)
               : FSpiffCoCommandResult::Fail(TEXT("cheat manager unavailable"));
}

UFGCheatManager* GetCheatManager(const FSpiffCoCommandContext& Context)
{
    AFGPlayerController* Controller = GetPlayer(Context);
    if (Controller == nullptr)
    {
        return nullptr;
    }
    if (Controller->CheatManager == nullptr)
    {
        // On a shipping dedicated server EnableCheats() is a no-op (the engine
        // only auto-creates the manager when CheatClass is set, which shipping
        // builds leave null), so fall back to instantiating it explicitly. This
        // only creates the cheat-manager object — it does NOT enable Advanced
        // Game Settings/creative, so it stays achievement-safe.
        Controller->EnableCheats();
        if (Controller->CheatManager == nullptr)
        {
            Controller->CheatManager = NewObject<UFGCheatManager>(Controller);
            Controller->CheatManager->InitCheatManager();
        }
    }
    return Cast<UFGCheatManager>(Controller->CheatManager);
}

/**
 * Resolve an item reference from the SpiffCo UI: a descriptor class name
 * ("Desc_IronPlate_C"), a display name ("Iron Plate"), or a full asset path.
 */
TSubclassOf<UFGItemDescriptor> ResolveItem(const FString& ItemRef)
{
    if (ItemRef.Contains(TEXT("/")))
    {
        if (UClass* Loaded = FSoftClassPath(ItemRef).TryLoadClass<UFGItemDescriptor>())
        {
            return Loaded;
        }
    }
    for (TObjectIterator<UClass> It; It; ++It)
    {
        UClass* Candidate = *It;
        if (!Candidate->IsChildOf(UFGItemDescriptor::StaticClass()) ||
            Candidate->HasAnyClassFlags(CLASS_Abstract))
        {
            continue;
        }
        if (Candidate->GetName().Equals(ItemRef, ESearchCase::IgnoreCase))
        {
            return Candidate;
        }
        // ADJUST-ME: static display-name accessor on UFGItemDescriptor.
        const FText DisplayName = UFGItemDescriptor::GetItemName(Candidate);
        if (DisplayName.ToString().Equals(ItemRef, ESearchCase::IgnoreCase))
        {
            return Candidate;
        }
    }
    return nullptr;
}

double NumberParam(const FSpiffCoCommandContext& Context, const FString& Name, double Default)
{
    double Value = Default;
    if (Context.Params.IsValid())
    {
        Context.Params->TryGetNumberField(Name, Value);
    }
    return Value;
}

FString StringParam(const FSpiffCoCommandContext& Context, const FString& Name)
{
    FString Value;
    if (Context.Params.IsValid())
    {
        Context.Params->TryGetStringField(Name, Value);
    }
    return Value;
}

FSpiffCoCommandResult GiveItems(const FSpiffCoCommandContext& Context, const int32 Amount)
{
    AFGCharacterPlayer* Character = GetCharacter(Context);
    if (Character == nullptr)
    {
        return NoPlayerResult(Context);
    }
    const FString ItemRef = StringParam(Context, TEXT("item"));
    const TSubclassOf<UFGItemDescriptor> ItemClass = ResolveItem(ItemRef);
    if (ItemClass == nullptr)
    {
        return FSpiffCoCommandResult::Fail(
            FString::Printf(TEXT("unknown item '%s'"), *ItemRef));
    }
    // ADJUST-ME: FInventoryStack ctor order / AddStack signature.
    UFGInventoryComponent* Inventory = Character->GetInventory();
    const int32 Added = Inventory->AddStack(FInventoryStack(Amount, ItemClass), true);
    return FSpiffCoCommandResult::Ok(
        FString::Printf(TEXT("added %d x %s"), Added, *ItemClass->GetName()));
}

/** Find a connected player controller by exact display name (case-insensitive). */
AFGPlayerController* FindNamedController(const FSpiffCoCommandContext& Context, const FString& Name)
{
    if (Context.World == nullptr || Name.IsEmpty())
    {
        return nullptr;
    }
    for (FConstPlayerControllerIterator It = Context.World->GetPlayerControllerIterator();
         It; ++It)
    {
        AFGPlayerController* Controller = Cast<AFGPlayerController>(It->Get());
        if (Controller != nullptr && Controller->PlayerState != nullptr &&
            Controller->PlayerState->GetPlayerName().Equals(Name, ESearchCase::IgnoreCase))
        {
            return Controller;
        }
    }
    return nullptr;
}

/** One saved player inventory (item class + count per stack). */
struct FSpiffCoInventorySnapshot
{
    TArray<TPair<TSubclassOf<UFGItemDescriptor>, int32>> Stacks;
};

// Named inventory snapshots. In-memory and process-wide: presets persist for the
// life of the dedicated server and are cleared on restart.
static TMap<FString, FSpiffCoInventorySnapshot> GInventoryPresets;

// ---- Infinite equipment (jetpack fuel / gas filters / parachutes / ammo) ----
// The equipment's own fuel/ammo state is protected, but every one of these
// consumes ITEMS from the player's inventory. So "infinite" = a background timer
// (driven by the subsystem) that keeps the relevant consumable topped up. Which
// toggles are active is stored here as bit flags per target player ("" = first).
enum ESpiffCoInfiniteEquip : uint8
{
    IE_Jetpack = 1 << 0,
    IE_GasFilters = 1 << 1,
    IE_Parachute = 1 << 2,
    IE_Ammo = 1 << 3,
};
static TMap<FString, uint8> GInfiniteEquipment;

/** Ensure the inventory holds at least Target of ItemClass (adds only the gap). */
void TopUpItem(UFGInventoryComponent* Inventory, TSubclassOf<UFGItemDescriptor> ItemClass,
               const int32 Target)
{
    if (Inventory == nullptr || ItemClass == nullptr)
    {
        return;
    }
    const int32 Have = Inventory->GetNumItems(ItemClass);
    if (Have < Target)
    {
        Inventory->AddStack(FInventoryStack(Target - Have, ItemClass), true);
    }
}

/** Synthesize a context targeting a named player (for the top-up timer). */
FSpiffCoCommandContext ContextForPlayer(UWorld* World, const FString& PlayerName)
{
    FSpiffCoCommandContext Context;
    Context.World = World;
    const TSharedPtr<FJsonObject> Params = MakeShared<FJsonObject>();
    if (!PlayerName.IsEmpty())
    {
        Params->SetStringField(TEXT("player"), PlayerName);
    }
    Context.Params = Params;
    return Context;
}

} // namespace

FSpiffCoCommandRegistry::FSpiffCoCommandRegistry()
{
    RegisterPlayerCommands();
    RegisterWorldCommands();
    RegisterFactoryCommands();
    RegisterAchievementGuards();
}

void FSpiffCoCommandRegistry::RegisterAchievementGuards()
{
    // ACHIEVEMENT-SAFE POLICY: this bridge only ever uses the cheat manager and
    // direct engine/game calls. It NEVER touches Advanced Game Settings /
    // creative (AFGGameRulesSubsystem etc.) — enabling any AGS option flags the
    // session and permanently disables achievements. Actions whose only
    // feasible implementation is an AGS option are hard-refused here (not left
    // unregistered) so the refusal reason reaches the admin panel verbatim.
    const auto Refuse = [](const FSpiffCoCommandContext&) {
        return FSpiffCoCommandResult::Fail(
            TEXT("refused: only possible via Advanced Game Settings (creative), "
                 "which permanently disables achievements for this session"));
    };
    for (const TCHAR* ActionId : {TEXT("build.free_placement"), TEXT("build.no_collision"),
                                  TEXT("build.no_clearance")})
    {
        checkf(!Handlers.Contains(ActionId),
               TEXT("achievement guard would shadow a real handler: %s"), ActionId);
        Handlers.Add(ActionId, Refuse);
    }
}

FSpiffCoCommandResult FSpiffCoCommandRegistry::Execute(
    const FString& ActionId, const FSpiffCoCommandContext& Context) const
{
    const FSpiffCoCommandHandler* Handler = Handlers.Find(ActionId);
    if (Handler == nullptr)
    {
        return FSpiffCoCommandResult::Fail(
            FString::Printf(TEXT("action '%s' is not implemented by this bridge version"),
                            *ActionId));
    }
    return (*Handler)(Context);
}

TArray<FString> FSpiffCoCommandRegistry::SupportedActions() const
{
    TArray<FString> Actions;
    Handlers.GetKeys(Actions);
    Actions.Sort();
    return Actions;
}

void FSpiffCoCommandRegistry::RegisterPlayerCommands()
{
    Handlers.Add(TEXT("player.fly"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        const bool bEnable = Context.Enabled.Get(true);
        Cheats->PlayerFly(bEnable);
        if (!bEnable)
        {
            // Leaving fly also drops ghost/no-clip so the pioneer lands with
            // normal collision instead of hovering through the world.
            Cheats->PlayerNoClipModeOnFly(false);
        }
        // PlayerFly puts the character in the native flight movement mode, so
        // in-game Space ascends and Ctrl/crouch descends — same as the AGS
        // flight toggle; re-toggling here re-arms it if the client dropped it.
        return FSpiffCoCommandResult::Ok(
            bEnable ? TEXT("fly enabled — Space to ascend, Ctrl to descend")
                    : TEXT("fly disabled"));
    });

    Handlers.Add(TEXT("player.noclip"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        // No-clip in FactoryGame is ghost mode layered on flight. Enabling forces
        // fly on so you pass through geometry; disabling restores collision while
        // staying airborne (toggle Fly off to land).
        const bool bEnable = Context.Enabled.Get(true);
        if (bEnable)
        {
            Cheats->PlayerFly(true);
        }
        Cheats->PlayerNoClipModeOnFly(bEnable);
        return FSpiffCoCommandResult::Ok(bEnable ? TEXT("no-clip enabled (pass through walls)")
                                                 : TEXT("no-clip disabled"));
    });

    Handlers.Add(TEXT("player.god_mode"), [](const FSpiffCoCommandContext& Context) {
        AFGPlayerController* Controller = GetPlayer(Context);
        if (Controller == nullptr || Controller->GetPawn() == nullptr)
        {
            return NoPlayerResult(Context);
        }
        // Engine god-mode flag: pawn ignores all damage. Explicit set (not the
        // console toggle) so repeated requests stay idempotent.
        Controller->GetPawn()->SetCanBeDamaged(!Context.Enabled.Get(true));
        return FSpiffCoCommandResult::Ok();
    });

    Handlers.Add(TEXT("player.spawn_item"), [](const FSpiffCoCommandContext& Context) {
        return GiveItems(Context,
                         static_cast<int32>(NumberParam(Context, TEXT("quantity"), 100)));
    });

    Handlers.Add(TEXT("player.spawn_full_stacks"), [](const FSpiffCoCommandContext& Context) {
        const FString ItemRef = StringParam(Context, TEXT("item"));
        const TSubclassOf<UFGItemDescriptor> ItemClass = ResolveItem(ItemRef);
        if (ItemClass == nullptr)
        {
            return FSpiffCoCommandResult::Fail(
                FString::Printf(TEXT("unknown item '%s'"), *ItemRef));
        }
        const int32 Stacks = static_cast<int32>(NumberParam(Context, TEXT("stacks"), 1));
        // ADJUST-ME: static stack-size accessor on UFGItemDescriptor.
        const int32 PerStack = UFGItemDescriptor::GetStackSize(ItemClass);
        return GiveItems(Context, Stacks * PerStack);
    });

    Handlers.Add(TEXT("player.clear_inventory"), [](const FSpiffCoCommandContext& Context) {
        AFGCharacterPlayer* Character = GetCharacter(Context);
        if (Character == nullptr)
        {
            return NoPlayerResult(Context);
        }
        Character->GetInventory()->Empty();
        return FSpiffCoCommandResult::Ok(TEXT("inventory cleared"));
    });

    Handlers.Add(TEXT("player.unlock_all_recipes"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        Cheats->GiveAllSchematics();
        return FSpiffCoCommandResult::Ok(TEXT("all schematics granted"));
    });

    Handlers.Add(TEXT("player.unlock_mam"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        Cheats->GiveAllResearchTrees();
        return FSpiffCoCommandResult::Ok(TEXT("all MAM research granted"));
    });

    Handlers.Add(TEXT("player.teleport_coords"), [](const FSpiffCoCommandContext& Context) {
        AFGCharacterPlayer* Character = GetCharacter(Context);
        if (Character == nullptr)
        {
            return NoPlayerResult(Context);
        }
        TArray<FString> Parts;
        StringParam(Context, TEXT("coords")).ParseIntoArray(Parts, TEXT(","), true);
        if (Parts.Num() != 3)
        {
            return FSpiffCoCommandResult::Fail(TEXT("coords must be 'x,y,z' in cm"));
        }
        const FVector Target(FCString::Atod(*Parts[0].TrimStartAndEnd()),
                             FCString::Atod(*Parts[1].TrimStartAndEnd()),
                             FCString::Atod(*Parts[2].TrimStartAndEnd()));
        Character->SetActorLocation(Target, false, nullptr, ETeleportType::TeleportPhysics);
        return FSpiffCoCommandResult::Ok(
            FString::Printf(TEXT("teleported to %s"), *Target.ToCompactString()));
    });

    Handlers.Add(TEXT("player.infinite_health"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        Cheats->GodMode(Context.Enabled.Get(true));
        return FSpiffCoCommandResult::Ok();
    });

    Handlers.Add(TEXT("player.unlock_milestone"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        const int32 Tier = static_cast<int32>(NumberParam(Context, TEXT("tier"), 0));
        Cheats->GiveSchematicsOfTier(Tier);
        return FSpiffCoCommandResult::Ok(
            FString::Printf(TEXT("unlocked tier %d schematics"), Tier));
    });

    Handlers.Add(TEXT("player.unlock_awesome_shop"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        // No direct "unlock shop" cheat; grant a large coupon stash so every
        // AWESOME Shop item can be purchased.
        Cheats->GiveResourceSinkCoupons(500);
        return FSpiffCoCommandResult::Ok(TEXT("granted 500 AWESOME Shop coupons"));
    });

    Handlers.Add(TEXT("player.give_hard_drives"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        const TSubclassOf<UFGItemDescriptor> Drive = ResolveItem(TEXT("Desc_HardDrive_C"));
        if (Drive == nullptr)
        {
            return FSpiffCoCommandResult::Fail(TEXT("hard drive item not found"));
        }
        const int32 Count = static_cast<int32>(NumberParam(Context, TEXT("count"), 100));
        Cheats->GiveItemsSingle(Drive, Count);
        return FSpiffCoCommandResult::Ok(FString::Printf(TEXT("gave %d hard drives"), Count));
    });

    Handlers.Add(TEXT("player.equip_gear"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        const TSubclassOf<UFGItemDescriptor> Gear = ResolveItem(StringParam(Context, TEXT("gear")));
        if (Gear == nullptr)
        {
            return FSpiffCoCommandResult::Fail(TEXT("unknown gear item"));
        }
        Cheats->GiveItemsSingle(Gear, 1);
        return FSpiffCoCommandResult::Ok(
            TEXT("gear added to inventory (equip it from the equipment slots)"));
    });

    Handlers.Add(TEXT("player.teleport_player"), [](const FSpiffCoCommandContext& Context) {
        AFGCharacterPlayer* Me = GetCharacter(Context);
        if (Me == nullptr)
        {
            return NoPlayerResult(Context);
        }
        const FString ToName = StringParam(Context, TEXT("to_player"));
        AFGPlayerController* Dest = FindNamedController(Context, ToName);
        APawn* DestPawn = Dest != nullptr ? Dest->GetPawn() : nullptr;
        if (DestPawn == nullptr)
        {
            return FSpiffCoCommandResult::Fail(
                FString::Printf(TEXT("player '%s' is not online"), *ToName));
        }
        Me->SetActorLocation(DestPawn->GetActorLocation() + FVector(0.0f, 0.0f, 200.0f),
                             false, nullptr, ETeleportType::TeleportPhysics);
        return FSpiffCoCommandResult::Ok(FString::Printf(TEXT("teleported to %s"), *ToName));
    });

    Handlers.Add(TEXT("player.time_scale"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        const float Scale = Context.Enabled.Get(true)
                                ? static_cast<float>(NumberParam(Context, TEXT("scale"), 1.0))
                                : 1.0f;
        Cheats->SetSlomo(Scale);
        return FSpiffCoCommandResult::Ok(FString::Printf(TEXT("time scale x%.2f"), Scale));
    });

    // Custom gravity / jump height: scale the movement component's shipped
    // defaults (read from the CDO so repeated toggles never compound).
    const auto ScaleMovement = [](const FSpiffCoCommandContext& Context, const bool bGravity) {
        AFGCharacterPlayer* Character = GetCharacter(Context);
        if (Character == nullptr)
        {
            return NoPlayerResult(Context);
        }
        UFGCharacterMovementComponent* Move = Character->GetFGMovementComponent();
        if (Move == nullptr)
        {
            return FSpiffCoCommandResult::Fail(TEXT("no movement component"));
        }
        const UCharacterMovementComponent* Def =
            Move->GetClass()->GetDefaultObject<UCharacterMovementComponent>();
        const float Scale = Context.Enabled.Get(true)
                                ? static_cast<float>(NumberParam(Context, TEXT("scale"), 1.0))
                                : 1.0f;
        if (bGravity)
        {
            Move->GravityScale = Def->GravityScale * Scale;
        }
        else
        {
            Move->JumpZVelocity = Def->JumpZVelocity * Scale;
        }
        return FSpiffCoCommandResult::Ok();
    };
    Handlers.Add(TEXT("player.gravity"),
                 [ScaleMovement](const FSpiffCoCommandContext& C) { return ScaleMovement(C, true); });
    Handlers.Add(TEXT("player.jump_height"),
                 [ScaleMovement](const FSpiffCoCommandContext& C) { return ScaleMovement(C, false); });

    Handlers.Add(TEXT("player.save_inventory_preset"), [](const FSpiffCoCommandContext& Context) {
        AFGCharacterPlayer* Character = GetCharacter(Context);
        if (Character == nullptr)
        {
            return NoPlayerResult(Context);
        }
        const FString Name = StringParam(Context, TEXT("name"));
        if (Name.IsEmpty())
        {
            return FSpiffCoCommandResult::Fail(TEXT("preset name required"));
        }
        UFGInventoryComponent* Inventory = Character->GetInventory();
        FSpiffCoInventorySnapshot Snapshot;
        for (int32 Index = 0; Index < Inventory->GetSizeLinear(); ++Index)
        {
            FInventoryStack Stack;
            if (Inventory->GetStackFromIndex(Index, Stack) && Stack.HasItems())
            {
                Snapshot.Stacks.Emplace(Stack.Item.GetItemClass(), Stack.NumItems);
            }
        }
        GInventoryPresets.Add(Name, Snapshot);
        return FSpiffCoCommandResult::Ok(
            FString::Printf(TEXT("saved '%s' (%d stacks)"), *Name, Snapshot.Stacks.Num()));
    });

    Handlers.Add(TEXT("player.load_inventory_preset"), [](const FSpiffCoCommandContext& Context) {
        AFGCharacterPlayer* Character = GetCharacter(Context);
        if (Character == nullptr)
        {
            return NoPlayerResult(Context);
        }
        const FString Name = StringParam(Context, TEXT("name"));
        const FSpiffCoInventorySnapshot* Snapshot = GInventoryPresets.Find(Name);
        if (Snapshot == nullptr)
        {
            return FSpiffCoCommandResult::Fail(
                FString::Printf(TEXT("no saved preset '%s'"), *Name));
        }
        UFGInventoryComponent* Inventory = Character->GetInventory();
        Inventory->Empty();
        int32 Restored = 0;
        for (const TPair<TSubclassOf<UFGItemDescriptor>, int32>& Pair : Snapshot->Stacks)
        {
            if (Pair.Key != nullptr)
            {
                Inventory->AddStack(FInventoryStack(Pair.Value, Pair.Key), true);
                ++Restored;
            }
        }
        return FSpiffCoCommandResult::Ok(
            FString::Printf(TEXT("restored '%s' (%d stacks)"), *Name, Restored));
    });

    // ---- Owner / god-tier tools (all straight cheat-manager calls) ----
    const auto SimpleCheat = [](const FSpiffCoCommandContext& Context,
                                const TFunction<void(UFGCheatManager*)>& Action,
                                const TCHAR* OkMessage) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        Action(Cheats);
        return FSpiffCoCommandResult::Ok(OkMessage);
    };

    Handlers.Add(TEXT("player.heal"), [SimpleCheat](const FSpiffCoCommandContext& C) {
        return SimpleCheat(C, [](UFGCheatManager* M) { M->Heal(); }, TEXT("healed to full"));
    });
    Handlers.Add(TEXT("player.revive"), [SimpleCheat](const FSpiffCoCommandContext& C) {
        return SimpleCheat(C, [](UFGCheatManager* M) { M->ReviveSelf(); }, TEXT("revived"));
    });
    Handlers.Add(TEXT("player.reveal_map"), [SimpleCheat](const FSpiffCoCommandContext& C) {
        return SimpleCheat(C, [](UFGCheatManager* M) { M->Map_Reveal(); },
                           TEXT("map fog of war revealed"));
    });
    Handlers.Add(TEXT("player.collect_crates"), [SimpleCheat](const FSpiffCoCommandContext& C) {
        return SimpleCheat(C, [](UFGCheatManager* M) { M->CollectAllCrates(); },
                           TEXT("collected all dropped inventory crates"));
    });
    Handlers.Add(TEXT("player.complete_research"), [SimpleCheat](const FSpiffCoCommandContext& C) {
        return SimpleCheat(C, [](UFGCheatManager* M) { M->CompleteResearch(); },
                           TEXT("completed active MAM research"));
    });
    Handlers.Add(TEXT("player.next_game_phase"), [SimpleCheat](const FSpiffCoCommandContext& C) {
        return SimpleCheat(C, [](UFGCheatManager* M) { M->SetNextGamePhase(); },
                           TEXT("advanced to the next game phase"));
    });
    Handlers.Add(TEXT("player.promote_admin"), [SimpleCheat](const FSpiffCoCommandContext& C) {
        return SimpleCheat(C, [](UFGCheatManager* M) { M->PromoteToServerAdmin(); },
                           TEXT("promoted to server admin"));
    });

    Handlers.Add(TEXT("player.give_coupons"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        const int32 Count = static_cast<int32>(NumberParam(Context, TEXT("count"), 50));
        Cheats->GiveResourceSinkCoupons(Count);
        return FSpiffCoCommandResult::Ok(FString::Printf(TEXT("gave %d coupons"), Count));
    });

    Handlers.Add(TEXT("player.unlock_inventory_slots"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        const int32 Slots = static_cast<int32>(NumberParam(Context, TEXT("count"), 24));
        Cheats->UnlockInventorySlots(Slots);
        return FSpiffCoCommandResult::Ok(
            FString::Printf(TEXT("unlocked %d inventory slots"), Slots));
    });

    Handlers.Add(TEXT("player.unlock_arm_slots"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        const int32 Slots = static_cast<int32>(NumberParam(Context, TEXT("count"), 1));
        Cheats->UnlockArmSlots(Slots);
        return FSpiffCoCommandResult::Ok(FString::Printf(TEXT("unlocked %d arm slots"), Slots));
    });

    // Infinite equipment toggles: flip a per-player flag; the subsystem's timer
    // keeps the consumable stocked while it's set (see ServiceInfiniteEquipment).
    const auto InfiniteEquip = [](const FSpiffCoCommandContext& Context, const uint8 Flag) {
        if (GetCharacter(Context) == nullptr)
        {
            return NoPlayerResult(Context);
        }
        FString Key;
        if (Context.Params.IsValid())
        {
            Context.Params->TryGetStringField(TEXT("player"), Key);
        }
        uint8& Mask = GInfiniteEquipment.FindOrAdd(Key);
        if (Context.Enabled.Get(true))
        {
            Mask |= Flag;
        }
        else
        {
            Mask &= ~Flag;
            if (Mask == 0)
            {
                GInfiniteEquipment.Remove(Key);
            }
        }
        return FSpiffCoCommandResult::Ok();
    };
    Handlers.Add(TEXT("player.infinite_jetpack"), [InfiniteEquip](const FSpiffCoCommandContext& C) {
        return InfiniteEquip(C, IE_Jetpack);
    });
    Handlers.Add(TEXT("player.infinite_gas_filters"), [InfiniteEquip](const FSpiffCoCommandContext& C) {
        return InfiniteEquip(C, IE_GasFilters);
    });
    Handlers.Add(TEXT("player.infinite_parachute"), [InfiniteEquip](const FSpiffCoCommandContext& C) {
        return InfiniteEquip(C, IE_Parachute);
    });
    Handlers.Add(TEXT("player.infinite_ammo"), [InfiniteEquip](const FSpiffCoCommandContext& C) {
        return InfiniteEquip(C, IE_Ammo);
    });
}

void FSpiffCoCommandRegistry::RegisterWorldCommands()
{
    const auto SetTime = [](const FSpiffCoCommandContext& Context, const int32 Hour) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        // ADJUST-ME: UFGCheatManager::SetTimeOfDay(hour, minute).
        Cheats->SetTimeOfDay(Hour, 0);
        return FSpiffCoCommandResult::Ok(FString::Printf(TEXT("time set to %02d:00"), Hour));
    };
    Handlers.Add(TEXT("world.time_morning"),
                 [SetTime](const FSpiffCoCommandContext& C) { return SetTime(C, 7); });
    Handlers.Add(TEXT("world.time_noon"),
                 [SetTime](const FSpiffCoCommandContext& C) { return SetTime(C, 12); });
    Handlers.Add(TEXT("world.time_sunset"),
                 [SetTime](const FSpiffCoCommandContext& C) { return SetTime(C, 19); });
    Handlers.Add(TEXT("world.time_midnight"),
                 [SetTime](const FSpiffCoCommandContext& C) { return SetTime(C, 0); });

    const auto SetTimeSpeed = [](const FSpiffCoCommandContext& Context, const float Speed) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        // ADJUST-ME: UFGCheatManager::SetTimeSpeedMultiplier(float).
        Cheats->SetTimeSpeedMultiplier(Speed);
        return FSpiffCoCommandResult::Ok(
            FString::Printf(TEXT("day/night speed x%.2f"), Speed));
    };
    Handlers.Add(TEXT("world.freeze_time"), [SetTimeSpeed](const FSpiffCoCommandContext& C) {
        return SetTimeSpeed(C, C.Enabled.Get(true) ? 0.0f : 1.0f);
    });
    Handlers.Add(TEXT("world.time_multiplier"), [SetTimeSpeed](const FSpiffCoCommandContext& C) {
        const float Scale = C.Enabled.Get(true)
                                ? static_cast<float>(NumberParam(C, TEXT("scale"), 1.0))
                                : 1.0f;
        return SetTimeSpeed(C, Scale);
    });

    Handlers.Add(TEXT("world.kill_creatures"), [](const FSpiffCoCommandContext& Context) {
        if (Context.World == nullptr)
        {
            return FSpiffCoCommandResult::Fail(TEXT("no world"));
        }
        int32 Killed = 0;
        for (TActorIterator<AFGCreature> It(Context.World); It; ++It)
        {
            // Destroy rather than damage: works for every creature type and
            // matches the "kill all" intent; respawn via world.respawn_creatures.
            It->Destroy();
            ++Killed;
        }
        return FSpiffCoCommandResult::Ok(
            FString::Printf(TEXT("removed %d creatures"), Killed));
    });

    Handlers.Add(TEXT("world.respawn_creatures"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        Cheats->Creature_ForceSpawnCreatures();
        return FSpiffCoCommandResult::Ok(TEXT("forced creature respawn"));
    });

    Handlers.Add(TEXT("world.remove_foliage"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        // Whole-map removal (the area selection is a client build-gun concept the
        // server can't reconstruct); 0 = no instance cap.
        Cheats->Foliage_RemoveInBulk(0);
        return FSpiffCoCommandResult::Ok(TEXT("removed foliage across the map"));
    });

    Handlers.Add(TEXT("world.disable_arachnids"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        const bool bDisable = Context.Enabled.Get(true);
        Cheats->Creature_SetArachnidCreaturesDisabled(bDisable);
        return FSpiffCoCommandResult::Ok(bDisable
            ? TEXT("arachnid creatures replaced (arachnophobia mode on)")
            : TEXT("arachnid creatures restored"));
    });
}

void FSpiffCoCommandRegistry::RegisterFactoryCommands()
{
    Handlers.Add(TEXT("power.infinite"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        // Buildings run regardless of available power while enabled.
        Cheats->NoPower(Context.Enabled.Get(true));
        return FSpiffCoCommandResult::Ok();
    });

    Handlers.Add(TEXT("power.fill_fuel"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        // Generators keep running without consuming fuel.
        Cheats->NoFuel(true);
        return FSpiffCoCommandResult::Ok(TEXT("generators no longer consume fuel"));
    });

    Handlers.Add(TEXT("pipes.fill"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        Cheats->Pipe_FillFirstInEachNetwork();
        return FSpiffCoCommandResult::Ok(TEXT("filled a pipe in each network"));
    });

    Handlers.Add(TEXT("pipes.drain"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        Cheats->Pipe_EmptyAll();
        return FSpiffCoCommandResult::Ok(TEXT("drained all pipes"));
    });

    Handlers.Add(TEXT("trains.fill_cargo"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        Cheats->Trains_FillAllFreightCars(1.0f);
        return FSpiffCoCommandResult::Ok(TEXT("filled all freight cars"));
    });

    Handlers.Add(TEXT("trains.empty_cargo"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        Cheats->Trains_EmptyAllFreightCars();
        return FSpiffCoCommandResult::Ok(TEXT("emptied all freight cars"));
    });

    Handlers.Add(TEXT("trains.pause"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        if (Context.Enabled.Get(true))
        {
            Cheats->Trains_DisableSelfDriving();
        }
        else
        {
            Cheats->Trains_EnableSelfDriving(false);
        }
        return FSpiffCoCommandResult::Ok();
    });

    Handlers.Add(TEXT("drones.force_deliveries"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        Cheats->Vehicle_BringIdleDrones();
        return FSpiffCoCommandResult::Ok(TEXT("brought idle drones home"));
    });

    Handlers.Add(TEXT("radiation.spawn_waste"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        const TSubclassOf<UFGItemDescriptor> Waste = ResolveItem(TEXT("Desc_NuclearWaste_C"));
        if (Waste == nullptr)
        {
            return FSpiffCoCommandResult::Fail(TEXT("nuclear waste item not found"));
        }
        const int32 Quantity = static_cast<int32>(NumberParam(Context, TEXT("quantity"), 100));
        Cheats->GiveItemsSingle(Waste, Quantity);
        return FSpiffCoCommandResult::Ok(
            FString::Printf(TEXT("gave %d uranium waste"), Quantity));
    });

    Handlers.Add(TEXT("appearance.random_colors"), [](const FSpiffCoCommandContext& Context) {
        UFGCheatManager* Cheats = GetCheatManager(Context);
        if (Cheats == nullptr)
        {
            return CheatsUnavailable(Context);
        }
        Cheats->RandomizeBuildingsColorSlot(0);
        return FSpiffCoCommandResult::Ok(TEXT("randomized building colors"));
    });
}

void FSpiffCoCommandRegistry::ServiceInfiniteEquipment(UWorld* World) const
{
    if (World == nullptr || GInfiniteEquipment.Num() == 0)
    {
        return;
    }
    for (const TPair<FString, uint8>& Entry : GInfiniteEquipment)
    {
        const FSpiffCoCommandContext Context = ContextForPlayer(World, Entry.Key);
        AFGCharacterPlayer* Character = GetCharacter(Context);
        if (Character == nullptr)
        {
            continue; // Target offline right now; resume when they're back.
        }
        UFGInventoryComponent* Inventory = Character->GetInventory();
        const uint8 Mask = Entry.Value;
        if (Mask & IE_Jetpack)
        {
            TopUpItem(Inventory, ResolveItem(TEXT("Desc_Biofuel_C")), 50);
        }
        if (Mask & IE_GasFilters)
        {
            TopUpItem(Inventory, ResolveItem(TEXT("Desc_Filter_C")), 10);
        }
        if (Mask & IE_Parachute)
        {
            TopUpItem(Inventory, ResolveItem(TEXT("Desc_Parachute_C")), 10);
        }
        if (Mask & IE_Ammo)
        {
            // Top up whatever ammo the currently-held weapon fires.
            for (AFGEquipment* Equipment : Character->GetActiveEquipments())
            {
                const AFGWeapon* Weapon = Cast<AFGWeapon>(Equipment);
                if (Weapon == nullptr)
                {
                    continue;
                }
                const UFGAmmoType* Ammo = Weapon->GetAmmoTypeDescriptor();
                if (Ammo != nullptr &&
                    Ammo->GetClass()->IsChildOf(UFGItemDescriptor::StaticClass()))
                {
                    TopUpItem(Inventory, Ammo->GetClass(), 200);
                }
            }
        }
    }
}
