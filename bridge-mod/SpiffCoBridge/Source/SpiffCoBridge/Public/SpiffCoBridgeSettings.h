#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "SpiffCoBridgeSettings.generated.h"

/**
 * Bridge configuration, read from Game.ini:
 *
 *   [/Script/SpiffCoBridge.SpiffCoBridgeSettings]
 *   bEnabled=True
 *   Port=8091
 *   AuthToken=change-me
 *
 * On a dedicated server the file lives in Saved/Config/WindowsServer/Game.ini
 * (LinuxServer on Linux). An empty AuthToken disables auth — only acceptable
 * on a trusted LAN.
 */
UCLASS(Config = Game, DefaultConfig)
class SPIFFCOBRIDGE_API USpiffCoBridgeSettings : public UDeveloperSettings
{
    GENERATED_BODY()

public:
    /** Master switch; the HTTP listener only starts when true. */
    UPROPERTY(Config, EditAnywhere, Category = "SpiffCo Bridge")
    bool bEnabled = false;

    /** TCP port for the bridge HTTP server (FRM's default is 8080 — keep them apart). */
    UPROPERTY(Config, EditAnywhere, Category = "SpiffCo Bridge")
    int32 Port = 8091;

    /** Shared secret; requests must carry it in the X-SpiffCo-Token header. */
    UPROPERTY(Config, EditAnywhere, Category = "SpiffCo Bridge")
    FString AuthToken;

    static const USpiffCoBridgeSettings* Get() { return GetDefault<USpiffCoBridgeSettings>(); }
};
