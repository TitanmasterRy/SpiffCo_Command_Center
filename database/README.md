# Database — Static Game Data

JSON files describing Satisfactory game entities, used by the planner, map, and
advisor modules. These are **seed data** for Phase 1; the full datasets are
imported from the community docs (`Docs.json` from the game files) by
`scripts/import_game_data.py` (planned).

See [docs/DATABASE_SCHEMA.md](../docs/DATABASE_SCHEMA.md) for field definitions.

| File | Contents |
|---|---|
| `data/items.json` | Craftable items and fluids |
| `data/recipes.json` | Default recipes (machine, inputs, outputs, rates) |
| `data/alternate_recipes.json` | Alternate recipes unlocked via hard drives |
| `data/buildings.json` | Production buildings and their stats |
| `data/build_costs.json` | Construction costs per building |
| `data/power_buildings.json` | Generators and power infrastructure |
| `data/resources.json` | Raw resources |
| `data/resource_nodes.json` | Node locations, purity, type |
| `data/transportation.json` | Belts, pipes, vehicles and their throughput |
| `data/machines.json` | Machine definitions used by the simulator |

All rates are **per minute** and all power values are **megawatts** unless a
field name says otherwise. IDs are stable slugs (`iron-ingot`), never display names.
