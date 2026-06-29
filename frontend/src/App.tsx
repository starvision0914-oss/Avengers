import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { isAuthenticated } from './api/auth';
import MainLayout from './components/Layout/MainLayout';
import LoginPage from './pages/Auth/LoginPage';
import DashboardPage from './pages/Dashboard/DashboardPage';
import SpeedGoPage from './pages/SpeedGo/SpeedGoPage';
import CPCDashboard from './pages/CPC/CPCDashboard';
import AccountListPage from './pages/Accounts/AccountListPage';
import SalesListPage from './pages/Sales/SalesListPage';
import SalesDashboardPage from './pages/Sales/SalesDashboardPage';
import NetProfitPage from './pages/Sales/NetProfitPage';
import ElevenKilllistPage from './pages/St11/ElevenKilllistPage';
import SalesUploadPage from './pages/Sales/SalesUploadPage';
import KanbanBoard from './pages/Todos/KanbanBoard';
import ProjectListPage from './pages/Todos/ProjectListPage';
import ChatPage from './pages/Messaging/ChatPage';
import EmailPage from './pages/Email/EmailPage';
import SettingsPage from './pages/Settings/SettingsPage';
import CrawlerPage from './pages/Crawler/CrawlerPage';
import TelegramPage from './pages/Telegram/TelegramPage';
import AnalysisPage from './pages/Analysis/AnalysisPage';
import AdSettingsPage from './pages/AdSettings/AdSettingsPage';
import CrawlerAccountsPage from './pages/CrawlerAccounts/CrawlerAccountsPage';
import St11Dashboard from './pages/St11/St11Dashboard';
import St11RoasPage from './pages/St11/St11RoasPage';
import SmsManagePage from './pages/Sms/SmsManagePage';
import OwnerclanProductsPage from './pages/Ownerclan/OwnerclanProductsPage';
import MyProductPage from './pages/MyProduct/MyProductPage';
import KeywordProductsPage from './pages/Keyword/KeywordProductsPage';
import ElevenMyProductsPage from './pages/ElevenMy/ElevenMyProductsPage';
import GmarketMyProductsPage from './pages/GmarketMy/GmarketMyProductsPage';
import GmarketDashboard from './pages/Gmarket/GmarketDashboard';
import GmarketAdGroupPage from './pages/Gmarket/GmarketAdGroupPage';
import GmarketRoasPage from './pages/Gmarket/GmarketRoasPage';
import LottoPage from './pages/Lotto/LottoPage';
import OverviewDashboard from './pages/Overview/OverviewDashboard';
import RoadmapPage from './pages/Roadmap/RoadmapPage';
import SalesMatchPage from './pages/Sales/SalesMatchPage';
import TaxVatPage from './pages/Tax/TaxVatPage';
import SmsWidget from './components/SmsWidget';
import SmartStorePage from './pages/SmartStore/SmartStorePage';
import NaverRoasPage from './pages/SmartStore/NaverRoasPage';
import NaverBlogPage from './pages/NaverBlog/NaverBlogPage';

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
        <Route path="/" element={<ProtectedRoute><><MainLayout /><SmsWidget /></></ProtectedRoute>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="overview" element={<OverviewDashboard />} />
          <Route path="roadmap" element={<RoadmapPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="tax" element={<TaxVatPage />} />
          <Route path="speedgo" element={<SpeedGoPage />} />
          <Route path="ownerclan" element={<OwnerclanProductsPage workspace="reserve" />} />
          <Route path="product-processing" element={<OwnerclanProductsPage workspace="processing" />} />
          <Route path="myproduct" element={<ElevenMyProductsPage />} />
          <Route path="myproduct-wholesale" element={<MyProductPage />} />
          <Route path="keyword" element={<Navigate to="/blog" replace />} />
          <Route path="eleven-my" element={<ElevenMyProductsPage />} />
          <Route path="gmarket-my" element={<GmarketMyProductsPage />} />
          <Route path="gmarket" element={<GmarketDashboard />} />
          <Route path="gmarket-adgroup" element={<GmarketAdGroupPage />} />
          <Route path="gmarket-roas" element={<GmarketRoasPage />} />
          <Route path="cpc" element={<CPCDashboard />} />
          <Route path="accounts" element={<AccountListPage />} />
          <Route path="sales" element={<SalesListPage />} />
          <Route path="sales-dashboard" element={<SalesDashboardPage />} />
          <Route path="net-profit" element={<NetProfitPage />} />
          <Route path="sales/upload" element={<SalesUploadPage />} />
          <Route path="sales/match" element={<SalesMatchPage />} />
          <Route path="todos" element={<ProjectListPage />} />
          <Route path="todos/:projectId" element={<KanbanBoard />} />
          <Route path="messaging" element={<ChatPage />} />
          <Route path="email" element={<EmailPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="crawler" element={<CrawlerPage />} />
          <Route path="telegram" element={<TelegramPage />} />
          <Route path="analysis" element={<AnalysisPage />} />
          <Route path="ad-settings" element={<AdSettingsPage />} />
          <Route path="crawler-accounts" element={<CrawlerAccountsPage />} />
          <Route path="st11" element={<St11Dashboard />} />
          <Route path="st11-roas" element={<St11RoasPage />} />
          <Route path="st11-killlist" element={<ElevenKilllistPage />} />
          <Route path="sms" element={<SmsManagePage />} />
          <Route path="lotto" element={<LottoPage />} />
          <Route path="smartstore" element={<SmartStorePage />} />
          <Route path="naver-roas" element={<NaverRoasPage />} />
          <Route path="naver-blog" element={<Navigate to="/blog" replace />} />
          <Route path="blog" element={<NaverBlogPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
