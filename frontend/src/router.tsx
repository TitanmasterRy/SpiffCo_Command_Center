import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './layout/AppLayout';
import Dashboard from './pages/Dashboard';
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
      { path: 'settings', element: <Settings /> },
    ],
  },
]);
