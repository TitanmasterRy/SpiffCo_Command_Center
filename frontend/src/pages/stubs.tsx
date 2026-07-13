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

export function Resources() {
  return (
    <PagePlaceholder
      title="Resources"
      phase="Phase 3+"
      description="Resource node management: locations, purity, occupancy, and extraction rates."
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
