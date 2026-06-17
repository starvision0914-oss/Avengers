import { useState } from 'react';
import { formatKRW } from '../../utils/format';

export interface KwRow {
  keyword: string;
  cost: number;
  clicks: number;
  conv_amount: number;
  roas: number;
  impressions?: number;
  orders?: number;
}

interface Props {
  productNo: string;
  sellerCode?: string;
  keywords: KwRow[];
  onClose: () => void;
}

// 효율(%) = 광고수익률(roas) — 칸 절약 위해 정수 표시
function effColor(eff: number): string {
  if (!eff) return 'text-[#dc2626] font-bold';
  if (eff >= 300) return 'text-[#00a651] font-bold';
  if (eff >= 100) return 'text-[#e08000] font-semibold';
  return 'text-[#dc2626] font-semibold';
}

const COLS: { key: keyof KwRow; label: string; text?: boolean }[] = [
  { key: 'keyword', label: '키워드', text: true },
  { key: 'roas', label: '효율(%)' },
  { key: 'impressions', label: '노출' },
  { key: 'clicks', label: '클릭' },
  { key: 'cost', label: '광고비' },
  { key: 'orders', label: '구매수' },
  { key: 'conv_amount', label: '구매금액' },
];

export default function GmktKeywordDetailModal({ productNo, sellerCode, keywords, onClose }: Props) {
  const [sort, setSort] = useState<{ key: keyof KwRow; dir: 'asc' | 'desc' }>({ key: 'cost', dir: 'desc' });
  const sortClick = (k: keyof KwRow, text?: boolean) =>
    setSort(s => s.key === k ? { key: k, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key: k, dir: text ? 'asc' : 'desc' });
  const arrow = (k: keyof KwRow) => (sort.key === k ? (sort.dir === 'asc' ? ' ▲' : ' ▼') : '');
  const rows = [...keywords].sort((a, b) => {
    const va = a[sort.key], vb = b[sort.key];
    const c = (typeof va === 'string' || typeof vb === 'string')
      ? String(va || '').localeCompare(String(vb || ''))
      : (Number(va) || 0) - (Number(vb) || 0);
    return sort.dir === 'asc' ? c : -c;
  });
  const tot = rows.reduce((s, k) => ({
    cost: s.cost + (k.cost || 0), clicks: s.clicks + (k.clicks || 0),
    conv: s.conv + (k.conv_amount || 0), imp: s.imp + (k.impressions || 0), ord: s.ord + (k.orders || 0),
  }), { cost: 0, clicks: 0, conv: 0, imp: 0, ord: 0 });
  const totEff = tot.cost ? Math.round(tot.conv * 100 / tot.cost) : 0;

  return (
    <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/45 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-[720px] max-w-full max-h-[85vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-2 px-5 py-3 border-b border-[#eee]">
          <h3 className="text-[13px] font-bold text-[#333]">키워드 상세</h3>
          <span className="font-mono text-[12px] text-[#1d4ed8]">{productNo}</span>
          {sellerCode && <span className="font-mono text-[11px] text-[#888]">{sellerCode}</span>}
          <span className="text-[11px] text-[#888]">키워드 {rows.length}개</span>
          <button onClick={onClose} className="ml-auto text-[#999] hover:text-[#333] text-[18px] leading-none">&times;</button>
        </div>
        <div className="overflow-auto">
          <table className="w-full text-[12px]">
            <thead className="bg-[#f5f6f8] text-[#555] sticky top-0">
              <tr>
                {COLS.map(c => (
                  <th key={String(c.key)} onClick={() => sortClick(c.key, c.text)}
                    title={c.key === 'roas' ? '효율 = 구매금액÷광고비 (정수)' : '클릭하면 정렬'}
                    className={`px-2 py-2 cursor-pointer select-none hover:bg-[#eaeaea] ${c.text ? 'text-left px-3' : 'text-right'}`}>
                    {c.label}{arrow(c.key)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && <tr><td colSpan={7} className="text-center py-6 text-[#aaa]">수집된 키워드 없음</td></tr>}
              {rows.map((k, i) => (
                <tr key={i} className="border-t border-[#f0f0f0] hover:bg-[#fafafa]">
                  <td className="px-3 py-1.5 font-medium text-[#333]">{k.keyword}</td>
                  <td className={`px-2 py-1.5 text-right ${effColor(Math.round(k.roas || 0))}`}>{Math.round(k.roas || 0)}</td>
                  <td className="px-2 py-1.5 text-right text-[#666]">{(k.impressions || 0).toLocaleString()}</td>
                  <td className="px-2 py-1.5 text-right text-[#666]">{(k.clicks || 0).toLocaleString()}</td>
                  <td className="px-2 py-1.5 text-right">{formatKRW(k.cost || 0)}</td>
                  <td className="px-2 py-1.5 text-right text-[#666]">{(k.orders || 0).toLocaleString()}</td>
                  <td className="px-2 py-1.5 text-right text-[#1d7a46]">{formatKRW(k.conv_amount || 0)}</td>
                </tr>
              ))}
            </tbody>
            {rows.length > 0 && (
              <tfoot>
                <tr className="bg-[#f8fafc] font-bold border-t-2 border-[#e0e0e0]">
                  <td className="px-3 py-2 text-left text-[#333]">합계</td>
                  <td className={`px-2 py-2 text-right ${effColor(totEff)}`}>{totEff}</td>
                  <td className="px-2 py-2 text-right text-[#666]">{tot.imp.toLocaleString()}</td>
                  <td className="px-2 py-2 text-right text-[#666]">{tot.clicks.toLocaleString()}</td>
                  <td className="px-2 py-2 text-right">{formatKRW(tot.cost)}</td>
                  <td className="px-2 py-2 text-right text-[#666]">{tot.ord.toLocaleString()}</td>
                  <td className="px-2 py-2 text-right text-[#1d7a46]">{formatKRW(tot.conv)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
        <div className="px-5 py-2.5 border-t border-[#eee] text-right">
          <button onClick={onClose} className="px-4 py-1.5 bg-[#555] text-white rounded text-[12px] font-semibold hover:bg-[#444]">닫기</button>
        </div>
      </div>
    </div>
  );
}
