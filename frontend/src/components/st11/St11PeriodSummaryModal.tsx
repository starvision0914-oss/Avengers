import type { St11TotalsSummary } from '../../types/st11';
import type { PeriodMode } from '../../types/cpc';
import { formatKRW } from '../../utils/format';

interface Props {
  totals: St11TotalsSummary;
  periodMode: PeriodMode;
  date: string;
  rangeStart: string;
  rangeEnd: string;
  lastCollected: string;
  onClose: () => void;
}

function periodLabel(periodMode: PeriodMode, date: string, rangeStart: string, rangeEnd: string): string {
  if (periodMode === 'range') return `${rangeStart} ~ ${rangeEnd}`;
  if (periodMode === 'yearly') return `${date.slice(0, 4)}년`;
  if (periodMode === 'monthly') return `${date.slice(0, 4)}년 ${Number(date.slice(5, 7))}월`;
  return date;
}

export default function St11PeriodSummaryModal({ totals, periodMode, date, rangeStart, rangeEnd, lastCollected, onClose }: Props) {
  const sales = totals.sales || 0;
  const cpc = totals.cpc_spend || 0;
  const cost = totals.cost || 0;
  const net = totals.net_profit || 0;
  const roas = cpc > 0 ? Math.round((sales / cpc) * 100) : 0;          // 광고 대비 매출 %
  const adRatio = sales > 0 ? Math.round((cpc / sales) * 1000) / 10 : 0; // 광고비 비중 %
  const margin = sales > 0 ? Math.round((net / sales) * 1000) / 10 : 0;  // 순이익률 %

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/45 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-[640px] max-w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#eee]" style={{ background: '#fff8f1' }}>
          <div className="flex items-center gap-2.5">
            <span className="w-3.5 h-3.5 rounded-sm" style={{ background: '#e67700' }} />
            <div>
              <h2 className="text-[16px] font-bold text-[#222]">11번가 기간 요약</h2>
              <p className="text-[12px] text-[#e67700] font-semibold mt-0.5">{periodLabel(periodMode, date, rangeStart, rangeEnd)}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-[#aaa] hover:text-[#333] text-[22px] leading-none">&times;</button>
        </div>

        <div className="p-6 space-y-5">
          {/* 손익 핵심 4개 */}
          <div className="grid grid-cols-2 gap-3">
            <BigCard label="매출" value={sales} color="#0369a1" bg="#eff6ff" />
            <BigCard label="광고비 (CPC)" value={cpc} color="#e67700" bg="#fff7ed" />
            <BigCard label="구매가 (원가)" value={cost} color="#92400e" bg="#fef9f0" />
            <BigCard label="순수익" value={net} color={net >= 0 ? '#15803d' : '#dc2626'} bg={net >= 0 ? '#f0fdf4' : '#fef2f2'} />
          </div>

          {/* 비율 지표 3개 */}
          <div className="grid grid-cols-3 gap-3">
            <RatioCard label="ROAS" value={`${roas}%`} hint="매출÷광고비" color="#1e6fd9" />
            <RatioCard label="광고비 비중" value={`${adRatio}%`} hint="광고비÷매출" color="#e67700" />
            <RatioCard label="순이익률" value={`${margin}%`} hint="순수익÷매출" color={margin >= 0 ? '#15803d' : '#dc2626'} />
          </div>

          {/* 자금 현황 */}
          <Section title="자금 현황">
            <Row label="셀러캐시" value={formatKRW(totals.cash || 0)} color="#0369a1" />
            <Row label="셀러포인트" value={formatKRW(totals.point || 0)} color="#7c3aed" />
            <Row label="잔액 합계" value={formatKRW(totals.balance || 0)} color="#222" bold />
            <Row label="총 충전" value={formatKRW(totals.charge || 0)} color="#2e7d32" />
          </Section>

          {/* 규모 */}
          <Section title="규모">
            <Row label="셀러 수" value={`${totals.seller_count}개`} color="#222" />
            <Row label="상품 수" value={`${(totals.products || 0).toLocaleString()} / ${(totals.product_limit || 0).toLocaleString()}`} color="#222"
              suffix={<span className="text-[#00a651] text-[11px] ml-1">여유 {(totals.available || 0).toLocaleString()}</span>} />
          </Section>
        </div>

        <div className="px-6 py-3 border-t border-[#eee] flex items-center justify-between">
          <span className="text-[11px] text-[#999]">{lastCollected ? `최종수집 ${lastCollected}` : '11번가 전체 합계'}</span>
          <button onClick={onClose} className="px-5 py-1.5 bg-[#e67700] text-white rounded-md font-semibold text-[12px] hover:bg-[#bf5600]">닫기</button>
        </div>
      </div>
    </div>
  );
}

function BigCard({ label, value, color, bg }: { label: string; value: number; color: string; bg: string }) {
  return (
    <div className="rounded-xl px-4 py-3.5" style={{ background: bg }}>
      <div className="text-[12px] text-[#666] mb-1">{label}</div>
      <div className="text-[20px] font-bold tabular-nums" style={{ color }}>{formatKRW(value)}</div>
    </div>
  );
}

function RatioCard({ label, value, hint, color }: { label: string; value: string; hint: string; color: string }) {
  return (
    <div className="rounded-xl border border-[#eee] px-3 py-2.5 text-center">
      <div className="text-[11px] text-[#888]">{label}</div>
      <div className="text-[18px] font-bold tabular-nums my-0.5" style={{ color }}>{value}</div>
      <div className="text-[10px] text-[#bbb]">{hint}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[12px] font-bold text-[#333] mb-1.5">{title}</div>
      <div className="rounded-xl border border-[#eee] divide-y divide-[#f3f3f3]">{children}</div>
    </div>
  );
}

function Row({ label, value, color, bold, suffix }: { label: string; value: string; color: string; bold?: boolean; suffix?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-4 py-2">
      <span className="text-[12px] text-[#666]">{label}</span>
      <span className="tabular-nums" style={{ color, fontWeight: bold ? 700 : 600, fontSize: 13 }}>{value}{suffix}</span>
    </div>
  );
}
