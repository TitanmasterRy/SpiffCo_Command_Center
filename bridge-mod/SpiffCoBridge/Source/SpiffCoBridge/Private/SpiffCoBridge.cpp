#include "SpiffCoBridge.h"

DEFINE_LOG_CATEGORY(LogSpiffCoBridge);

void FSpiffCoBridgeModule::StartupModule()
{
    UE_LOG(LogSpiffCoBridge, Log, TEXT("SpiffCoBridge module loaded"));
}

void FSpiffCoBridgeModule::ShutdownModule()
{
}

IMPLEMENT_MODULE(FSpiffCoBridgeModule, SpiffCoBridge)
