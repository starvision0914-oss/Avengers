import { Outlet } from 'react-router-dom';
import TopNav from './TopNav';

export default function MainLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-100">
      <TopNav />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
