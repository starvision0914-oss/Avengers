import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, BarChart3, Users, ShoppingCart, CheckSquare, MessageCircle, Mail, Settings, LogOut, Bot, PieChart, MessageSquare, Sliders, Smartphone, Leaf, UserCog, Store, Package, BadgeCheck, Tags, Layers, Map, Receipt, TrendingUp, Wrench } from 'lucide-react';
import { logout } from '../../api/auth';

const navItems = [
  { to: '/overview', icon: Layers, label: '통합현황' },
  { to: '/roadmap', icon: Map, label: '개발로드맵' },
  { to: '/dashboard', icon: LayoutDashboard, label: '대시보드' },
  { to: '/speedgo', icon: Leaf, label: '스피드고' },
  { to: '/ownerclan', icon: Package, label: '예비상품' },
  { to: '/product-processing', icon: Wrench, label: '상품가공' },
  { to: '/myproduct', icon: BadgeCheck, label: '나의 상품' },
  { to: '/gmarket-my', icon: Store, label: '지마켓 상품' },
  { to: '/gmarket-roas', icon: TrendingUp, label: '지마켓/옥션 ROAS' },
  { to: '/st11', icon: Store, label: '11번가' },
  { to: '/st11-killlist', icon: TrendingUp, label: '11번가 광고킬' },
  { to: '/cpc', icon: BarChart3, label: 'CPC 광고비' },
  { to: '/accounts', icon: Users, label: '판매자 계정' },
  { to: '/sales-dashboard', icon: ShoppingCart, label: '매출 대시보드' },
  { to: '/net-profit', icon: TrendingUp, label: '전체몰 순수익' },
  { to: '/sales', icon: ShoppingCart, label: '매출 데이터' },
  { to: '/tax', icon: Receipt, label: '세무(부가세)' },
  { to: '/todos', icon: CheckSquare, label: '할 일' },
  { to: '/messaging', icon: MessageCircle, label: '메시지' },
  { to: '/sms', icon: Smartphone, label: '문자 관리' },
  { to: '/email', icon: Mail, label: '이메일' },
  { to: '/crawler', icon: Bot, label: '크롤러' },
  { to: '/crawler-accounts', icon: UserCog, label: 'ID 관리' },
  { to: '/analysis', icon: PieChart, label: '분석' },
  { to: '/telegram', icon: MessageSquare, label: '텔레그램' },
  { to: '/ad-settings', icon: Sliders, label: '광고 설정' },
  { to: '/settings', icon: Settings, label: '설정' },
  { to: '/keyword', icon: Tags, label: '키워드추출기' },
];

export default function Sidebar() {
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="w-60 bg-gray-900 text-white flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-xl font-bold">Avengers</h1>
        <p className="text-xs text-gray-400 mt-1">업무 관리 시스템</p>
      </div>
      <nav className="flex-1 py-4">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-800'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
      <button
        onClick={handleLogout}
        className="flex items-center gap-3 px-4 py-3 text-sm text-gray-400 hover:text-white hover:bg-gray-800 border-t border-gray-700"
      >
        <LogOut size={18} />
        로그아웃
      </button>
    </aside>
  );
}
