import { Package, CheckCircle2, AlertCircle, XCircle, Edit3, RefreshCw } from 'lucide-react';
import type { ProductStats } from '../../api/ownerclan';
import { themeStyles, fmt } from './constants';

interface Props {
  dark: boolean;
  stats: ProductStats | null;
  activeFilter?: { saleStatus?: number; isSynced?: number };
  onCardClick?: (key: 'all' | 'selling' | 'soldout' | 'discontinued' | 'changed' | 'unsynced') => void;
}

export default function OwnerclanStatCards({ dark, stats, activeFilter, onCardClick }: Props) {
  const cards = [
    { key: 'all', label: '전체', value: stats?.total ?? 0, color: '#2563eb', icon: Package, active: !activeFilter?.saleStatus && activeFilter?.isSynced === undefined },
    { key: 'selling', label: '판매중', value: stats?.selling ?? 0, color: '#16a34a', icon: CheckCircle2, active: activeFilter?.saleStatus === 1 },
    { key: 'soldout', label: '품절', value: stats?.soldout ?? 0, color: '#f59e0b', icon: AlertCircle, active: activeFilter?.saleStatus === 2 },
    { key: 'discontinued', label: '단종', value: stats?.discontinued ?? 0, color: '#dc2626', icon: XCircle, active: activeFilter?.saleStatus === 3 },
    { key: 'changed', label: '변경됨', value: stats?.changed ?? 0, color: '#ff5a2e', icon: Edit3, active: activeFilter?.isSynced === 0 },
    { key: 'unsynced', label: '미동기화', value: stats?.unsynced ?? 0, color: '#8b5cf6', icon: RefreshCw, active: false },
  ] as const;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
      {cards.map(c => (
        <StatCard
          key={c.key}
          dark={dark}
          label={c.label}
          value={c.value}
          color={c.color}
          Icon={c.icon}
          active={c.active}
          onClick={() => onCardClick?.(c.key)}
        />
      ))}
    </div>
  );
}

function StatCard({
  dark, label, value, color, Icon, active, onClick,
}: {
  dark: boolean; label: string; value: number; color: string; Icon: any; active?: boolean; onClick?: () => void;
}) {
  const s = themeStyles(dark);
  return (
    <button
      onClick={onClick}
      className={`text-left rounded-xl border ${s.card} p-3 md:p-4 transition-all hover:scale-[1.02] cursor-pointer`}
      style={active ? { boxShadow: `inset 0 0 0 1.5px ${color}` } : undefined}
    >
      <div className="flex items-start justify-between">
        <div className={`text-[10px] md:text-[11px] font-medium ${s.text3}`}>{label}</div>
        <Icon size={14} style={{ color }} />
      </div>
      <div className="text-[12px] md:text-[22px] font-bold mt-1 flex items-baseline gap-1" style={{ color }}>
        {fmt(value)}
        <span className={`text-[10px] ${s.text3}`}>개</span>
      </div>
    </button>
  );
}
