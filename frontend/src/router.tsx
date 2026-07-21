import type { ReactNode } from 'react';
import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './layout/AppLayout';
import { RequireAuth, RequirePermission } from './components/RouteGuards';
import Admin from './pages/Admin';
import Dashboard from './pages/Dashboard';
import ExternalTool from './pages/ExternalTool';
import Factories from './pages/Factories';
import FactoryPlanner from './pages/FactoryPlanner';
import Advisor from './pages/Advisor';
import Analytics from './pages/Analytics';
import Blueprints from './pages/Blueprints';
import Login from './pages/Login';
import Logistics from './pages/Logistics';
import Offline from './pages/Offline';
import Planner from './pages/Planner';
import Power from './pages/Power';
import Resources from './pages/Resources';
import Settings from './pages/Settings';
import WorldMap from './pages/WorldMap';

/** Wrap a page in a per-page permission gate. */
function guard(permission: string, element: ReactNode): ReactNode {
  return <RequirePermission permission={permission}>{element}</RequirePermission>;
}

/** Application route table. */
export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    // RequireAuth gates the whole app behind login (no-op when auth is disabled).
    element: <RequireAuth />,
    children: [
      {
        path: '/',
        element: <AppLayout />,
        children: [
          { index: true, element: guard('view:dashboard', <Dashboard />) },
          { path: 'map', element: guard('view:map', <WorldMap />) },
          { path: 'factories', element: guard('view:factories', <Factories />) },
          { path: 'factory-planner', element: guard('view:factory-planner', <FactoryPlanner />) },
          { path: 'planner', element: guard('view:planner', <Planner />) },
          { path: 'power', element: guard('view:power', <Power />) },
          { path: 'resources', element: guard('view:resources', <Resources />) },
          { path: 'trains', element: guard('view:logistics', <Logistics />) },
          { path: 'blueprints', element: guard('view:blueprints', <Blueprints />) },
          { path: 'analytics', element: guard('view:analytics', <Analytics />) },
          { path: 'advisor', element: guard('view:advisor', <Advisor />) },
          { path: 'offline', element: guard('view:offline', <Offline />) },
          // Admin gates its own tabs (cheats vs. users) by permission.
          { path: 'admin', element: <Admin /> },
          {
            path: 'tools/sc-production',
            element: (
              <ExternalTool
                title="SC Production Planner"
                src="https://satisfactory-calculator.com/en/planners/production"
                source="satisfactory-calculator.com"
              />
            ),
          },
          {
            path: 'tools/sc-power',
            element: (
              <ExternalTool
                title="SC Power Planner"
                src="https://satisfactory-calculator.com/en/planners/power"
                source="satisfactory-calculator.com"
              />
            ),
          },
          {
            path: 'tools/satisfactory-tools',
            element: (
              <ExternalTool
                title="Satisfactory Tools Planner"
                src="https://www.satisfactorytools.com/1.0/production"
                source="satisfactorytools.com"
              />
            ),
          },
          {
            path: 'tools/scim',
            element: (
              <ExternalTool
                title="SCIM Interactive Map"
                src="https://satisfactory-calculator.com/en/interactive-map"
                source="satisfactory-calculator.com"
                note="save-file based; for the live in-game feed use World Map"
              />
            ),
          },
          { path: 'settings', element: guard('view:settings', <Settings />) },
        ],
      },
    ],
  },
]);
