import type { BuildingModel } from '../utils/buildingOutline';
import type { MapFeature } from '../types/world';

/**
 * Game-styled building info panel shown when clicking a building on the map,
 * styled after SCIM's building UI and using the mod's own textures
 * (`/assets/scim/ui/`, taken from the SC-InteractiveMap `img/` assets):
 * a dark FICSIT panel with the machine background art as a watermark and the
 * in-game indicator light for the building's status.
 */

const UI_BASE = '/assets/scim/ui';

/** Building category → SCIM background art. */
function panelBackground(category: string | undefined): string {
  if (category === 'extraction') return `${UI_BASE}/Extractor_BG.png`;
  if (category === 'generator') return `${UI_BASE}/TXUI_GeothermalBG.png`;
  return `${UI_BASE}/TXUI_Manufacturer_BG.png`;
}

const STATUS_LIGHT: Record<string, { icon: string; label: string; color: string }> = {
  operational: {
    icon: `${UI_BASE}/TXUI_IndicatorPanel_Light_Operational.png`,
    label: 'Operational',
    color: '#7fd856',
  },
  caution: {
    icon: `${UI_BASE}/TXUI_IndicatorPanel_Light_Caution.png`,
    label: 'Idle',
    color: '#e8c341',
  },
  error: {
    icon: `${UI_BASE}/TXUI_IndicatorPanel_Light_Error.png`,
    label: 'No power',
    color: '#e0524d',
  },
};

interface BuildingPanelProps {
  feature: MapFeature;
  model?: BuildingModel;
}

export function BuildingPanel({ feature, model }: BuildingPanelProps) {
  const status = STATUS_LIGHT[String(feature.meta.status ?? '')];
  const produces = String(feature.meta.produces ?? '');
  const power = feature.meta.power_mw;
  const isGenerator = feature.type === 'power_plant';
  return (
    <div className="w-64 overflow-hidden rounded-md border-2 border-[#5b5b5b] bg-[#2b2a27] text-slate-200 shadow-xl">
      {/* FICSIT orange header band. */}
      <div className="bg-[#fa9549] px-3 py-1.5 text-sm font-bold uppercase tracking-wide text-[#3d2000]">
        {feature.name}
      </div>
      <div
        className="relative px-3 py-2"
        style={{
          backgroundImage: `linear-gradient(rgba(43,42,39,.88), rgba(43,42,39,.94)), url(${panelBackground(isGenerator ? 'generator' : model?.category)})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      >
        {status && (
          <div className="mb-2 flex items-center gap-2">
            <img src={status.icon} alt="" style={{ width: 22, height: 22, minWidth: 0 }} />
            <span className="text-xs font-semibold" style={{ color: status.color }}>
              {status.label}
            </span>
          </div>
        )}
        <dl className="space-y-1 text-xs">
          {produces && (
            <div>
              <dt className="text-[10px] uppercase tracking-wide text-slate-400">
                {isGenerator ? 'Generates' : 'Produces'}
              </dt>
              <dd className="text-slate-200">{produces}</dd>
            </div>
          )}
          {typeof power === 'number' && power > 0 && (
            <div>
              <dt className="text-[10px] uppercase tracking-wide text-slate-400">Power draw</dt>
              <dd className="text-slate-200">{power} MW</dd>
            </div>
          )}
          <div>
            <dt className="text-[10px] uppercase tracking-wide text-slate-400">Location</dt>
            <dd className="font-mono text-[11px] text-slate-300">
              X {Math.round(feature.position.x).toLocaleString()} · Y{' '}
              {Math.round(feature.position.y).toLocaleString()}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
