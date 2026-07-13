import { PagePlaceholder } from '../components/PagePlaceholder';

/**
 * Placeholder pages for modules implemented in later phases.
 * Each becomes its own file when its phase begins.
 */

export function Factories() {
  return (
    <PagePlaceholder
      title="Factories"
      phase="Phase 2"
      description="Per-factory status, machine counts, efficiency, and production details."
    />
  );
}

export function Planner() {
  return (
    <PagePlaceholder
      title="Production Planner"
      phase="Phase 5"
      description="Recipe planning with clock speeds, somersloops, alternate recipes, input/output balancing, power calculations, and shopping lists."
    />
  );
}

export function Power() {
  return (
    <PagePlaceholder
      title="Power"
      phase="Phase 7"
      description="Power graph, historical usage, consumption vs. generation, battery backup, and recommendations."
    />
  );
}

export function Resources() {
  return (
    <PagePlaceholder
      title="Resources"
      phase="Phase 3+"
      description="Resource node management: locations, purity, occupancy, and extraction rates."
    />
  );
}

export function Trains() {
  return (
    <PagePlaceholder
      title="Train Network"
      phase="Phase 6"
      description="Train routes, timetables, throughput analysis, and network visualization."
    />
  );
}

export function Blueprints() {
  return (
    <PagePlaceholder
      title="Blueprints"
      phase="Phase 8"
      description="Blueprint library with categories, tags, search, favorites, import/export, and statistics."
    />
  );
}
