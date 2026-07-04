import { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Package, ShoppingCart, Receipt, CheckCircle2, XCircle } from 'lucide-react';
import api from '../../api/client';

interface Row {
  no: number;
  login_id: string;
  seller_name: string;
  has_api_key: boolean;
  is_rocket_growth: boolean;
  product_count: number;
  approved_count: number;
  rejected_count: number;
  order_count: number;
  order_total: number;
  vat_total: number;
  last_synced: string | null;
}
interface DashResp {
  date_from: string;
  date_to: string;
  totals: { product_count: number; order_count: number; order_total: number; vat_total: number };
  rows: Row[];
}

const fmt = (n: number) => (n || 0).toLocaleString();
const sv = (d: Date) => d.toLocaleDateString('sv');

export default function CoupangDashboard() {
  const [data, setData] = useState<DashResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [from, setFrom] = useState(sv(new Date(new Date().getFullYear(), 0, 1)));
  const [to, setTo] = useState(sv(new Date()));

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<DashResp>('/coupang/dashboard/', { params: { date_from: from, date_to: to } });
      setData(data);
    } catch {
      /* noop */
    } finally {
      setLoading(false);
    }
  }, [from, to]);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">쿠팡</h1>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          새로고침
        </button>
      </div>

      <div className="flex items-center gap-2 mb-4 text-sm">
        <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="border rounded px-2 py-1" />
        <span>~</span>
        <input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="border rounded px-2 py-1" />
        <span className="text-gray-400 ml-2">(주문/매출 조회기간)</span>
      </div>

      {data && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><Package size={16} />등록상품</div>
            <div className="text-xl font-bold">{fmt(data.totals.product_count)}개</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><ShoppingCart size={16} />주문건수</div>
            <div className="text-xl font-bold">{fmt(data.totals.order_count)}건</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><ShoppingCart size={16} />주문금액(API, 수수료전)</div>
            <div className="text-xl font-bold">{fmt(data.totals.order_total)}원</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><Receipt size={16} />부가세신고매출(연간)</div>
            <div className="text-xl font-bold">{fmt(data.totals.vat_total)}원</div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-3 py-2 text-left">#</th>
              <th className="px-3 py-2 text-left">계정</th>
              <th className="px-3 py-2 text-left">상호</th>
              <th className="px-3 py-2 text-center">오픈API</th>
              <th className="px-3 py-2 text-center">로켓그로스</th>
              <th className="px-3 py-2 text-right">상품수</th>
              <th className="px-3 py-2 text-right">승인/반려</th>
              <th className="px-3 py-2 text-right">주문건수</th>
              <th className="px-3 py-2 text-right">주문금액</th>
              <th className="px-3 py-2 text-right">부가세매출(연)</th>
              <th className="px-3 py-2 text-left">최근수집</th>
            </tr>
          </thead>
          <tbody>
            {data?.rows.map((r) => (
              <tr key={r.login_id} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2">{r.no}</td>
                <td className="px-3 py-2 font-medium">{r.login_id}</td>
                <td className="px-3 py-2">{r.seller_name}</td>
                <td className="px-3 py-2 text-center">
                  {r.has_api_key ? <CheckCircle2 size={16} className="inline text-green-600" /> : <XCircle size={16} className="inline text-gray-300" />}
                </td>
                <td className="px-3 py-2 text-center">{r.is_rocket_growth ? 'O' : '-'}</td>
                <td className="px-3 py-2 text-right">{fmt(r.product_count)}</td>
                <td className="px-3 py-2 text-right">
                  <span className="text-green-600">{fmt(r.approved_count)}</span>
                  {r.rejected_count > 0 && <span className="text-red-500"> / {fmt(r.rejected_count)}</span>}
                </td>
                <td className="px-3 py-2 text-right">{fmt(r.order_count)}</td>
                <td className="px-3 py-2 text-right">{fmt(r.order_total)}원</td>
                <td className="px-3 py-2 text-right">{fmt(r.vat_total)}원</td>
                <td className="px-3 py-2 text-gray-400 text-xs">{r.last_synced ? new Date(r.last_synced).toLocaleString('ko-KR') : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
