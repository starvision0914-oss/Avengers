import { useEffect, useState } from 'react';
import { getAdDetail } from '../api/crawler';
import { X } from 'lucide-react';

const CAT_COLORS: Record<string, { bg: string; text: string }> = {
  CPC: { bg: '#e7f5ff', text: '#228be6' },
  AI: { bg: '#fff3e0', text: '#e08000' },
  프라임: { bg: '#f3e5f5', text: '#7b1fa2' },
  CHARGE: { bg: '#e8f5e9', text: '#2e7d32' },
  REWARD: { bg: '#fff8e1', text: '#f57f17' },
  OTHERS: { bg: '#f5f5f5', text: '#666' },
};

interface Props {
  sellerId: string;
  sellerAlias: string;
  platform: 'gmarket' | '11st';
  date: string;
  category?: string;
  onClose: () => void;
}

export default function AdCostModal({ sellerId, sellerAlias, platform, date, category, onClose }: Props) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params: Record<string, string> = { seller_id: sellerId, platform, date };
    if (category) params.category = category;
    getAdDetail(params).then(d => { setData(d); setLoading(false); }).catch(() => setLoading(false));
  }, [sellerId, platform, date, category]);

  const rows = data?.rows || [];
  const summary = data?.summary || {};
  const fmt = (v: number) => v.toLocaleString();

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-[560px] max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        {/* 헤더 */}
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <div>
            <h2 className="text-[14px] font-bold text-[#333]">{sellerAlias} 광고비 상세</h2>
            <p className="text-[11px] text-[#999]">{date} {category ? `· ${category}` : ''} · {platform === 'gmarket' ? '지마켓' : '11번가'}</p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X size={18} className="text-[#999]" /></button>
        </div>

        {/* 요약 */}
        {Object.keys(summary).length > 0 && (
          <div className="flex items-center gap-4 px-5 py-2 border-b bg-[#fafafa] text-[12px]">
            {Object.entries(summary).map(([cat, s]: [string, any]) => {
              const color = CAT_COLORS[cat] || CAT_COLORS.OTHERS;
              return (
                <div key={cat} className="flex items-center gap-1">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold" style={{ background: color.bg, color: color.text }}>{cat}</span>
                  <span className="font-semibold">{fmt(Math.abs(s.total))}원</span>
                  <span className="text-[#aaa]">({s.count}건)</span>
                </div>
              );
            })}
            <div className="ml-auto font-bold text-[#333]">
              합계 {fmt(Math.abs(Object.values(summary).reduce((s: number, v: any) => s + v.total, 0)))}원
            </div>
          </div>
        )}

        {/* 테이블 */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-[#aaa]">로딩중...</div>
          ) : rows.length > 0 ? (
            <table className="w-full text-[12px]" style={{ fontVariantNumeric: 'tabular-nums' }}>
              <thead className="bg-[#f7f7f7] sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left text-[#999] font-normal w-20">시간</th>
                  <th className="px-3 py-2 text-left text-[#999] font-normal w-16">구분</th>
                  <th className="px-3 py-2 text-right text-[#999] font-normal w-24">금액</th>
                  <th className="px-4 py-2 text-left text-[#999] font-normal">설명</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r: any, i: number) => {
                  const color = CAT_COLORS[r.category] || CAT_COLORS.OTHERS;
                  return (
                    <tr key={i} className={`border-b border-[#f0f0f0] ${i % 2 ? 'bg-[#fafafa]' : 'bg-white'} hover:bg-[#f5f9ff]`}>
                      <td className="px-4 py-[6px] text-[#aaa]">{r.time}</td>
                      <td className="px-3 py-[6px]">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold" style={{ background: color.bg, color: color.text }}>{r.category}</span>
                      </td>
                      <td className="px-3 py-[6px] text-right font-medium">{fmt(r.amount)}원</td>
                      <td className="px-4 py-[6px] text-[#666] truncate max-w-[200px]" title={r.description}>{r.description}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="flex items-center justify-center py-12 text-[#aaa]">내역이 없습니다.</div>
          )}
        </div>
      </div>
    </div>
  );
}
