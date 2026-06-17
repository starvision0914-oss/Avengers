import { useState } from 'react';
import type { TotalsSummary, Last15MinResponse, TelegramMode, PeriodMode } from '../../types/cpc';
import { formatKRW } from '../../utils/format';
import PeriodSelector from './PeriodSelector';

const TG_SHORT: Record<TelegramMode, string> = {
  off: 'OFF', change: '변동', '15m': '15분', '1h': '1시간',
};

interface Props {
  totals: TotalsSummary;
  delta: Last15MinResponse;
  lastCollected: string;
  tgMode: TelegramMode;
  onTgModeChange: (mode: TelegramMode) => void;
  tgStatus: string;
  onManualSend: () => void;
  periodMode: PeriodMode;
  onPeriodChange: (mode: PeriodMode) => void;
  onExcelDownload?: () => void;
  onAiManage?: () => void;
  onCpc2Manage?: () => void;
  onSellerGrade?: () => void;
}

export default function SummaryBar({ totals, delta, lastCollected, tgMode, onTgModeChange, tgStatus, onManualSend, periodMode, onPeriodChange, onExcelDownload, onAiManage, onCpc2Manage, onSellerGrade }: Props) {
  const np = totals.net_profit;
  const isDaily = periodMode === 'daily';
  const [tgOpen, setTgOpen] = useState(false);

  return (
    <div className="bg-white border border-[#e0e0e0] rounded">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 px-4 md:px-5 py-2.5 md:py-3 border-b border-[#eee] text-[12px] md:text-[12px]">
        <span>
          <span className="text-[#888] mr-1">매출:</span>
          <span className="font-bold text-[#222]">{formatKRW(totals.sales)}</span>
          <span className="text-[#999] text-[10px] ml-1">({totals.sales_count}건)</span>
        </span>
        <Sep />
        <span>
          <span className="text-[#888] mr-1">원가:</span>
          <span className="font-bold text-[#222]">{formatKRW(totals.cost)}</span>
        </span>
        <Sep />
        <span>
          <span className="text-[#888] mr-1">이익:</span>
          <span className="font-bold text-[#222]">{formatKRW(totals.profit)}원</span>
        </span>
        <Sep />
        <span>
          <span className="text-[#888] mr-1">순이익:</span>
          <span className={`font-bold ${np >= 0 ? 'text-[#00a651]' : 'text-[#e04040] font-extrabold'}`}>{formatKRW(np)}원</span>
        </span>
        <span className="ml-auto flex items-center gap-2">
          {onSellerGrade && (
            <button onClick={onSellerGrade} className="px-3 py-1 text-[11px] font-semibold bg-[#555] text-white rounded hover:bg-[#444]">등급</button>
          )}
          {onAiManage && (
            <button onClick={onAiManage} className="px-3 py-1 text-[11px] font-semibold bg-[#7c3aed] text-white rounded hover:bg-[#6d28d9]">AI관리</button>
          )}
          {onCpc2Manage && (
            <button onClick={onCpc2Manage} className="px-3 py-1 text-[11px] font-semibold bg-[#0284c7] text-white rounded hover:bg-[#0369a1]">간편광고</button>
          )}
          {onExcelDownload && (
            <button onClick={onExcelDownload} className="px-3 py-1 text-[11px] font-semibold bg-[#217346] text-white rounded hover:bg-[#1a5c38]">Excel</button>
          )}
          <PeriodSelector value={periodMode} onChange={onPeriodChange} />
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 px-4 md:px-5 py-2 md:py-2.5 text-[11px] md:text-[12px]">
        {isDaily ? (
          <>
            <DeltaItem label="총CPC" value={totals.cpc_spend} delta={delta.cpc_delta} />
            <Sep />
            <DeltaItem label="총AI" value={totals.ai_spend} delta={delta.ai_delta} />
            <Sep />
            <DeltaItem label="프라임" value={totals.prime_spend} delta={delta.prime_delta} />
            <Sep />
            <DeltaItem label="총광고비" value={totals.ad_total} delta={delta.ad_delta} />
          </>
        ) : (
          <>
            <Item label="총CPC" value={totals.cpc_spend} />
            <Sep />
            <Item label="총AI" value={totals.ai_spend} />
            <Sep />
            <Item label="프라임" value={totals.prime_spend} />
            <Sep />
            <Item label="총광고비" value={totals.ad_total} />
          </>
        )}
        <span className="ml-auto flex items-center gap-2">
          {lastCollected && (
            <span className="text-[10px] text-[#999]">수집: <span className="text-[#666] font-medium">{lastCollected}</span></span>
          )}
          <div className="relative">
            <button onClick={() => setTgOpen(!tgOpen)}
              className={`flex items-center gap-1 px-2 py-[3px] rounded border text-[10px] font-bold ${
                tgMode === 'off' ? 'border-[#ddd] text-[#999] bg-[#f5f5f5]' : 'border-[#4dabf7] text-[#228be6] bg-[#e7f5ff]'
              }`}>
              TG {TG_SHORT[tgMode]}
            </button>
            {tgOpen && (
              <div className="absolute right-0 top-full mt-1 bg-white border border-[#ddd] rounded-lg shadow-lg p-3 z-50 min-w-[180px]">
                <div className="text-[11px] font-bold text-[#333] mb-2">텔레그램 알림</div>
                {(['off', 'change', '15m', '1h'] as TelegramMode[]).map(m => (
                  <label key={m} className="flex items-center gap-2 text-[11px] py-1 cursor-pointer hover:bg-[#f5f5f5] px-1 rounded">
                    <input type="radio" name="tg" checked={tgMode === m} onChange={() => { onTgModeChange(m); setTgOpen(false); }} className="w-3.5 h-3.5" />
                    {TG_SHORT[m]}
                  </label>
                ))}
                <button onClick={() => { onManualSend(); setTgOpen(false); }}
                  className="mt-2 w-full px-3 py-1.5 bg-[#228be6] text-white text-[11px] font-semibold rounded hover:bg-[#1971c2]">
                  즉시 전송
                </button>
              </div>
            )}
          </div>
          {tgStatus && <span className="text-[10px] text-[#228be6] font-medium animate-pulse">{tgStatus}</span>}
        </span>
      </div>
    </div>
  );
}

function Item({ label, value }: { label: string; value: number }) {
  return (
    <span>
      <span className="text-[#888] mr-1">{label}:</span>
      <span className="font-bold text-[#222]">{formatKRW(value)}</span>
    </span>
  );
}

function DeltaItem({ label, value, delta }: { label: string; value: number; delta: number }) {
  return (
    <span>
      <span className="text-[#888] mr-1">{label}:</span>
      <span className="font-bold text-[#222]">{formatKRW(value)}</span>
      <span className={`text-[10px] font-semibold ml-1 ${delta > 0 ? 'text-[#e08000]' : 'text-[#bbb]'}`}>({formatKRW(delta)})</span>
    </span>
  );
}

function Sep() {
  return <span className="text-[#ddd] hidden md:inline">|</span>;
}
