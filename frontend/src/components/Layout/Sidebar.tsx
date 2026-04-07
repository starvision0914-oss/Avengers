import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, BarChart3, Users, ShoppingCart, CheckSquare, MessageCircle, Mail, Settings, LogOut, Bot } from 'lucide-react';
import { logout } from '../../api/auth';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: '대시보드' },
  { to: '/cpc', icon: BarChart3, label: 'CPC 광고비' },
  { to: '/accounts', icon: Users, label: '판매자 계정' },
  { to: '/sales', icon: ShoppingCart, label: '매출 데이터' },
  { to: '/todos', icon: CheckSquare, label: '할 일' },
  { to: '/messaging', icon: MessageCircle, label: '메시지' },
  { to: '/email', icon: Mail, label: '이메일' },
  { to: '/crawler', icon: Bot, label: '크롤러' },
  { to: '/settings', icon: Settings, label: '설정' },
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
