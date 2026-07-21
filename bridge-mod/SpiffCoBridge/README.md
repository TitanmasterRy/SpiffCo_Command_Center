# SpiffCoBridge — game-side command bridge for SpiffCo Command Center

A Satisfactory mod (SML plugin) that runs a small authenticated HTTP server
inside the game / dedicated server and executes admin actions dispatched by the
SpiffCo backend. It is the **write path** companion to Ficsit Remote Monitoring:
FRM reads telemetry, SpiffCoBridge executes commands.

## How it fits together

```
SpiffCo Admin Panel ──▶ SpiffCo backend ──POST /execute──▶ SpiffCoBridge (in-game)
                          (audit log)      X-SpiffCo-Token      │
                                                                ▼
                                                    FGCheatManager / game APIs
```

- The backend's action ids (`player.fly`, `world.time_noon`, …) are defined in
  `backend/app/admin/catalog.py`; the bridge's `FSpiffCoCommandRegistry` maps
  them to game calls.
- Unimplemented actions return **501**, which the backend logs as `failed` and
  shows in the panel — no silent no-ops.
- Before the mod is built, `scripts/mock_bridge.py` implements the same
  contract for end-to-end testing.

## HTTP contract

| Route | Verb | Body / response |
|---|---|---|
| `/health` | GET | `{status, world, actions: [supported ids]}` |
| `/execute` | POST | `{action, params?, enabled?}` → `{action, succeeded, message}`; 401 bad token, 422 malformed, 501 unsupported, 500 handler failure |

Auth: shared secret in the `X-SpiffCo-Token` header. Empty token in config =
auth disabled (trusted LAN only; the mod logs a warning).

## Building (SML toolchain)

This is a standard SML C++ mod; it cannot be compiled standalone — it needs the
modding fork of Unreal Engine and the SatisfactoryModLoader project. Follow the
official docs (https://docs.ficsit.app/satisfactory-modding/latest/Development/
BeginnersGuide/index.html), then:

1. Clone `satisfactorymodding/SatisfactoryModLoader` and set it up per the
   guide (UE 5.3.2-CSS, Wwise, Visual Studio 2022).
2. Copy this `SpiffCoBridge/` folder into the project's `Mods/` directory.
3. Regenerate project files, build the `FactoryGameEditor` target, then package
   the mod via `Alpakit` (ships with SML) for `Windows` and/or `WindowsServer`
   / `LinuxServer`.
4. Install the packaged `.smod`/plugin on the game **host** (the machine with
   authority — the dedicated server, or the host in single-player). Clients do
   not need it; the listener never starts on clients.

> **Compile notes:** call sites marked `ADJUST-ME` in
> `SpiffCoCommandRegistry.cpp` touch FactoryGame signatures that occasionally
> drift between game updates (item descriptor accessors, cheat-manager time
> functions, `FInventoryStack`). If the build errors there, check the current
> header in `Source/FactoryGame/Public/` and adjust the one line.

## Configuration

`Saved/Config/WindowsServer/Game.ini` on a dedicated server (or
`%LOCALAPPDATA%/FactoryGame/Saved/Config/Windows/Game.ini` for a host client):

```ini
[/Script/SpiffCoBridge.SpiffCoBridgeSettings]
bEnabled=True
Port=8091
AuthToken=pick-a-long-random-string
```

Then on the SpiffCo backend:

```
SPIFFCO_ADMIN_COMMAND_URL=http://<game-host>:8091   ; host.docker.internal from Docker
SPIFFCO_ADMIN_COMMAND_TOKEN=pick-a-long-random-string
```

Port 8091 avoids FRM's default 8080 (and SmartFoxServer, which also squats on
8080 on some machines).

## Action coverage (wave 1)

| Action id | Implementation |
|---|---|
| `player.fly` | `UFGCheatManager::PlayerFly` |
| `player.noclip` | `PlayerNoClipModeOnFly` (forces fly on) |
| `player.god_mode` | pawn `SetCanBeDamaged(false)` |
| `player.spawn_item` / `player.spawn_full_stacks` | inventory `AddStack`, item resolved by class name (`Desc_IronPlate_C`), display name, or asset path |
| `player.clear_inventory` | inventory `Empty()` |
| `player.unlock_all_recipes` | `GiveAllSchematics` |
| `player.unlock_mam` | `GiveAllResearchTrees` |
| `player.teleport_coords` | `SetActorLocation` (`x,y,z` in cm — same units as the World Map) |
| `world.time_morning/noon/sunset/midnight` | `SetTimeOfDay` |
| `world.freeze_time` / `world.time_multiplier` | `SetTimeSpeedMultiplier` |
| `world.kill_creatures` | destroy all `AFGCreature` |
| everything else | 501 until a later wave |

Wave 2 candidates (roughly in order of implementation effort): remaining cheat-
manager passthroughs (Awesome Shop / milestone unlocks, hard drives, radiation
toggle), power controls via `AFGCircuitSubsystem`, belt/storage fill via
inventory components, creature spawning via `AFGCreatureSpawner`, mass-building
tools (hardest — needs buildable iteration + undo snapshots).

## Player targeting

Player-scoped commands read `params.player` (sent by the admin panel's
"Target player" selector, populated from FRM's online-player list):

- `params.player` set → the connected player whose display name matches
  (case-insensitive). If they are **not online, the command fails** with
  `player '<name>' is not online` — it never falls through to someone else.
- `params.player` empty/absent → the first connected player (the host in
  single-player).

World-scoped commands (flagged **All players** in the panel) ignore the param —
they act on session-shared state.

## Achievement safety

**The bridge never enables Advanced Game Settings / creative mode.** In
Satisfactory, flipping any AGS option flags the session and permanently
disables achievements; plain cheat-manager and engine calls do not. Policy,
enforced in `RegisterAchievementGuards()`:

- Every implemented command uses `UFGCheatManager` or direct engine/game calls
  only. Nothing in this codebase references the AGS/creative subsystems — keep
  it that way in wave 2 (grep for `GameRules` before merging new handlers).
- Actions that are *only* achievable via an AGS option
  (`build.free_placement`, `build.no_collision`, `build.no_clearance`) are
  registered as hard refusals with an explanatory message, rather than left as
  501s, so the panel shows *why* instead of "not implemented yet".
- If a future game update ever routes a cheat-manager function through AGS,
  drop that handler rather than accept the flag.
