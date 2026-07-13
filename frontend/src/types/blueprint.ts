/** Mirrors of backend/app/schemas/blueprint.py (Phase 8 — blueprint library). */

export interface BlueprintSummary {
  id: number;
  name: string;
  description: string;
  category: string;
  tags: string[];
  favorite: boolean;
  created_at: string;
  updated_at: string;
}

export interface Blueprint extends BlueprintSummary {
  data: Record<string, unknown>;
}

export interface BlueprintIn {
  name: string;
  description?: string;
  category?: string;
  tags?: string[];
  favorite?: boolean;
  data?: Record<string, unknown>;
}

export interface BlueprintUpdate {
  name?: string;
  description?: string;
  category?: string;
  tags?: string[];
  favorite?: boolean;
  data?: Record<string, unknown>;
}

export interface BlueprintExport {
  name: string;
  description?: string;
  category?: string;
  tags?: string[];
  data?: Record<string, unknown>;
  exported_at?: string | null;
}

export interface BlueprintStats {
  total: number;
  favorites: number;
  by_category: Record<string, number>;
  by_tag: Record<string, number>;
}
