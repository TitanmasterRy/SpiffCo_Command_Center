import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { useDashboardStreamHandler } from '../hooks/useDashboard';
import { useLogisticsStreamHandler } from '../hooks/useLogistics';
import { usePowerStreamHandler } from '../hooks/usePower';
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
  const handlePowerEvent = usePowerStreamHandler();
  useEventStream(['*'], (message) => {
    handleDashboardEvent(message);
    handleWorldEvent(message);
    handleLogisticsEvent(message);
    handlePowerEvent(message);
  });

  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onMenu={() => setNavOpen(true)} />
        <main className="flex-1 overflow-y-auto p-3 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
