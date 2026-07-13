import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: '▦' },
  { to: '/map', label: 'World Map', icon: '🗺' },
  { to: '/factories', label: 'Factories', icon: '🏭' },
  { to: '/factory-planner', label: 'Factory Planner', icon: '🧱' },
  { to: '/planner', label: 'Production Planner', icon: '⚙' },
  { to: '/power', label: 'Power', icon: '⚡' },
  { to: '/resources', label: 'Resources', icon: '⛏' },
  { to: '/trains', label: 'Logistics', icon: '🚆' },
  { to: '/blueprints', label: 'Blueprints', icon: '📐' },
  { to: '/analytics', label: 'Analytics', icon: '📈' },
  { to: '/advisor', label: 'Advisor', icon: '🧠' },
  { to: '/settings', label: 'Settings', icon: '🛠' },
] as const;

/** Primary navigation sidebar. */
export function Sidebar() {
  return (
    <nav className="flex w-56 shrink-0 flex-col border-r border-surface-border bg-surface-raised">
      <div className="flex items-center gap-2 px-4 py-5">
        <span className="text-xl text-accent" aria-hidden>
          ⬢
        </span>
        <div>
          <div className="text-sm font-bold tracking-wide text-slate-100">SpiffCo</div>
          <div className="text-[10px] uppercase tracking-widest text-slate-500">
            Command Center
          </div>
        </div>
      </div>
      <ul className="flex-1 space-y-0.5 px-2">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? 'bg-accent/10 font-medium text-accent'
                    : 'text-slate-400 hover:bg-surface-overlay hover:text-slate-200'
                }`
              }
            >
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
