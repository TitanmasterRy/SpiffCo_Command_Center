import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './layout/AppLayout';
import Dashboard from './pages/Dashboard';
import FactoryPlanner from './pages/FactoryPlanner';
import Blueprints from './pages/Blueprints';
import Logistics from './pages/Logistics';
import Planner from './pages/Planner';
import Power from './pages/Power';
import Settings from './pages/Settings';
import WorldMap from './pages/WorldMap';
import { Factories, Resources } from './pages/stubs';

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
      { path: 'settings', element: <Settings /> },
    ],
  },
]);
