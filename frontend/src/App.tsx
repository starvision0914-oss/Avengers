import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { isAuthenticated } from './api/auth';
import MainLayout from './components/Layout/MainLayout';
import LoginPage from './pages/Auth/LoginPage';
import DashboardPage from './pages/Dashboard/DashboardPage';
import CPCDashboard from './pages/CPC/CPCDashboard';
import AccountListPage from './pages/Accounts/AccountListPage';
import SalesListPage from './pages/Sales/SalesListPage';
import SalesUploadPage from './pages/Sales/SalesUploadPage';
import KanbanBoard from './pages/Todos/KanbanBoard';
import ProjectListPage from './pages/Todos/ProjectListPage';
import ChatPage from './pages/Messaging/ChatPage';
import EmailPage from './pages/Email/EmailPage';
import SettingsPage from './pages/Settings/SettingsPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="cpc" element={<CPCDashboard />} />
          <Route path="accounts" element={<AccountListPage />} />
          <Route path="sales" element={<SalesListPage />} />
          <Route path="sales/upload" element={<SalesUploadPage />} />
          <Route path="todos" element={<ProjectListPage />} />
          <Route path="todos/:projectId" element={<KanbanBoard />} />
          <Route path="messaging" element={<ChatPage />} />
          <Route path="email" element={<EmailPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
