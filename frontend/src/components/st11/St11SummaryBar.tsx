import type { St11TotalsSummary, St11Last15MinResponse } from '../../types/st11';
import type { PeriodMode } from '../../types/cpc';
import { formatKRW } from '../../utils/format';
import PeriodSelector from '../cpc/PeriodSelector';

interface Props {
  totals: St11TotalsSummary;
  delta: St11Last15MinResponse;
  lastCollected: string;
  periodMode: PeriodMode;
  onPeriodChange: (mode: PeriodMode) => void;
  onRefresh?: () => void;
}

export default function St11SummaryBar({ totals, delta, lastCollected, periodMode, onPeriodChange, onRefresh }: Props) {
  const isDaily = periodMode === 'daily';

  return (
    <div className="bg-white border border-[#e0e0e0] rounded">
      {/* 한 줄로 통합 (자금 + 광고비/매출/순수익) */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 px-4 md:px-5 py-2 md:py-2.5 text-[12px] md:text-[12px]">
        <span>
          <span className="text-[#888] mr-1">셀러캐시:</span>
          <span className="font-bold text-[#0369a1]">{formatKRW(totals.cash)}</span>
        </span>
        <Sep />
        <span>
          <span className="text-[#888] mr-1">셀러포인트:</span>
          <span className="font-bold text-[#7c3aed]">{formatKRW(totals.point)}</span>
        </span>
        <Sep />
        <span>
          <span className="text-[#888] mr-1">잔액합계:</span>
          <span className="font-bold text-[#222]">{formatKRW(totals.balance)}</span>
        </span>
        <Sep />
        <span>
          <span className="text-[#888] mr-1">상품:</span>
          <span className="font-bold text-[#333]">{totals.products.toLocaleString()}</span>
          <span className="text-[#999] text-[10px] ml-1">/{totals.product_limit.toLocaleString()}</span>
          <span className="text-[#00a651] text-[10px] ml-1">(여유 {totals.available.toLocaleString()})</span>
        </span>
        <Sep />
        {isDaily
          ? <DeltaItem label="총CPC" value={totals.cpc_spend} delta={delta.cpc_delta} />
          : <Item label="총CPC" value={totals.cpc_spend} />}
        <Sep />
        <span>
          <span className="text-[#888] mr-1">총충전:</span>
          <span className="font-bold text-[#2e7d32]">{formatKRW(totals.charge)}</span>
        </span>
        <Sep />
        <span>
          <span className="text-[#888] mr-1">매출:</span>
          <span className="font-bold text-[#0369a1]">{formatKRW(totals.sales || 0)}</span>
        </span>
        <Sep />
        <span>
          <span className="text-[#888] mr-1">구매가:</span>
          <span className="font-bold text-[#92400e]">{formatKRW(totals.cost || 0)}</span>
        </span>
        <Sep />
        <span>
          <span className="text-[#888] mr-1">순수익:</span>
          <span className="font-bold" style={{ color: (totals.net_profit || 0) >= 0 ? '#15803d' : '#dc2626' }}>{formatKRW(totals.net_profit || 0)}</span>
        </span>
        <Sep />
        <Item label="셀러수" value={totals.seller_count} plain />
        <span className="ml-auto flex items-center gap-2">
          {lastCollected && (
            <span className="text-[10px] text-[#999]">수집 {lastCollected}</span>
          )}
          {onRefresh && (
            <button onClick={onRefresh} className="px-3 py-1 text-[11px] font-semibold bg-[#e67700] text-white rounded hover:bg-[#bf5600]">새로고침</button>
          )}
          <PeriodSelector value={periodMode} onChange={onPeriodChange} />
        </span>
      </div>
    </div>
  );
}

function Item({ label, value, plain }: { label: string; value: number; plain?: boolean }) {
  return (
    <span>
      <span className="text-[#888] mr-1">{label}:</span>
      {plain
        ? <span className="font-bold text-[#222]">{value}</span>
        : <span className="font-bold text-[#e67700]">{formatKRW(value)}</span>
      }
    </span>
  );
}

function DeltaItem({ label, value, delta }: { label: string; value: number; delta: number }) {
  return (
    <span>
      <span className="text-[#888] mr-1">{label}:</span>
      <span className="font-bold text-[#e67700]">{formatKRW(value)}</span>
      <span className={`text-[10px] font-semibold ml-1 ${delta > 0 ? 'text-[#e08000]' : 'text-[#bbb]'}`}>({formatKRW(delta)})</span>
    </span>
  );
}

function Sep() {
  return <span className="text-[#ddd] hidden md:inline">|</span>;
}
