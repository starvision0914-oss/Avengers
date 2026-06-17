import { useEffect, useState, useCallback } from 'react';
import api from '../../api/client';

const fmt = (n: number) => (n || 0).toLocaleString();
const won = (n: number) => `${fmt(n)}원`;

type Plat = {
  platform: string; label: string; revenue: number; profit: number; orders: number;
  ad_cost: number; net_after_ad: number; margin: number; real_margin: number;
};
type Shop = { shop_id: string; platform: string; label: string; revenue: number; profit: number; orders: number; margin: number };
type Summary = {
  total_revenue: number; total_profit: number; total_orders: number;
  total_ad_cost: number; total_net_after_ad: number;
  by_platform: Plat[]; by_shop: Shop[];
};

const today = () => new Date().toISOString().slice(0, 10);
const ymd = (y: number, m: number, d: number) => `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

export default function SalesDashboardPage() {
  const [from, setFrom] = useState(ymd(new Date().getFullYear(), 1, 1));
  const [to, setTo] = useState(today());
  const [data, setData] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    api.get<Summary>('/sales/summary/', { params: { from, to } })
      .then(r => setData(r.data)).finally(() => setLoading(false));
  }, [from, to]);
  useEffect(() => { load(); }, [load]);

  const setMonth = (m: number) => {
    const y = new Date().getFullYear();
    setFrom(ymd(y, m, 1)); setTo(ymd(y, m, new Date(y, m, 0).getDate()));
  };
  const setYear = () => { setFrom(ymd(new Date().getFullYear(), 1, 1)); setTo(today()); };

  const cards = data ? [
    { label: '총매출', value: data.total_revenue, color: '#1e6fd9' },
    { label: '순수익 (매출−원가)', value: data.total_profit, color: '#16a34a' },
    { label: '광고비', value: data.total_ad_cost, color: '#e67700' },
    { label: '실질순이익 (−광고비)', value: data.total_net_after_ad, color: '#7c3aed' },
  ] : [];
  const realRate = data && data.total_revenue ? (data.total_net_after_ad * 100 / data.total_revenue) : 0;

  return (
    <div className="min-h-screen bg-[#f5f5f5] p-5">
      <div className="flex items-center gap-3 flex-wrap mb-4">
        <h1 className="text-2xl font-bold">🛒 쇼핑몰 매출 대시보드</h1>
        <div className="flex items-center gap-1 ml-auto text-[12px]">
          <button onClick={setYear} className="px-2.5 py-1 bg-white border rounded hover:bg-gray-50">올해</button>
          {[6, 5, 4, 3].map(m => (
            <button key={m} onClick={() => setMonth(m)} className="px-2.5 py-1 bg-white border rounded hover:bg-gray-50">{m}월</button>
          ))}
          <input type="date" value={from} onChange={e => setFrom(e.target.value)} className="px-2 py-1 border rounded" />
          <span>~</span>
          <input type="date" value={to} onChange={e => setTo(e.target.value)} className="px-2 py-1 border rounded" />
        </div>
      </div>

      {loading && <div className="text-gray-400 py-10 text-center">불러오는 중…</div>}
      {!loading && data && (
        <>
          {/* 총괄 카드 */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
            {cards.map(c => (
              <div key={c.label} className="bg-white rounded-xl p-4 shadow-sm border-l-4" style={{ borderColor: c.color }}>
                <div className="text-[12px] text-gray-500">{c.label}</div>
                <div className="text-[22px] font-bold" style={{ color: c.color }}>{won(c.value)}</div>
              </div>
            ))}
          </div>
          <div className="text-[12px] text-gray-600 mb-4">
            실질 순이익률 <b className="text-[#7c3aed]">{realRate.toFixed(1)}%</b> · 주문 {fmt(data.total_orders)}건 · 기간 {from} ~ {to}
          </div>

          {/* 플랫폼별 */}
          <div className="bg-white rounded-xl shadow-sm mb-4 overflow-x-auto">
            <div className="px-4 py-3 font-bold border-b">쇼핑몰별 매출·순이익</div>
            <table className="w-full text-[12px]">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  <th className="px-3 py-2 text-left">쇼핑몰</th>
                  <th className="px-3 py-2 text-right">주문</th>
                  <th className="px-3 py-2 text-right">매출</th>
                  <th className="px-3 py-2 text-right">순수익(−원가)</th>
                  <th className="px-3 py-2 text-right">광고비</th>
                  <th className="px-3 py-2 text-right">실질순이익</th>
                  <th className="px-3 py-2 text-right">실질마진</th>
                </tr>
              </thead>
              <tbody>
                {data.by_platform.map(p => (
                  <tr key={p.platform} className="border-t hover:bg-gray-50">
                    <td className="px-3 py-2 font-semibold">{p.label}</td>
                    <td className="px-3 py-2 text-right">{fmt(p.orders)}</td>
                    <td className="px-3 py-2 text-right">{fmt(p.revenue)}</td>
                    <td className="px-3 py-2 text-right text-green-700">{fmt(p.profit)}</td>
                    <td className="px-3 py-2 text-right text-orange-600">{fmt(p.ad_cost)}</td>
                    <td className="px-3 py-2 text-right font-bold text-purple-700">{fmt(p.net_after_ad)}</td>
                    <td className={`px-3 py-2 text-right font-semibold ${p.real_margin < 20 ? 'text-red-500' : 'text-gray-700'}`}>{p.real_margin}%</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-gray-50 font-bold border-t-2">
                <tr>
                  <td className="px-3 py-2">합계</td>
                  <td className="px-3 py-2 text-right">{fmt(data.total_orders)}</td>
                  <td className="px-3 py-2 text-right">{fmt(data.total_revenue)}</td>
                  <td className="px-3 py-2 text-right text-green-700">{fmt(data.total_profit)}</td>
                  <td className="px-3 py-2 text-right text-orange-600">{fmt(data.total_ad_cost)}</td>
                  <td className="px-3 py-2 text-right text-purple-700">{fmt(data.total_net_after_ad)}</td>
                  <td className="px-3 py-2 text-right">{realRate.toFixed(1)}%</td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* 셀러(쇼핑몰id)별 상위 */}
          <div className="bg-white rounded-xl shadow-sm overflow-x-auto">
            <div className="px-4 py-3 font-bold border-b">쇼핑몰id별 매출 (상위 {data.by_shop.length})</div>
            <table className="w-full text-[12px]">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  <th className="px-3 py-2 text-left">쇼핑몰id</th>
                  <th className="px-3 py-2 text-left">마켓</th>
                  <th className="px-3 py-2 text-right">주문</th>
                  <th className="px-3 py-2 text-right">매출</th>
                  <th className="px-3 py-2 text-right">순수익</th>
                  <th className="px-3 py-2 text-right">마진</th>
                </tr>
              </thead>
              <tbody>
                {data.by_shop.map((s, i) => (
                  <tr key={i} className="border-t hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium">{s.shop_id}</td>
                    <td className="px-3 py-2 text-gray-500">{s.label}</td>
                    <td className="px-3 py-2 text-right">{fmt(s.orders)}</td>
                    <td className="px-3 py-2 text-right">{fmt(s.revenue)}</td>
                    <td className="px-3 py-2 text-right text-green-700">{fmt(s.profit)}</td>
                    <td className={`px-3 py-2 text-right font-semibold ${s.margin < 20 ? 'text-red-500' : 'text-gray-700'}`}>{s.margin}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
