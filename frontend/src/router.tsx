import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './layout/AppLayout';
import Dashboard from './pages/Dashboard';
import FactoryPlanner from './pages/FactoryPlanner';
import Settings from './pages/Settings';
import WorldMap from './pages/WorldMap';
import { Blueprints, Factories, Planner, Power, Resources, Trains } from './pages/stubs';

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
      { path: 'trains', element: <Trains /> },
      { path: 'blueprints', element: <Blueprints /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
]);
