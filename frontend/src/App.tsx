import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { isAuthenticated } from './api/auth';
import MainLayout from './components/Layout/MainLayout';
import LoginPage from './pages/Auth/LoginPage';
import SmsWidget from './components/SmsWidget';

const SpeedGoPage = lazy(() => import('./pages/SpeedGo/SpeedGoPage'));
const AccountListPage = lazy(() => import('./pages/Accounts/AccountListPage'));
const SalesListPage = lazy(() => import('./pages/Sales/SalesListPage'));
const SalesDashboardPage = lazy(() => import('./pages/Sales/SalesDashboardPage'));
const NetProfitPage = lazy(() => import('./pages/Sales/NetProfitPage'));
const ElevenKilllistPage = lazy(() => import('./pages/St11/ElevenKilllistPage'));
const SalesUploadPage = lazy(() => import('./pages/Sales/SalesUploadPage'));
const KanbanBoard = lazy(() => import('./pages/Todos/KanbanBoard'));
const ProjectListPage = lazy(() => import('./pages/Todos/ProjectListPage'));
const ChatPage = lazy(() => import('./pages/Messaging/ChatPage'));
const EmailPage = lazy(() => import('./pages/Email/EmailPage'));
const SettingsPage = lazy(() => import('./pages/Settings/SettingsPage'));
const CrawlerPage = lazy(() => import('./pages/Crawler/CrawlerPage'));
const TelegramPage = lazy(() => import('./pages/Telegram/TelegramPage'));
const AdSettingsPage = lazy(() => import('./pages/AdSettings/AdSettingsPage'));
const CrawlerAccountsPage = lazy(() => import('./pages/CrawlerAccounts/CrawlerAccountsPage'));
const St11Dashboard = lazy(() => import('./pages/St11/St11Dashboard'));
const St11RoasPage = lazy(() => import('./pages/St11/St11RoasPage'));
const SmsManagePage = lazy(() => import('./pages/Sms/SmsManagePage'));
const OwnerclanProductsPage = lazy(() => import('./pages/Ownerclan/OwnerclanProductsPage'));
const MyProductPage = lazy(() => import('./pages/MyProduct/MyProductPage'));
const ElevenMyProductsPage = lazy(() => import('./pages/ElevenMy/ElevenMyProductsPage'));
const GmarketDashboard = lazy(() => import('./pages/Gmarket/GmarketDashboard'));
const GmarketAdGroupPage = lazy(() => import('./pages/Gmarket/GmarketAdGroupPage'));
const GmarketRoasPage = lazy(() => import('./pages/Gmarket/GmarketRoasPage'));
const LottoPage = lazy(() => import('./pages/Lotto/LottoPage'));
const OverviewDashboard = lazy(() => import('./pages/Overview/OverviewDashboard'));
const RoadmapPage = lazy(() => import('./pages/Roadmap/RoadmapPage'));
const SalesMatchPage = lazy(() => import('./pages/Sales/SalesMatchPage'));
const TaxVatPage = lazy(() => import('./pages/Tax/TaxVatPage'));
const SmartStorePage = lazy(() => import('./pages/SmartStore/SmartStorePage'));
const NaverRoasPage = lazy(() => import('./pages/SmartStore/NaverRoasPage'));
const OwnerclanCrawlerPage = lazy(() => import('./pages/Ownerclan/OwnerclanCrawlerPage'));
const NaverBlogPage = lazy(() => import('./pages/NaverBlog/NaverBlogPage'));
const TistoryPage = lazy(() => import('./pages/Tistory/TistoryPage'));
const TossDashboard = lazy(() => import('./pages/Toss/TossDashboard'));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function PageLoading() {
  return (
    <div className="flex items-center justify-center h-[60vh] text-[13px] text-gray-400">
      불러오는 중...
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<ProtectedRoute><><MainLayout /><SmsWidget /></></ProtectedRoute>}>
            <Route index element={<Navigate to="/overview" replace />} />
            <Route path="overview" element={<OverviewDashboard />} />
            <Route path="roadmap" element={<RoadmapPage />} />
            <Route path="dashboard" element={<Navigate to="/overview" replace />} />
            <Route path="tax" element={<TaxVatPage />} />
            <Route path="speedgo" element={<SpeedGoPage />} />
            <Route path="ownerclan" element={<OwnerclanProductsPage workspace="reserve" />} />
            <Route path="product-processing" element={<OwnerclanProductsPage workspace="processing" />} />
            <Route path="myproduct" element={<ElevenMyProductsPage />} />
            <Route path="myproduct-wholesale" element={<MyProductPage />} />
            <Route path="keyword" element={<Navigate to="/blog" replace />} />
            <Route path="eleven-my" element={<Navigate to="/myproduct" replace />} />
            <Route path="gmarket-my" element={<Navigate to="/myproduct" replace />} />
            <Route path="gmarket" element={<GmarketDashboard />} />
            <Route path="coupang" element={<Navigate to="/smartstore" replace />} />
            <Route path="lotteon" element={<Navigate to="/smartstore" replace />} />
            <Route path="gmarket-adgroup" element={<GmarketAdGroupPage />} />
            <Route path="gmarket-roas" element={<GmarketRoasPage />} />
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
            <Route path="ad-settings" element={<AdSettingsPage />} />
            <Route path="crawler-accounts" element={<CrawlerAccountsPage />} />
            <Route path="st11" element={<St11Dashboard />} />
            <Route path="st11-roas" element={<St11RoasPage />} />
            <Route path="st11-killlist" element={<ElevenKilllistPage />} />
            <Route path="sms" element={<SmsManagePage />} />
            <Route path="lotto" element={<LottoPage />} />
            <Route path="smartstore" element={<SmartStorePage />} />
            <Route path="naver-roas" element={<NaverRoasPage />} />
            <Route path="naver-blog" element={<NaverBlogPage />} />
            <Route path="tistory" element={<TistoryPage />} />
            <Route path="toss" element={<TossDashboard />} />
            <Route path="blog" element={<Navigate to="/owner" replace />} />
            <Route path="owner" element={<OwnerclanCrawlerPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
