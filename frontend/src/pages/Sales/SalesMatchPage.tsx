import { useState, useEffect, useMemo } from 'react';
import { getUnmatchedSales, matchSeller } from '../../api/sales';
import { getAccounts } from '../../api/accounts';
import type { SellerAccount } from '../../types';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

const PLATFORM_LABEL: Record<string, string> = {
  '11st': '11번가', gmarket: '지마켓', auction: '옥션', coupang: '쿠팡', smartstore: '스마트스토어', ably: '에이블리',
};
const PLATFORM_ORDER: Record<string, number> = { '11st': 1, gmarket: 2, auction: 3, coupang: 4, smartstore: 5, ably: 6 };

interface Unmatched {
  shop_name: string; platform: string; count: number; sales: number;
  suggested_seller_id: number | null; suggested_seller_name: string | null;
}

export default function SalesMatchPage() {
  const [rows, setRows] = useState<Unmatched[]>([]);
  const [accounts, setAccounts] = useState<SellerAccount[]>([]);
  const [sel, setSel] = useState<Record<string, number | ''>>({});
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const [u, a] = await Promise.all([getUnmatchedSales(), getAccounts()]);
      const list: Unmatched[] = Array.isArray(u) ? u : [];
      setRows(list);
      setAccounts(Array.isArray(a) ? a : a.results || []);
      const init: Record<string, number | ''> = {};
      list.forEach(r => { init[r.shop_name] = r.suggested_seller_id ?? ''; });
      setSel(init);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const ordered = useMemo(() =>
    [...rows].sort((a, b) =>
      (PLATFORM_ORDER[a.platform] ?? 99) - (PLATFORM_ORDER[b.platform] ?? 99) || b.count - a.count),
  [rows]);

  const apply = async (shop: string) => {
    const sid = sel[shop];
    if (!sid) { toast.error('셀러를 선택하세요'); return; }
    try {
      const res = await matchSeller(shop, Number(sid));
      toast.success(`${res.matched}건 → ${res.seller} 매칭 완료`);
      setRows(rs => rs.filter(r => r.shop_name !== shop));
    } catch { toast.error('매칭 실패'); }
  };

  const totalPending = rows.reduce((a, r) => a + r.count, 0);

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">매출 셀러 매칭 <span className="text-base text-gray-500">(대기 {totalPending}건)</span></h1>
        <div className="flex gap-3">
          <button onClick={load} className="text-sm text-blue-600 hover:underline">↻ 새로고침</button>
          <button onClick={() => navigate('/sales')} className="text-sm text-gray-600 hover:underline">매출목록</button>
        </div>
      </div>
      <p className="text-sm text-gray-500 mb-4">매칭 안 된 매출의 '쇼핑몰명'을 셀러계정에 연결합니다. 적용하면 그 상점명은 <b>다음 업로드부터 자동매칭</b>됩니다. (11번가 → 지마켓 → 나머지 순)</p>

      {loading ? <p>불러오는 중…</p> : ordered.length === 0 ? (
        <div className="p-8 text-center text-green-600 bg-green-50 rounded-lg">✅ 매칭 대기 건이 없습니다.</div>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b-2 border-gray-300 text-left">
              <th className="p-2">마켓</th><th className="p-2">쇼핑몰명</th><th className="p-2 text-right">건수</th>
              <th className="p-2 text-right">매출</th><th className="p-2">→ 셀러계정</th><th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {ordered.map(r => (
              <tr key={r.shop_name} className="border-b border-gray-100">
                <td className="p-2"><span className="px-2 py-0.5 rounded text-xs font-bold" style={{ background: '#eef', color: '#33a' }}>{PLATFORM_LABEL[r.platform] || r.platform}</span></td>
                <td className="p-2 font-medium">{r.shop_name || '(미지정)'}</td>
                <td className="p-2 text-right">{r.count.toLocaleString()}</td>
                <td className="p-2 text-right text-blue-700">{r.sales.toLocaleString()}원</td>
                <td className="p-2">
                  <select value={sel[r.shop_name] ?? ''} onChange={e => setSel(s => ({ ...s, [r.shop_name]: e.target.value ? Number(e.target.value) : '' }))}
                    className="border rounded px-2 py-1 w-44">
                    <option value="">셀러 선택…</option>
                    {accounts.map(a => <option key={a.id} value={a.id}>{a.seller_name}</option>)}
                  </select>
                  {r.suggested_seller_name && <span className="ml-1 text-xs text-orange-600">추천:{r.suggested_seller_name}</span>}
                </td>
                <td className="p-2"><button onClick={() => apply(r.shop_name)} className="bg-green-600 text-white px-3 py-1 rounded text-xs hover:bg-green-700">적용</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
