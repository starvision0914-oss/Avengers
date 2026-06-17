import { useEffect, useState } from 'react';
import { fetchSellerGrades } from '../../api/gmarket';
import type { SellerGradeItem } from '../../types/cpc';

interface Props {
  onClose: () => void;
}

export default function SellerGradeModal({ onClose }: Props) {
  const [grades, setGrades] = useState<SellerGradeItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchSellerGrades().then(setGrades).catch(() => setGrades([])).finally(() => setLoading(false));
  }, []);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-[95vw] max-w-[600px] max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#eee]">
          <h3 className="text-[12px] font-bold text-[#333]">셀러 등급 현황</h3>
          <button onClick={onClose} className="text-[#999] hover:text-[#333] text-[12px] leading-none px-1">&times;</button>
        </div>
        <div className="overflow-y-auto flex-1">
          {loading ? (
            <p className="text-[12px] text-[#999] py-8 text-center">로딩중...</p>
          ) : grades.length === 0 ? (
            <p className="text-[12px] text-[#999] py-8 text-center">등급 데이터가 없습니다.</p>
          ) : (
            <table className="w-full text-[12px]">
              <thead className="bg-[#f7f7f7] sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left text-[#555] font-semibold">셀러</th>
                  <th className="px-3 py-2 text-left text-[#555] font-semibold">등급</th>
                  <th className="px-3 py-2 text-right text-[#555] font-semibold">최대수량</th>
                  <th className="px-3 py-2 text-center text-[#555] font-semibold">승인</th>
                  <th className="px-3 py-2 text-left text-[#555] font-semibold">연락처인증</th>
                  <th className="px-3 py-2 text-left text-[#999] font-normal">수집</th>
                </tr>
              </thead>
              <tbody>
                {grades.map((g, i) => (
                  <tr key={g.gmarket_id} className={`border-b border-[#eee] ${i % 2 ? 'bg-[#fafafa]' : ''}`}>
                    <td className="px-3 py-2 font-semibold text-[#222]">{g.seller_id || g.gmarket_id}</td>
                    <td className={`px-3 py-2 font-semibold ${g.seller_grade === '파워이딜러' ? 'text-[#e04040]' : 'text-[#333]'}`}>{g.seller_grade}</td>
                    <td className={`px-3 py-2 text-right ${g.max_item_count >= 10000 ? 'text-[#e04040] font-bold' : 'text-[#333]'}`}>
                      {g.max_item_count?.toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${g.approval_status === '승인' ? 'bg-[#e8f5e9] text-[#00a651]' : 'bg-[#ffeef0] text-[#e04040]'}`}>
                        {g.approval_status}
                      </span>
                    </td>
                    <td className={`px-3 py-2 ${g.contact_expiry ? 'text-[#e08000]' : 'text-[#ccc]'}`}>{g.contact_expiry || '-'}</td>
                    <td className="px-3 py-2 text-[10px] text-[#aaa]">{g.collected_at}</td>
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
