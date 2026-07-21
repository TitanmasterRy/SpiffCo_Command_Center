using UnrealBuildTool;

public class SpiffCoBridge : ModuleRules
{
    public SpiffCoBridge(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        CppStandard = CppStandardVersion.Cpp20;

        PublicDependencyModuleNames.AddRange(new[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "DeveloperSettings",
            "Json",
            "JsonUtilities",
            "HTTPServer",
            "FactoryGame",
            "SML",
        });
    }
}
