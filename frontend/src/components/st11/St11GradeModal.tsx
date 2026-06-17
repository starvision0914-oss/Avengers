import { useEffect, useState } from 'react';
import api from '../../api/client';

interface GradeItem {
  eleven_id: string;
  seller_name: string;
  grade: number | null;
  grade_message: string;
  required_sales: number | null;
  collected_at: string;
}

interface Props {
  onClose: () => void;
}

const GRADE_STYLE: Record<number, { bg: string; text: string }> = {
  1: { bg: '#fef2f2', text: '#dc2626' },
  2: { bg: '#fff3e0', text: '#e67700' },
  3: { bg: '#e7f5ff', text: '#1a73e8' },
  4: { bg: '#f0fdf4', text: '#16a34a' },
  5: { bg: '#f0fdf4', text: '#00a651' },
};

export default function St11GradeModal({ onClose }: Props) {
  const [grades, setGrades] = useState<GradeItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get('/cpc/eleven-grades-latest/').then(r => {
      const data = r.data.results || r.data;
      const items = Array.isArray(data) ? data : [];
      const unique = new Map<string, GradeItem>();
      for (const g of items) {
        if (!unique.has(g.eleven_id)) {
          unique.set(g.eleven_id, {
            eleven_id: g.eleven_id,
            seller_name: g.seller_name || g.eleven_id,
            grade: g.grade,
            grade_message: g.grade_message || '',
            required_sales: g.required_sales || null,
            collected_at: g.collected_at || '',
          });
        }
      }
      setGrades(Array.from(unique.values()).sort((a, b) => (b.grade || 0) - (a.grade || 0)));
    }).catch(() => setGrades([])).finally(() => setLoading(false));
  }, []);

  const [sortKey, setSortKey] = useState<string>('grade');
  const [sortAsc, setSortAsc] = useState(false);
  const handleSort = (k: string) => {
    if (sortKey === k) setSortAsc(!sortAsc);
    else { setSortKey(k); setSortAsc(k === 'seller_name' || k === 'eleven_id'); }
  };
  const arrow = (k: string) => (sortKey === k ? (sortAsc ? ' ▲' : ' ▼') : '');
  const sorted = [...grades].sort((a, b) => {
    let va: any = (a as any)[sortKey], vb: any = (b as any)[sortKey];
    if (sortKey === 'grade' || sortKey === 'required_sales') {
      va = va ?? -1; vb = vb ?? -1; return sortAsc ? va - vb : vb - va;
    }
    va = (va || '').toString(); vb = (vb || '').toString();
    return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
  });

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-[95vw] max-w-[650px] max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#eee]">
          <h3 className="text-[12px] font-bold text-[#333]">
            11번가 셀러 등급 현황
            <span className="ml-2 text-[11px] font-normal text-[#999]">{grades.length}개</span>
          </h3>
          <button onClick={onClose} className="text-[#999] hover:text-[#333] text-[12px] leading-none px-1">&times;</button>
        </div>
        {/* 등급별 개수 */}
        {!loading && grades.length > 0 && (
          <div className="flex items-center gap-3 px-4 py-2.5 border-b border-[#eee] bg-[#fffbf0]">
            {[1, 2, 3, 4, 5].map(g => {
              const cnt = grades.filter(r => r.grade === g).length;
              if (cnt === 0) return null;
              const c = GRADE_STYLE[g] || { bg: '#f5f5f5', text: '#999' };
              return (
                <span key={g} className="flex items-center gap-1 text-[12px]">
                  <span className="px-2 py-0.5 rounded font-bold" style={{ background: c.bg, color: c.text }}>{g}등급</span>
                  <b className="text-[#333]">{cnt}개</b>
                </span>
              );
            })}
            <span className="ml-auto text-[12px] text-[#999]">총 {grades.length}개</span>
          </div>
        )}

        <div className="overflow-y-auto flex-1">
          {loading ? (
            <p className="text-[12px] text-[#999] py-8 text-center">로딩중...</p>
          ) : grades.length === 0 ? (
            <p className="text-[12px] text-[#999] py-8 text-center">등급 데이터가 없습니다.</p>
          ) : (
            <table className="w-full text-[12px]">
              <thead className="bg-[#f7f7f7] sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-center text-[#999] font-normal w-8">#</th>
                  <th className="px-3 py-2 text-left text-[#555] font-semibold cursor-pointer select-none hover:text-[#111]" onClick={() => handleSort('eleven_id')}>셀러 ID{arrow('eleven_id')}</th>
                  <th className="px-3 py-2 text-left text-[#555] font-semibold cursor-pointer select-none hover:text-[#111]" onClick={() => handleSort('seller_name')}>셀러명{arrow('seller_name')}</th>
                  <th className="px-3 py-2 text-center text-[#555] font-semibold cursor-pointer select-none hover:text-[#111]" colSpan={2} onClick={() => handleSort('grade')}>등급{arrow('grade')}</th>
                  <th className="px-3 py-2 text-right text-[#555] font-semibold cursor-pointer select-none hover:text-[#111]" onClick={() => handleSort('required_sales')}>필요매출{arrow('required_sales')}</th>
                  <th className="px-3 py-2 text-left text-[#999] font-normal cursor-pointer select-none hover:text-[#111]" onClick={() => handleSort('collected_at')}>수집{arrow('collected_at')}</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((g, i) => (
                  <tr key={g.eleven_id} className={`border-b border-[#eee] ${i % 2 ? 'bg-[#fafafa]' : ''}`}>
                    <td className="px-3 py-2 text-center text-[#999]">{i + 1}</td>
                    <td className="px-3 py-2 text-[#666]">{g.eleven_id}</td>
                    <td className="px-3 py-2 font-semibold text-[#222]">{g.seller_name}</td>
                    <td className="px-3 py-2 text-center" colSpan={2}>
                      {g.grade != null ? (() => {
                        const c = GRADE_STYLE[g.grade] || { bg: '#f5f5f5', text: '#999' };
                        return <span className="px-3 py-1 rounded text-[12px] font-bold" style={{ background: c.bg, color: c.text }}>{g.grade}등급</span>;
                      })() : <span className="text-[#ccc]">-</span>}
                    </td>
                    <td className="px-3 py-2 text-right text-[#666]">
                      {g.required_sales ? `${g.required_sales.toLocaleString()}원` : '-'}
                    </td>
                    <td className="px-3 py-2 text-[10px] text-[#aaa]">
                      {g.collected_at ? new Date(g.collected_at).toLocaleDateString('ko-KR') : '-'}
                    </td>
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
