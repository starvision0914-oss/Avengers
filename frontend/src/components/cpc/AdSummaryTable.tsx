import { useState } from 'react';
import type { SellerRow, TotalsSummary, AiAdStatus } from '../../types/cpc';
import { formatKRW, isOverdue90, feeDateSuffix } from '../../utils/format';

interface Props {
  sellers: SellerRow[];
  totals: TotalsSummary;
  selectedSeller: string | null;
  onSelectSeller: (id: string | null) => void;
  onAiClick: (sellerId: string, alias: string) => void;
  onCostClick: (sellerId: string, alias: string, category?: string) => void;
  onSalesClick?: (sellerAlias: string, monthly?: boolean) => void;
  blockedIds?: Set<string>;
  onDismissBlocked?: (sellerId: string) => void;
}

const TH = 'px-3 py-2 text-[11px] font-semibold text-[#555] bg-[#f7f7f7] border-b border-[#ddd] whitespace-nowrap';
const TD = 'px-3 py-[7px] text-[12.5px] text-right border-b border-[#eee] whitespace-nowrap';
const TD_LEFT = 'px-3 py-[7px] text-[12.5px] text-left border-b border-[#eee] whitespace-nowrap';

function AiBadge({ status, onClick }: { status: AiAdStatus; onClick?: (e: React.MouseEvent) => void }) {
  const btnOn = (status.btn || status.button_status) === 'ON';
  const actualOn = (status.actual || status.actual_status) === 'ON';
  return (
    <span className="ml-1 inline-flex items-center gap-0.5 text-[9px] font-bold cursor-pointer hover:opacity-70" onClick={onClick}>
      <span className={btnOn ? 'text-[#00a651]' : 'text-[#e04040]'}>{status.btn || status.button_status}</span>
      <span className={actualOn ? 'text-[#00a651]' : 'text-[#e04040]'}>({status.actual || status.actual_status})</span>
      {btnOn && (status.start || status.start_date) && (
        <span className="text-[8px] text-[#999] font-normal">{status.start || status.start_date}</span>
      )}
    </span>
  );
}

