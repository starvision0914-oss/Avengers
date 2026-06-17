import type { SellerRow } from '../../types/cpc';
import { formatKRW } from '../../utils/format';

interface Props {
  seller: SellerRow;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
  onAiClick: (sellerId: string, alias: string) => void;
  onCostClick: (sellerId: string, alias: string, category?: string) => void;
  onSalesClick?: (sellerAlias: string) => void;
}

export default function MobileSellerCard({ seller: s, index, isSelected, onSelect, onAiClick, onCostClick, onSalesClick }: Props) {
  const lowBalance = s.balance > 0 && s.balance < 500000;
  const netProfit = s.profit - s.ad_total;

  return (
    <div onClick={onSelect}
      className={`p-3 border-b border-[#eee] cursor-pointer transition-colors active:bg-[#e8f5e9] ${isSelected ? 'bg-[#e8f5e9]' : 'bg-white'}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[12px] font-bold text-[#222]">{index}. {s.seller_alias}</span>
        <span className={`text-[12px] font-bold ${lowBalance ? 'text-[#e08000]' : 'text-[#333]'}`}
          onClick={e => { e.stopPropagation(); onCostClick(s.seller_id, s.seller_alias); }}>
          잔액 {formatKRW(s.balance)}
        </span>
      </div>
      <div className="flex items-center gap-3 text-[11px] mb-1.5">
        <span onClick={e => { e.stopPropagation(); onCostClick(s.seller_id, s.seller_alias, 'CPC'); }}>
          <span className="text-[#999]">CPC </span>
          <span className={s.cpc_spend > 0 ? 'text-[#1a73e8] font-semibold' : 'text-[#ccc]'}>{formatKRW(s.cpc_spend)}</span>
        </span>
        <span onClick={e => { e.stopPropagation(); onCostClick(s.seller_id, s.seller_alias, 'AI'); }}>
          <span className="text-[#999]">AI </span>
          <span className={s.ai_spend > 0 ? 'text-[#1a73e8] font-semibold' : 'text-[#ccc]'}>{formatKRW(s.ai_spend)}</span>
          {s.ai_status && (() => {
            const btnOn = (s.ai_status.btn || s.ai_status.button_status) === 'ON';
            const actOn = (s.ai_status.actual || s.ai_status.actual_status) === 'ON';
            return (
              <span className="ml-0.5 text-[9px] font-bold" onClick={e => { e.stopPropagation(); onAiClick(s.seller_id, s.seller_alias); }}>
                <span className={btnOn ? 'text-[#00a651]' : 'text-[#e04040]'}>{s.ai_status.btn || s.ai_status.button_status}</span>
                <span className={actOn ? 'text-[#00a651]' : 'text-[#e04040]'}>({s.ai_status.actual || s.ai_status.actual_status})</span>
              </span>
            );
          })()}
        </span>
        <span>
          <span className="text-[#999]">합 </span>
          <span className={s.ad_total > 0 ? 'text-[#1557b0] font-bold' : 'text-[#ccc]'}>{formatKRW(s.ad_total)}</span>
        </span>
      </div>
      <div className="flex items-center gap-3 text-[11px]">
        <span onClick={s.sales > 0 && onSalesClick ? e => { e.stopPropagation(); onSalesClick(s.seller_alias); } : undefined}>
          <span className="text-[#999]">매출 </span>
          <span className={s.sales > 0 ? 'text-[#333] font-semibold' : 'text-[#ccc]'}>{formatKRW(s.sales)}</span>
        </span>
        <span>
          <span className="text-[#999]">이익 </span>
          <span className={s.profit > 0 ? 'text-[#00a651] font-semibold' : 'text-[#ccc]'}>{formatKRW(s.profit)}</span>
        </span>
        <span className="ml-auto">
          <span className="text-[#999]">총수익 </span>
          <span className={`font-bold ${netProfit < 0 ? 'text-[#e04040]' : netProfit > 0 ? 'text-[#00a651]' : 'text-[#ccc]'}`}>{formatKRW(netProfit)}</span>
        </span>
      </div>
    </div>
  );
}
