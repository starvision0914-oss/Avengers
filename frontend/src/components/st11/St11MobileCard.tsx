import type { St11SellerRow } from '../../types/st11';
import { formatKRW } from '../../utils/format';

interface Props {
  seller: St11SellerRow;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
  onCostClick: (sellerId: string, alias: string) => void;
}

export default function St11MobileCard({ seller: s, index, isSelected, onSelect, onCostClick }: Props) {
  const lowAvail = (s.available || 0) > 0 && (s.available || 0) < 100;

  return (
    <div
      onClick={onSelect}
      className={`p-3 border-b border-[#eee] cursor-pointer transition-colors active:bg-[#fff3e0] ${isSelected ? 'bg-[#fff3e0]' : 'bg-white'}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="flex flex-col">
          <span className="text-[12px] font-bold text-[#222]">{index}. {s.seller_alias}</span>
          <span className="text-[10px] text-[#aaa]">{s.seller_id}</span>
        </span>
        <span className="flex items-center gap-2 text-[11px]">
          {s.grade != null && <GradeChip grade={s.grade} />}
          {(s.cash || 0) > 0 && <span className="text-[#0369a1] font-bold">캐시 {formatKRW(s.cash!)}</span>}
          {(s.point || 0) > 0 && <span className="text-[#7c3aed] font-bold">PT {formatKRW(s.point!)}</span>}
        </span>
      </div>
      <div className="flex items-center gap-3 text-[11px] mb-1.5">
        <span>
          <span className="text-[#999]">상품 </span>
          <span className="text-[#333] font-semibold">{(s.products || 0).toLocaleString()}</span>
          <span className="text-[#999]">/{(s.product_limit || 0).toLocaleString()}</span>
        </span>
        <span className={lowAvail ? 'text-[#dc2626] font-bold' : ''}>
          <span className="text-[#999]">여유 </span>
          <span className={`font-semibold ${lowAvail ? 'text-[#dc2626]' : 'text-[#00a651]'}`}>{(s.available || 0).toLocaleString()}</span>
        </span>
        {s.fulfillment && (
          <span className="text-[10px]">
            <GradeDot v={s.fulfillment} /><GradeDot v={s.shipping} /><GradeDot v={s.inquiry} />
          </span>
        )}
      </div>
      <div className="flex items-center gap-3 text-[11px]">
        <span onClick={e => { e.stopPropagation(); onCostClick(s.seller_id, s.seller_alias); }}>
          <span className="text-[#999]">CPC </span>
          <span className={s.cpc_spend > 0 ? 'text-[#e67700] font-semibold' : 'text-[#ccc]'}>{formatKRW(s.cpc_spend)}</span>
        </span>
        <span>
          <span className="text-[#999]">충전 </span>
          <span className={s.charge > 0 ? 'text-[#2e7d32] font-semibold' : 'text-[#ccc]'}>{formatKRW(s.charge)}</span>
        </span>
        <span className="ml-auto text-[10px] text-[#aaa]">
          {s.crawling_status === '정상' ? '정상' : s.crawling_status === '차단됨' ? '차단' : s.crawling_status || ''}
        </span>
      </div>
    </div>
  );
}

function GradeDot({ v }: { v?: string }) {
  if (!v) return null;
  const c = v === '우수' ? '#00a651' : v === '경고' ? '#dc2626' : v === '주의' ? '#e67700' : '#bbb';
  return <span className="inline-block w-2 h-2 rounded-full mr-0.5" style={{ background: c }} title={v} />;
}

const GRADE_COLORS: Record<number, { bg: string; text: string }> = {
  1: { bg: '#fef2f2', text: '#dc2626' },
  2: { bg: '#fff3e0', text: '#e67700' },
  3: { bg: '#e7f5ff', text: '#1a73e8' },
  4: { bg: '#f0fdf4', text: '#16a34a' },
  5: { bg: '#f0fdf4', text: '#00a651' },
};

function GradeChip({ grade }: { grade: number }) {
  const c = GRADE_COLORS[grade] || { bg: '#f5f5f5', text: '#999' };
  return (
    <span className="px-1.5 py-0 rounded text-[10px] font-bold" style={{ background: c.bg, color: c.text }}>
      {grade}등급
    </span>
  );
}
