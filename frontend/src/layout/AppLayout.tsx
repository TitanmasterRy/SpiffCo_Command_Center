import { Outlet } from 'react-router-dom';
import { useDashboardStreamHandler } from '../hooks/useDashboard';
import { useLogisticsStreamHandler } from '../hooks/useLogistics';
import { useWorldStreamHandler } from '../hooks/useWorld';
import { useEventStream } from '../hooks/useEventStream';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

/**
 * Root layout: sidebar + top bar + routed page content.
 * Owns the app-wide WebSocket subscription.
 */
export function AppLayout() {
  const handleDashboardEvent = useDashboardStreamHandler();
  const handleWorldEvent = useWorldStreamHandler();
  const handleLogisticsEvent = useLogisticsStreamHandler();
  useEventStream(['*'], (message) => {
    handleDashboardEvent(message);
    handleWorldEvent(message);
    handleLogisticsEvent(message);
  });

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
