import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './layout/AppLayout';
import Dashboard from './pages/Dashboard';
import ExternalTool from './pages/ExternalTool';
import Factories from './pages/Factories';
import FactoryPlanner from './pages/FactoryPlanner';
import Advisor from './pages/Advisor';
import Analytics from './pages/Analytics';
import Blueprints from './pages/Blueprints';
import Logistics from './pages/Logistics';
import Offline from './pages/Offline';
import Planner from './pages/Planner';
import Power from './pages/Power';
import Resources from './pages/Resources';
import Settings from './pages/Settings';
import WorldMap from './pages/WorldMap';

/** Application route table. */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'map', element: <WorldMap /> },
      { path: 'factories', element: <Factories /> },
      { path: 'factory-planner', element: <FactoryPlanner /> },
      { path: 'planner', element: <Planner /> },
      { path: 'power', element: <Power /> },
      { path: 'resources', element: <Resources /> },
      { path: 'trains', element: <Logistics /> },
      { path: 'blueprints', element: <Blueprints /> },
      { path: 'analytics', element: <Analytics /> },
      { path: 'advisor', element: <Advisor /> },
      { path: 'offline', element: <Offline /> },
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
      { path: 'settings', element: <Settings /> },
    ],
  },
]);
