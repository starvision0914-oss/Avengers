import { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, BarChart3, Users, ShoppingCart, CheckSquare,
  MessageCircle, Mail, Settings, LogOut, Bot, PieChart, MessageSquare,
  Sliders, Smartphone, Leaf, UserCog, Store, Package, MoreHorizontal,
  BadgeCheck, Tags, ShoppingBag, Dices, Layers, Map, Receipt,
} from 'lucide-react';
import { logout } from '../../api/auth';

const primary = [
  { to: '/overview', icon: Layers, label: '통합현황' },
  { to: '/ownerclan', icon: Package, label: '예비상품' },
  { to: '/myproduct', icon: BadgeCheck, label: '나의 상품' },
  { to: '/gmarket-my', icon: ShoppingBag, label: '지마켓상품' },
  { to: '/st11', icon: Store, label: '11번가' },
  { to: '/gmarket', icon: Store, label: '지마켓' },
  { to: '/smartstore', icon: ShoppingCart, label: '스스' },
  { to: '/cpc', icon: BarChart3, label: 'CPC' },
  { to: '/sales', icon: ShoppingCart, label: '매출' },
  { to: '/tax', icon: Receipt, label: '세무' },
  { to: '/analysis', icon: PieChart, label: '분석' },
  { to: '/ad-settings', icon: Sliders, label: '광고설정' },
  { to: '/speedgo', icon: Leaf, label: '스피드고' },
  { to: '/keyword', icon: Tags, label: '키워드추출기' },
];

const more = [
  { to: '/dashboard', icon: LayoutDashboard, label: '대시보드' },
  { to: '/roadmap', icon: Map, label: '개발로드맵' },
  { to: '/eleven-my', icon: ShoppingBag, label: '11번가 나의 상품' },
  { to: '/accounts', icon: Users, label: '판매자 계정' },
  { to: '/crawler-accounts', icon: UserCog, label: 'ID 관리' },
  { to: '/crawler', icon: Bot, label: '크롤러' },
  { to: '/sms', icon: Smartphone, label: '문자 관리' },
  { to: '/messaging', icon: MessageCircle, label: '메시지' },
  { to: '/email', icon: Mail, label: '이메일' },
  { to: '/telegram', icon: MessageSquare, label: '텔레그램' },
  { to: '/todos', icon: CheckSquare, label: '할 일' },
  { to: '/lotto', icon: Dices, label: '로또 예측' },
  { to: '/settings', icon: Settings, label: '설정' },
];

export default function TopNav() {
  const navigate = useNavigate();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!moreOpen) return;
    const onClick = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) setMoreOpen(false);
    };
    setTimeout(() => window.addEventListener('mousedown', onClick), 0);
    return () => window.removeEventListener('mousedown', onClick);
  }, [moreOpen]);

  const handleLogout = () => { logout(); navigate('/login'); };

  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold whitespace-nowrap transition-all ${
      isActive
        ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30'
        : 'text-gray-300 hover:bg-gray-800 hover:text-white'
    }`;

  return (
    <header className="sticky top-0 z-40 bg-gray-900 border-b border-gray-800 shadow-lg">
      <div className="px-4 h-14 flex items-center gap-3">
        <NavLink to="/dashboard" className="flex items-center gap-2 mr-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center font-bold text-white text-[12px]">A</div>
          <span className="text-white font-bold text-[12px] hidden sm:inline">Avengers</span>
        </NavLink>

        <nav className="flex items-center gap-1 flex-1 overflow-x-auto scrollbar-hide">
          {primary.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} className={linkCls}>
              <Icon size={14} />
              <span>{label}</span>
            </NavLink>
          ))}

          <div className="relative" ref={moreRef}>
            <button
              onClick={() => setMoreOpen(o => !o)}
              className={`inline-flex items-center gap-1 px-2 py-2 rounded-lg text-[12px] font-semibold whitespace-nowrap transition-all ${
                moreOpen ? 'bg-gray-700 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <MoreHorizontal size={14} />
              <span>더보기</span>
            </button>
            {moreOpen && (
              <div className="absolute top-full right-0 mt-1 w-52 rounded-xl border border-gray-700 bg-gray-900 shadow-2xl py-1.5 z-50">
                {more.map(({ to, icon: Icon, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={() => setMoreOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center gap-2.5 px-3 py-2 text-[12px] ${
                        isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-800'
                      }`
                    }
                  >
                    <Icon size={14} />
                    {label}
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        </nav>

        <button
          onClick={handleLogout}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold text-gray-400 hover:text-white hover:bg-gray-800 whitespace-nowrap"
        >
          <LogOut size={14} />
          <span className="hidden sm:inline">로그아웃</span>
        </button>
      </div>
    </header>
  );
}
