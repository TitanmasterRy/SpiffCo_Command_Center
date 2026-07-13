# SpiffCo Command Center — Frontend

React 18 + TypeScript + Vite + TailwindCSS single-page app.

## Run

```bash
npm install
npm run dev        # http://localhost:5173, proxies /api and /ws to :8000
```

## Build / test

```bash
npm run build      # type-check + production bundle in dist/
npm test           # vitest
```

## Layout

```
src/
  main.tsx       Entry point (React Query + Router providers)
  router.tsx     Route table
  layout/        Sidebar, top bar, root layout
  pages/         One component per route (stubs until their phase lands)
  components/    Reusable UI (Card, StatusBadge, …)
  hooks/         Data hooks (useHealth, useEventStream)
  api/           HTTP client, typed endpoints, WebSocket client
  stores/        Zustand client state
  types/         Mirrors of backend schemas
  utils/         Formatting helpers
  styles/        Tailwind entry CSS
  tests/         Vitest suites + setup
```

Conventions: strict TypeScript, functional components, server state via TanStack
Query, client state via Zustand. See `../docs/CODING_STANDARDS.md`.
