import { useEffect, useState } from 'react';
import { getAiHistory } from '../../api/gmarket';
import type { AiHistoryRow } from '../../types/cpc';

interface Props {
  sellerId: string;
  sellerAlias: string;
  onClose: () => void;
}

const TYPE_COLORS: Record<string, string> = {
  '광고 ON/OFF': 'bg-[#e7f5ff] text-[#228be6]',
  '노출 기간': 'bg-[#fff3e0] text-[#e08000]',
  '일 허용 예산': 'bg-[#f3e8ff] text-[#7c3aed]',
};

export default function AiHistoryModal({ sellerId, sellerAlias, onClose }: Props) {
  const [rows, setRows] = useState<AiHistoryRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getAiHistory(sellerId).then(setRows).catch(() => setRows([])).finally(() => setLoading(false));
  }, [sellerId]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-[95vw] max-w-[520px] max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#eee]">
          <h3 className="text-[12px] font-bold text-[#333]">
            {sellerAlias}
            <span className="ml-2 text-[11px] font-normal text-[#999]">AI광고 변경이력</span>
          </h3>
          <button onClick={onClose} className="text-[#999] hover:text-[#333] text-[12px] leading-none px-1">&times;</button>
        </div>
        <div className="overflow-y-auto flex-1 px-4 py-2">
          {loading && <p className="text-[12px] text-[#999] py-4 text-center">로딩중...</p>}
          {!loading && rows.length === 0 && <p className="text-[12px] text-[#999] py-4 text-center">이력이 없습니다.</p>}
          {!loading && rows.length > 0 && (
            <table className="w-full text-[12px]">
              <thead>
                <tr className="bg-[#f7f7f7]">
                  <th className="px-2 py-1.5 text-left text-[#999] font-normal">시간</th>
                  <th className="px-2 py-1.5 text-left text-[#999] font-normal">구분</th>
                  <th className="px-2 py-1.5 text-left text-[#999] font-normal">내용</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} className={i % 2 ? 'bg-[#fafafa]' : 'bg-white'}>
                    <td className="px-2 py-1.5 text-[#666] whitespace-nowrap">{r.event_time}</td>
                    <td className="px-2 py-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${TYPE_COLORS[r.history_type] || 'bg-[#f5f5f5] text-[#666]'}`}>
                        {r.history_type}
                      </span>
                    </td>
                    <td className="px-2 py-1.5 text-[#333]">{r.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
