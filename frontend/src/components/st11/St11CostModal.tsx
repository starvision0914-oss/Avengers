import { useEffect, useState } from 'react';
import { getSt11CostDetail } from '../../api/eleven';
import type { St11CostRow } from '../../types/st11';

const CAT_COLORS: Record<string, { bg: string; text: string }> = {
  CPC: { bg: '#fff3e0', text: '#e67700' },
  CHARGE: { bg: '#e8f5e9', text: '#2e7d32' },
};

interface Props {
  sellerId: string;
  sellerAlias: string;
  date: string;
  range?: { start_date: string; end_date: string };
  kind?: string;
  onClose: () => void;
}

const KIND_LABEL: Record<string, string> = {
  cpc: '광고비', settle: '충전/정산', server_fee: '서버이용료',
};

export default function St11CostModal({ sellerId, sellerAlias, date, range, kind, onClose }: Props) {
  const [rows, setRows] = useState<St11CostRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getSt11CostDetail(sellerId, date, range, kind)
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [sellerId, date, range, kind]);

  const summary: Record<string, { count: number; total: number }> = {};
  for (const r of rows) {
    if (!summary[r.category]) summary[r.category] = { count: 0, total: 0 };
    summary[r.category].count++;
    summary[r.category].total += r.amount;
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-[100]" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-[560px] max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <div>
            <h2 className="text-[12px] font-bold text-[#333]">{sellerAlias} {KIND_LABEL[kind || 'cpc'] || '거래'} 상세</h2>
            <p className="text-[11px] text-[#999]">
              {range ? `${range.start_date} ~ ${range.end_date}` : date}
              <span className="ml-2 text-[#e67700] font-medium">11번가</span>
            </p>
          </div>
          <button onClick={onClose} className="text-[#999] hover:text-[#333] text-[12px]">&times;</button>
        </div>
        {Object.keys(summary).length > 0 && (
          <div className="flex items-center gap-4 px-5 py-2 border-b bg-[#fafafa] text-[12px]">
            {Object.entries(summary).map(([cat, s]) => {
              const color = CAT_COLORS[cat] || { bg: '#f5f5f5', text: '#666' };
              return (
                <div key={cat} className="flex items-center gap-1">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold" style={{ background: color.bg, color: color.text }}>{cat}</span>
                  <span className="font-semibold">{Math.abs(s.total).toLocaleString()}원</span>
                  <span className="text-[#aaa]">({s.count}건)</span>
                </div>
              );
            })}
          </div>
        )}
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
                {rows.map((r, i) => {
                  const color = CAT_COLORS[r.category] || { bg: '#f5f5f5', text: '#666' };
                  return (
                    <tr key={i} className={`border-b border-[#f0f0f0] ${i % 2 ? 'bg-[#fafafa]' : 'bg-white'} hover:bg-[#fff8f0]`}>
                      <td className="px-4 py-[6px] text-[#aaa]">{r.time}</td>
                      <td className="px-3 py-[6px]">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold" style={{ background: color.bg, color: color.text }}>{r.category}</span>
                      </td>
                      <td className="px-3 py-[6px] text-right font-medium">{r.amount.toLocaleString()}원</td>
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
