import { useEffect, useState, useCallback } from 'react';
import { getTaxVatSummary, type TaxVatSummary } from '../../api/tax';
import { formatKRW } from '../../utils/format';

const MONTHS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];

export default function TaxVatPage() {
  const [year, setYear] = useState(2026);
  const [data, setData] = useState<TaxVatSummary | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await getTaxVatSummary(year)); } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [year]);

  // 30초마다 자동 새로고침 (수집 진행 중 모니터링)
  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load]);

  const months = data ? MONTHS.filter(m => data.monthly_totals[m] !== undefined) : [];
  const pct = data && data.progress.target ? Math.round(data.progress.collected / data.progress.target * 100) : 0;

  return (
    <div className="min-h-screen bg-[#f5f5f5] p-5">
      <div className="max-w-[1500px] mx-auto">
        <div className="flex items-center gap-3 mb-4">
          <h1 className="text-[20px] font-bold text-[#222]">11번가 부가세(VAT) 현황</h1>
          <select value={year} onChange={e => setYear(Number(e.target.value))}
            className="border border-[#ccc] rounded px-2 py-1 text-[12px]">
            {[2026, 2025, 2024].map(y => <option key={y} value={y}>{y}년</option>)}
          </select>
          <button onClick={load} className="px-3 py-1 text-[12px] font-semibold bg-[#e67700] text-white rounded">새로고침</button>
          {loading && <span className="text-[12px] text-[#999] animate-pulse">불러오는 중…</span>}
        </div>

        {/* 수집 진행률 */}
        {data && (
          <div className="bg-white border border-[#e0e0e0] rounded p-4 mb-4">
            <div className="flex items-center justify-between mb-2 text-[12px]">
              <span className="font-bold text-[#333]">수집 진행률</span>
              <span className="text-[#666]">
                {data.progress.collected} / {data.progress.target} 계정 ({pct}%)
                {data.progress.last_collected_at && (
                  <span className="ml-3 text-[12px] text-[#999]">
                    최근 수집 {new Date(data.progress.last_collected_at).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                  </span>
                )}
              </span>
            </div>
            <div className="w-full h-3 bg-[#eee] rounded overflow-hidden">
              <div className="h-full bg-[#00a651]" style={{ width: `${pct}%` }} />
            </div>
            <div className="flex gap-6 mt-3 text-[12px]">
              <span>총 과세매출 <b className="text-[#0369a1]">{formatKRW(data.grand_total)}</b></span>
              <span>매출세액(과세÷11) <b className="text-[#dc2626]">{formatKRW(data.vat_payable)}</b></span>
              <span>수집 계정 <b>{data.accounts.length}</b></span>
            </div>
          </div>
        )}

        {/* 계정별 월별 과세매출 */}
        <div className="bg-white border border-[#e0e0e0] rounded overflow-x-auto">
          <table className="w-full text-[12px]" style={{ borderCollapse: 'collapse', fontVariantNumeric: 'tabular-nums' }}>
            <thead>
              <tr style={{ background: '#fffbf0', borderBottom: '2px solid #ddd' }}>
                <th className="px-3 py-2 text-center" style={{ width: 44 }}>No</th>
                <th className="px-3 py-2 text-left">셀러</th>
                {months.map(m => <th key={m} className="px-3 py-2 text-right">{m}월</th>)}
                <th className="px-3 py-2 text-right font-bold">합계(과세)</th>
              </tr>
            </thead>
            <tbody>
              {data?.accounts.map((a, i) => (
                <tr key={a.group} style={{ background: i % 2 ? '#fafafa' : '#fff', borderBottom: '1px solid #eee' }}>
                  <td className="px-3 py-1.5 text-center text-[#888]">{i + 1}</td>
                  <td className="px-3 py-1.5"><b>{a.group}</b><span className="text-[12px] text-[#666]">({a.rep_login_id})</span>{a.member_count > 1 && <span className="text-[12px] text-[#888] ml-1">외 {a.member_count - 1}개</span>}</td>
                  {months.map(m => {
                    const v = a.months[m] ?? 0;
                    return <td key={m} className="px-3 py-1.5 text-right" style={{ color: v < 0 ? '#dc2626' : v > 0 ? '#333' : '#bbb' }}>{v ? formatKRW(v) : '-'}</td>;
                  })}
                  <td className="px-3 py-1.5 text-right font-bold text-[#0369a1]">{formatKRW(a.total)}</td>
                </tr>
              ))}
              {(!data || data.accounts.length === 0) && (
                <tr><td colSpan={months.length + 3} className="px-3 py-6 text-center text-[#999]">수집된 데이터가 없습니다 (크롤 진행 중일 수 있습니다)</td></tr>
              )}
            </tbody>
            {data && data.accounts.length > 0 && (
              <tfoot>
                <tr style={{ background: '#eef3ff', fontWeight: 700, borderTop: '2px solid #ccd' }}>
                  <td className="px-3 py-2 text-center" colSpan={2}>합계 ({data.accounts.length}그룹)</td>
                  {months.map(m => <td key={m} className="px-3 py-2 text-right">{formatKRW(data.monthly_totals[m] || 0)}</td>)}
                  <td className="px-3 py-2 text-right text-[#0369a1]">{formatKRW(data.grand_total)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
        <p className="text-[12px] text-[#999] mt-2">※ 11번가 셀러오피스 부가세신고내역(공식 과세매출) 기준. 30초마다 자동 갱신.</p>
      </div>
    </div>
  );
}
