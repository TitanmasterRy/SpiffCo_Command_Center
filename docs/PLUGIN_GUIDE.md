# Plugin Guide (design specification)

> Status: **specified, not yet implemented.** The plugin runtime ships after the
> core phases stabilize the APIs it exposes. This document fixes the design so
> core code is written to be plugin-friendly from the start.

## Goals

Let the community add panels, data sources, and advisors without forking:

- **Backend plugins**: Python packages exposing a `spiffco.plugin` entry point.
  They receive a `PluginContext` (event bus handle, scheduler, DB session
  factory, settings namespace) and may register routers under
  `/api/plugins/<name>/`, scheduler jobs, and advisor rules.
- **Frontend plugins**: a manifest declaring panels (route + remote module) that
  the shell lazy-loads and lists in the sidebar under a "Plugins" section.

## Contract sketch

```python
class SpiffcoPlugin(Protocol):
    name: str
    version: str

    def setup(self, ctx: PluginContext) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

## Rules for core development (in force today)

- Anything a plugin will need goes through an interface (`EventBus`,
  `Scheduler`, service functions) — never module globals.
- Topic names, error codes, and schemas are treated as public API; breaking
  changes require a changelog entry.
- The `plugins/` directory is reserved for drop-in plugin installations.
