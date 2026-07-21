import { NavLink } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

interface NavItem {
  to: string;
  label: string;
  icon: string;
  /** Permission key(s) required to see this item; visible if the user holds any. */
  perms?: string[];
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: '▦', perms: ['view:dashboard'] },
  { to: '/map', label: 'World Map', icon: '🗺', perms: ['view:map'] },
  { to: '/factories', label: 'Factories', icon: '🏭', perms: ['view:factories'] },
  { to: '/factory-planner', label: 'Factory Planner', icon: '🧱', perms: ['view:factory-planner'] },
  { to: '/planner', label: 'Production Planner', icon: '⚙', perms: ['view:planner'] },
  { to: '/power', label: 'Power', icon: '⚡', perms: ['view:power'] },
  { to: '/resources', label: 'Resources', icon: '⛏', perms: ['view:resources'] },
  { to: '/trains', label: 'Logistics', icon: '🚆', perms: ['view:logistics'] },
  { to: '/blueprints', label: 'Blueprints', icon: '📐', perms: ['view:blueprints'] },
  { to: '/analytics', label: 'Analytics', icon: '📈', perms: ['view:analytics'] },
  { to: '/advisor', label: 'Advisor', icon: '🧠', perms: ['view:advisor'] },
  { to: '/offline', label: 'Offline Mode', icon: '💾', perms: ['view:offline'] },
  // Admin: visible to anyone who can run cheats or manage accounts.
  { to: '/admin', label: 'Admin', icon: '🛡', perms: ['use:admin-cheats', 'manage:users'] },
  { to: '/settings', label: 'Settings', icon: '🛠', perms: ['view:settings'] },
];

/** Embedded third-party community tools (see the `/tools/*` routes). */
const TOOL_NAV_ITEMS = [
  { to: '/tools/sc-production', label: 'SC Production', icon: '🏗' },
  { to: '/tools/sc-power', label: 'SC Power', icon: '🔌' },
  { to: '/tools/satisfactory-tools', label: 'Satisfactory Tools', icon: '🧮' },
  { to: '/tools/scim', label: 'SCIM Map', icon: '🌍' },
] as const;

interface SidebarProps {
  /** Whether the mobile drawer is open (ignored at md+ where it's always shown). */
  open: boolean;
  /** Close the mobile drawer (also fired when a nav item is tapped). */
  onClose: () => void;
}

interface SidebarLinkProps {
  item: { to: string; label: string; icon: string };
  onClose: () => void;
}

/** True if the user may see *item* (no perms = always visible). */
function canSee(item: NavItem, has: (key: string) => boolean): boolean {
  return !item.perms || item.perms.some(has);
}

function SidebarLink({ item, onClose }: SidebarLinkProps) {
  return (
    <NavLink
      to={item.to}
      end={item.to === '/'}
      onClick={onClose}
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
  );
}

/** Primary navigation: a fixed column at md+, a slide-out drawer on mobile. */
export function Sidebar({ open, onClose }: SidebarProps) {
  const { hasPermission } = useAuth();
  const visibleItems = NAV_ITEMS.filter((item) => canSee(item, hasPermission));
  return (
    <>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/60 md:hidden" onClick={onClose} aria-hidden />
      )}
      <nav
        // Transform is an inline value (not a Tailwind var) so the slide
        // transitions reliably; md:!transform-none resets it on desktop where
        // the nav is a static in-flow column.
        style={{ transform: open ? 'translateX(0)' : 'translateX(-100%)' }}
        className="fixed inset-y-0 left-0 z-40 flex w-56 shrink-0 flex-col border-r border-surface-border bg-surface-raised md:static md:!transform-none"
      >
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
        <ul className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
          {visibleItems.map((item) => (
            <li key={item.to}>
              <SidebarLink item={item} onClose={onClose} />
            </li>
          ))}
          <li className="px-3 pb-1 pt-4 text-[10px] uppercase tracking-widest text-slate-500">
            External Tools
          </li>
          {TOOL_NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <SidebarLink item={item} onClose={onClose} />
            </li>
          ))}
        </ul>
      </nav>
    </>
  );
}
