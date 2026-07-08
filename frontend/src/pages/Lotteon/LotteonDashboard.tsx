import { useEffect, useState, useCallback } from 'react';
import { RefreshCw, ShoppingCart, Wallet, TrendingUp, Megaphone, CheckCircle2, XCircle } from 'lucide-react';
import api from '../../api/client';

interface Row {
  no: number;
  account_id: number;
  login_id: string;
  store_name: string;
  seller_no: string;
  has_api_key: boolean;
  sales: number;
  cogs: number;
  ad_cost: number;
  orders: number;
  net: number;
  roas: number | null;
  last_synced: string | null;
}
interface DashResp {
  start: string;
  end: string;
  totals: { sales: number; cogs: number; ad_cost: number; orders: number; net: number };
  rows: Row[];
}

const fmt = (n: number) => (n || 0).toLocaleString();
const sv = (d: Date) => d.toLocaleDateString('sv');
const LOTTE_RED = '#ec1d25';

export default function LotteonDashboard() {
  const [data, setData] = useState<DashResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [start, setStart] = useState(sv(new Date(new Date().getFullYear(), new Date().getMonth(), 1)));
  const [end, setEnd] = useState(sv(new Date()));

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<DashResp>('/lotteon/dashboard/', { params: { start, end } });
      setData(data);
    } catch {
      /* noop */
    } finally {
      setLoading(false);
    }
  }, [start, end]);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm" style={{ background: LOTTE_RED }} />
          <h1 className="text-2xl font-bold">롯데ON</h1>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-white rounded hover:opacity-90" style={{ background: LOTTE_RED }}>
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          새로고침
        </button>
      </div>

      <div className="flex items-center gap-2 mb-4 text-sm">
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="border rounded px-2 py-1" />
        <span>~</span>
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="border rounded px-2 py-1" />
        <span className="text-gray-400 ml-2">매출/구매가는 엑셀 업로드(판매관리 &gt; 엑셀업로드)로 반영됩니다</span>
      </div>

      {data && (
        <div className="grid grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><Wallet size={16} />매출</div>
            <div className="text-xl font-bold">{fmt(data.totals.sales)}원</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><ShoppingCart size={16} />구매가(원가)</div>
            <div className="text-xl font-bold text-sky-600">{fmt(data.totals.cogs)}원</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><Megaphone size={16} />광고비</div>
            <div className="text-xl font-bold text-orange-500">{fmt(data.totals.ad_cost)}원</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><TrendingUp size={16} />순수익</div>
            <div className={`text-xl font-bold ${data.totals.net >= 0 ? 'text-green-600' : 'text-red-600'}`}>{fmt(data.totals.net)}원</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><ShoppingCart size={16} />주문건수</div>
            <div className="text-xl font-bold">{fmt(data.totals.orders)}건</div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-3 py-2 text-left">#</th>
              <th className="px-3 py-2 text-left">계정</th>
              <th className="px-3 py-2 text-left">스토어명</th>
              <th className="px-3 py-2 text-left">셀러ID</th>
              <th className="px-3 py-2 text-center">오픈API</th>
              <th className="px-3 py-2 text-right">매출</th>
              <th className="px-3 py-2 text-right">구매가</th>
              <th className="px-3 py-2 text-right">광고비</th>
              <th className="px-3 py-2 text-right">순수익</th>
              <th className="px-3 py-2 text-right">ROAS</th>
              <th className="px-3 py-2 text-right">주문건수</th>
              <th className="px-3 py-2 text-left">최근수집</th>
            </tr>
          </thead>
          <tbody>
            {data?.rows.map((r) => (
              <tr key={r.login_id} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2">{r.no}</td>
                <td className="px-3 py-2 font-medium">{r.login_id}</td>
                <td className="px-3 py-2">{r.store_name}</td>
                <td className="px-3 py-2 text-gray-500">{r.seller_no || '-'}</td>
                <td className="px-3 py-2 text-center">
                  {r.has_api_key ? <CheckCircle2 size={16} className="inline text-green-600" /> : <XCircle size={16} className="inline text-gray-300" />}
                </td>
                <td className="px-3 py-2 text-right">{fmt(r.sales)}원</td>
                <td className="px-3 py-2 text-right text-sky-600">{fmt(r.cogs)}원</td>
                <td className="px-3 py-2 text-right text-orange-500">{fmt(r.ad_cost)}원</td>
                <td className={`px-3 py-2 text-right font-semibold ${r.net >= 0 ? 'text-green-600' : 'text-red-600'}`}>{fmt(r.net)}원</td>
                <td className="px-3 py-2 text-right">{r.roas != null ? r.roas + '%' : '-'}</td>
                <td className="px-3 py-2 text-right">{fmt(r.orders)}</td>
                <td className="px-3 py-2 text-gray-400 text-xs">{r.last_synced ? new Date(r.last_synced).toLocaleString('ko-KR') : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
