import { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Megaphone, TrendingUp, Eye, MousePointerClick } from 'lucide-react';
import api from '../../api/client';

interface DashRow {
  period: string;
  exec_ad_cost: number;
  conversion_amount: number;
  impressions: number;
  clicks: number;
  roas: number | null;
}
interface DashResp {
  start: string;
  end: string;
  group: 'day' | 'month';
  totals: { exec_ad_cost: number; conversion_amount: number; impressions: number; clicks: number; roas: number | null };
  rows: DashRow[];
}
interface CampaignRow {
  campaign_id: string;
  campaign_name: string;
  status: string;
  exec_ad_cost: number;
  conversion_amount: number;
  impressions: number;
  clicks: number;
  conv_qty: number;
  conv_orders: number;
  start_date: string;
  end_date: string;
  roas: number | null;
}
interface AccountRow {
  account_id: number;
  login_id: string;
  account_name: string;
  sales: number;
  settlement: number;
  orders: number;
  ad_cost: number;
  roas: number | null;
  registered_products: number | null;
  note: string;
}

const fmt = (n: number) => (n || 0).toLocaleString();
const sv = (d: Date) => d.toLocaleDateString('sv');
const TOSS_BLUE = '#0064ff';

export default function TossDashboard() {
  const [data, setData] = useState<DashResp | null>(null);
  const [campaigns, setCampaigns] = useState<CampaignRow[]>([]);
  const [accounts, setAccounts] = useState<AccountRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [group, setGroup] = useState<'day' | 'month'>('day');
  const [start, setStart] = useState(sv(new Date(new Date().getFullYear(), new Date().getMonth(), 1)));
  const [end, setEnd] = useState(sv(new Date(Date.now() - 86400000)));

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [dash, camp, accts] = await Promise.all([
        api.get<DashResp>('/toss/dashboard/', { params: { start, end, group } }),
        api.get<{ rows: CampaignRow[] }>('/toss/campaigns/', { params: { start, end } }),
        api.get<{ by_account: AccountRow[] }>('/toss/account-summary/', { params: { start, end } }),
      ]);
      setData(dash.data);
      setCampaigns(camp.data.rows);
      setAccounts(accts.data.by_account);
    } catch {
      /* noop */
    } finally {
      setLoading(false);
    }
  }, [start, end, group]);
  useEffect(() => { load(); }, [load]);

  const setPreset = (preset: 'today' | 'yesterday' | 'thisMonth') => {
    const now = new Date();
    if (preset === 'today') {
      const d = sv(now); setStart(d); setEnd(d); setGroup('day');
    } else if (preset === 'yesterday') {
      const d = sv(new Date(now.getTime() - 86400000)); setStart(d); setEnd(d); setGroup('day');
    } else {
      setStart(sv(new Date(now.getFullYear(), now.getMonth(), 1)));
      setEnd(sv(new Date(now.getTime() - 86400000)));
      setGroup('month');
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm" style={{ background: TOSS_BLUE }} />
          <h1 className="text-2xl font-bold">토스 광고비</h1>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-white rounded hover:opacity-90" style={{ background: TOSS_BLUE }}>
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          새로고침
        </button>
      </div>

      <div className="flex items-center gap-2 mb-4 text-sm flex-wrap">
        <button onClick={() => setPreset('today')} className="px-3 py-1 rounded border hover:bg-gray-50">오늘</button>
        <button onClick={() => setPreset('yesterday')} className="px-3 py-1 rounded border hover:bg-gray-50">어제</button>
        <button onClick={() => setPreset('thisMonth')} className="px-3 py-1 rounded border hover:bg-gray-50">이번달(월별)</button>
        <span className="mx-1 text-gray-300">|</span>
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="border rounded px-2 py-1" />
        <span>~</span>
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="border rounded px-2 py-1" />
        <select value={group} onChange={(e) => setGroup(e.target.value as 'day' | 'month')} className="border rounded px-2 py-1">
          <option value="day">일자별</option>
          <option value="month">월별</option>
        </select>
      </div>

      <div className="bg-white rounded-lg shadow overflow-x-auto mb-6">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-3 py-2 text-left">계정</th>
              <th className="px-3 py-2 text-right">매출</th>
              <th className="px-3 py-2 text-right">구매</th>
              <th className="px-3 py-2 text-right">광고비</th>
              <th className="px-3 py-2 text-right">ROAS</th>
              <th className="px-3 py-2 text-right">등록상품수</th>
              <th className="px-3 py-2 text-left">비고</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.account_id} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2 font-medium">{a.account_name}</td>
                <td className="px-3 py-2 text-right">{fmt(a.sales)}원</td>
                <td className="px-3 py-2 text-right">{fmt(a.orders)}건</td>
                <td className="px-3 py-2 text-right text-orange-500">{fmt(a.ad_cost)}원</td>
                <td className="px-3 py-2 text-right">{a.roas != null ? a.roas + '%' : '-'}</td>
                <td className="px-3 py-2 text-right">{a.registered_products != null ? fmt(a.registered_products) : '-'}</td>
                <td className="px-3 py-2 text-gray-500">{a.note}</td>
              </tr>
            ))}
            {accounts.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-gray-400">계정 없음</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {data && (
        <div className="grid grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><Megaphone size={16} />집행 광고비</div>
            <div className="text-xl font-bold text-orange-500">{fmt(data.totals.exec_ad_cost)}원</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><TrendingUp size={16} />광고 전환 거래액</div>
            <div className="text-xl font-bold">{fmt(data.totals.conversion_amount)}원</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><TrendingUp size={16} />ROAS</div>
            <div className="text-xl font-bold text-green-600">{data.totals.roas != null ? data.totals.roas + '%' : '-'}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><Eye size={16} />노출 수</div>
            <div className="text-xl font-bold">{fmt(data.totals.impressions)}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1"><MousePointerClick size={16} />클릭 수</div>
            <div className="text-xl font-bold">{fmt(data.totals.clicks)}</div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-x-auto mb-6">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-3 py-2 text-left">{group === 'month' ? '월' : '일자'}</th>
              <th className="px-3 py-2 text-right">집행광고비</th>
              <th className="px-3 py-2 text-right">전환거래액</th>
              <th className="px-3 py-2 text-right">ROAS</th>
              <th className="px-3 py-2 text-right">노출수</th>
              <th className="px-3 py-2 text-right">클릭수</th>
            </tr>
          </thead>
          <tbody>
            {data?.rows.map((r) => (
              <tr key={r.period} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2 font-medium">{r.period}</td>
                <td className="px-3 py-2 text-right text-orange-500">{fmt(r.exec_ad_cost)}원</td>
                <td className="px-3 py-2 text-right">{fmt(r.conversion_amount)}원</td>
                <td className="px-3 py-2 text-right">{r.roas != null ? r.roas + '%' : '-'}</td>
                <td className="px-3 py-2 text-right">{fmt(r.impressions)}</td>
                <td className="px-3 py-2 text-right">{fmt(r.clicks)}</td>
              </tr>
            ))}
            {data?.rows.length === 0 && (
              <tr><td colSpan={6} className="px-3 py-6 text-center text-gray-400">데이터 없음</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <h2 className="text-lg font-bold mb-2">전체 캠페인 내역</h2>
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-3 py-2 text-left">상태</th>
              <th className="px-3 py-2 text-left">캠페인</th>
              <th className="px-3 py-2 text-right">집행광고비</th>
              <th className="px-3 py-2 text-right">전환거래액</th>
              <th className="px-3 py-2 text-right">ROAS</th>
              <th className="px-3 py-2 text-right">노출수</th>
              <th className="px-3 py-2 text-right">클릭수</th>
              <th className="px-3 py-2 text-right">전환수량</th>
              <th className="px-3 py-2 text-right">전환주문</th>
              <th className="px-3 py-2 text-left">기간</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr key={c.campaign_id} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2">{c.status}</td>
                <td className="px-3 py-2 font-medium">{c.campaign_name}</td>
                <td className="px-3 py-2 text-right text-orange-500">{fmt(c.exec_ad_cost)}원</td>
                <td className="px-3 py-2 text-right">{fmt(c.conversion_amount)}원</td>
                <td className="px-3 py-2 text-right">{c.roas != null ? c.roas + '%' : '-'}</td>
                <td className="px-3 py-2 text-right">{fmt(c.impressions)}</td>
                <td className="px-3 py-2 text-right">{fmt(c.clicks)}</td>
                <td className="px-3 py-2 text-right">{fmt(c.conv_qty)}</td>
                <td className="px-3 py-2 text-right">{fmt(c.conv_orders)}</td>
                <td className="px-3 py-2 text-gray-400 text-xs">{c.start_date} ~ {c.end_date}</td>
              </tr>
            ))}
            {campaigns.length === 0 && (
              <tr><td colSpan={10} className="px-3 py-6 text-center text-gray-400">데이터 없음</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