export default function AdSummaryTable({ sellers, totals, selectedSeller, onSelectSeller, onAiClick, onCostClick, onSalesClick, blockedIds, onDismissBlocked }: Props) {
  const [hideEmpty, setHideEmpty] = useState(false);
  const filtered = hideEmpty ? sellers.filter(s => s.ad_total > 0 || s.sales > 0) : sellers;

  return (
    <div className="bg-white border border-[#e0e0e0] rounded overflow-x-auto">
      <table className="w-full border-collapse" style={{ fontVariantNumeric: 'tabular-nums' }}>
        <thead>
          <tr>
            <th className={`${TH} text-center w-9`}>#</th>
            <th className={`${TH} text-left cursor-pointer select-none hover:text-[#1a73e8]`}
              onClick={() => setHideEmpty(h => !h)} title={hideEmpty ? '전체 보기' : '활동 셀러만'}>
              셀러명 {hideEmpty && <span className="text-[10px] text-[#1a73e8] font-normal ml-1">({filtered.length}개만)</span>}
            </th>
            <th className={`${TH} text-center`} style={{ fontSize: '10px', padding: '4px 2px' }}>광고상태</th>
            <th className={`${TH} text-right`}>매출</th>
            <th className={`${TH} text-right`}>CPC</th>
            <th className={`${TH} text-right`}>AI</th>
            <th className={`${TH} text-right`}>프라임</th>
            <th className={`${TH} text-right`}>광고비합</th>
            <th className={`${TH} text-right`}>원가</th>
            <th className={`${TH} text-right`}>이익</th>
            <th className={`${TH} text-right`}>총수익</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((s, i) => {
            const isSelected = selectedSeller === s.seller_id;
            const lowBalance = s.balance > 0 && s.balance < 100000;
            const netProfit = s.profit - s.ad_total;
            const overdue = isOverdue90(s.server_fee_date);
            const suffix = feeDateSuffix(s.server_fee_date);

            return (
              <tr key={s.seller_id} onClick={() => onSelectSeller(isSelected ? null : s.seller_id)}
                className={`cursor-pointer transition-colors ${isSelected ? 'bg-[#e8f5e9]' : i % 2 === 0 ? 'bg-white' : 'bg-[#fafafa]'} hover:bg-[#f0f7f0]`}>
                <td className={`${TD_LEFT} text-center text-[11px] text-[#999]`}>{i + 1}</td>
                <td className={`${TD_LEFT} font-semibold ${s.grade_info?.max_item_count && s.grade_info.max_item_count >= 10000 ? 'text-[#e04040]' : 'text-[#222]'}`}>
                  <span className="relative group/bal inline-flex items-center">
                    {s.seller_alias}
                    {s.seller_alias !== s.seller_id && (
                      <span className="ml-1 text-[10px] text-[#999] font-normal">({s.seller_id})</span>
                    )}
                    {blockedIds?.has(s.seller_id) && (
                      <span className="ml-1 px-1.5 py-0 text-[9px] font-bold text-white bg-[#dc2626] rounded animate-pulse cursor-pointer hover:bg-[#b91c1c]"
                        onClick={e => { e.stopPropagation(); if (onDismissBlocked && confirm(`${s.seller_alias} 차단 해제?`)) onDismissBlocked(s.seller_id); }}>차단</span>
                    )}
                    {lowBalance && (
                      <>
                        <span className="ml-1 inline-block w-2 h-2 rounded-full bg-[#e04040] animate-pulse" title={`잔액: ${formatKRW(s.balance)}`} />
                        <span className="absolute z-50 hidden group-hover/bal:block bottom-full left-0 mb-1 px-2 py-1 bg-[#333] text-white text-[10px] rounded whitespace-nowrap shadow-lg">
                          잔액: {formatKRW(s.balance)}
                        </span>
                      </>
                    )}
                  </span>
                  {suffix && <span className={`ml-1 text-[10px] font-normal ${overdue ? 'text-[#e04040]' : 'text-[#aaa]'}`}>{suffix}</span>}
                </td>
                <td className="px-1 py-0.5 text-center whitespace-nowrap border-b border-[#eee]">
                  {s.cpc_status ? (
                    <div className="flex items-center justify-center gap-0.5">
                      <span className={`px-1 py-0 text-[9px] font-medium rounded ${s.cpc_status.cpc2_on > 0 ? 'bg-[#e8f5e9] text-[#2e7d32]' : 'bg-[#fbe9e7] text-[#c62828]'}`}>
                        간편 {s.cpc_status.cpc2_on}/{s.cpc_status.cpc2_off}
                      </span>
                      <span className={`px-1 py-0 text-[9px] font-medium rounded ${s.cpc_status.cpc1_on > 0 ? 'bg-[#e3f2fd] text-[#1565c0]' : 'bg-[#fbe9e7] text-[#c62828]'}`}>
                        일반 {s.cpc_status.cpc1_on}/{s.cpc_status.cpc1_off}
                      </span>
                    </div>
                  ) : <span className="text-[9px] text-[#ccc]">-</span>}
                </td>
                <td className={`${TD} ${s.sales > 0 ? 'text-[#333] cursor-pointer hover:underline' : 'text-[#ccc]'}`}
                  onClick={s.sales > 0 && onSalesClick ? e => { e.stopPropagation(); onSalesClick(s.seller_alias); } : undefined}>
                  {s.sales > 0 && <span className="text-[#999] text-[10px] mr-0.5">({s.sales_count}건)</span>}
                  {formatKRW(s.sales)}
                </td>
                <td className={`${TD} ${s.cpc_spend > 0 ? 'text-[#1a73e8]' : 'text-[#ccc]'} cursor-pointer hover:underline`}
                  onClick={e => { e.stopPropagation(); onCostClick(s.seller_id, s.seller_alias, 'CPC'); }}>
                  {formatKRW(s.cpc_spend)}
                </td>
                <td className={`${TD} ${s.ai_spend > 0 ? 'text-[#1a73e8]' : 'text-[#ccc]'} cursor-pointer hover:underline`}
                  onClick={e => { e.stopPropagation(); onCostClick(s.seller_id, s.seller_alias, 'AI'); }}>
                  {formatKRW(s.ai_spend)}
                  {s.ai_status && <AiBadge status={s.ai_status} onClick={e => { e.stopPropagation(); onAiClick(s.seller_id, s.seller_alias); }} />}
                </td>
                <td className={`${TD} ${s.prime_spend > 0 ? 'text-[#1a73e8]' : 'text-[#ccc]'} cursor-pointer hover:underline`}
                  onClick={e => { e.stopPropagation(); onCostClick(s.seller_id, s.seller_alias, '프라임'); }}>
                  {formatKRW(s.prime_spend)}
                </td>
                <td className={`${TD} font-semibold ${s.ad_total > 0 ? 'text-[#1557b0]' : 'text-[#ccc]'}`}>{formatKRW(s.ad_total)}</td>
                <td className={`${TD} ${s.cost > 0 ? 'text-[#333]' : 'text-[#ccc]'}`}>{formatKRW(s.cost)}</td>
                <td className={`${TD} font-semibold ${s.profit > 0 ? 'text-[#00a651]' : 'text-[#ccc]'}`}>{formatKRW(s.profit)}</td>
                <td className={`${TD} font-bold ${netProfit < 0 ? 'text-[#e04040]' : netProfit > 0 ? 'text-[#00a651]' : 'text-[#ccc]'}`}>{formatKRW(netProfit)}</td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="bg-[#f7f7f7] font-bold text-[12.5px] border-t-2 border-[#ddd]">
            <td className={`${TD_LEFT} text-center`} colSpan={3}>
              <span className="text-[#333]">합계</span>
              <span className="ml-2 text-[10px] text-[#999] font-normal">{filtered.length}개</span>
            </td>
            <td className={`${TD} text-[#333]`}>{formatKRW(totals.sales)}</td>
            <td className={`${TD} text-[#1a73e8]`}>{formatKRW(totals.cpc_spend)}</td>
            <td className={`${TD} text-[#1a73e8]`}>{formatKRW(totals.ai_spend)}</td>
            <td className={`${TD} text-[#1a73e8]`}>{formatKRW(totals.prime_spend)}</td>
            <td className={`${TD} text-[#1557b0]`}>{formatKRW(totals.ad_total)}</td>
            <td className={`${TD} text-[#333]`}>{formatKRW(totals.cost)}</td>
            <td className={`${TD} text-[#00a651]`}>{formatKRW(totals.profit)}</td>
            <td className={`${TD} ${totals.net_profit < 0 ? 'text-[#e04040]' : 'text-[#00a651]'}`}>{formatKRW(totals.net_profit)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
