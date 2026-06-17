import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, Megaphone, MousePointerClick, Eye } from 'lucide-react';
import api from '../../api/client';

interface Row {
  gmarket_id: string; ad_type: string; ad_group_name: string; status: string;
  ad_on: number; ad_off: number; impressions: number; clicks: number; ctr: number;
  avg_click_cost: number; total_cost: number; product_count: string; daily_budget: string;
}
interface Resp {
  date: string | null;
  totals: { groups: number; impressions: number; clicks: number; cost: number };
  rows: Row[]; accounts: string[];
}
const fmt = (n: number) => (n || 0).toLocaleString();

export default function GmarketAdGroupPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(true);
  const [account, setAccount] = useState('');
  const [adType, setAdType] = useState('');
  const [onlySpent, setOnlySpent] = useState(true);
  const [sortKey, setSortKey] = useState<string>('total_cost');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (account) params.account = account;
      if (adType) params.ad_type = adType;
      if (onlySpent) params.min_cost = '1';
      const { data } = await api.get<Resp>('/cpc/gmarket/adgroup/', { params });
      setData(data);
    } catch { /* noop */ } finally { setLoading(false); }
  }, [account, adType, onlySpent]);
  useEffect(() => { load(); }, [load]);

  const acc = (r: Row, k: string): number | string =>
    k === 'ad_group_name' || k === 'gmarket_id' || k === 'product_count' ? (r as any)[k] || '' : Number((r as any)[k] || 0);
  const rows = [...(data?.rows || [])].sort((a, b) => {
    const va = acc(a, sortKey), vb = acc(b, sortKey);
    const c = typeof va === 'string' ? String(va).localeCompare(String(vb)) : Number(va) - Number(vb);
    return sortDir === 'asc' ? c : -c;
  });
  const sortBy = (k: string) => {
    if (sortKey === k) setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(k); setSortDir('desc'); }
  };
  const t = data?.totals;
  const cell = 'px-3 py-1.5';
  const arrow = (k: string) => (sortKey === k ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '');
  const Th = ({ k, label, left }: { k: string; label: string; left?: boolean }) => (
    <th className={`${cell} ${left ? 'text-left' : 'text-right'} cursor-pointer select-none hover:bg-[#eee]`} onClick={() => sortBy(k)}>{label}{arrow(k)}</th>
  );
  const Card = ({ icon, label, value, color }: any) => (
    <div className="bg-white border border-[#e0e0e0] rounded-lg px-4 py-3 flex items-center gap-3">
      <div className="p-2 rounded-lg" style={{ background: color + '1a', color }}>{icon}</div>
      <div><div className="text-[11px] text-[#888]">{label}</div><div className="text-[12px] font-bold text-[#333]">{value}</div></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#f5f6f8]">
      <div className="bg-white border-b border-[#e0e0e0] px-6 py-2 flex flex-wrap items-center gap-2">
        <div className="w-3 h-3 rounded-sm" style={{ background: '#00a651' }} />
        <h1 className="text-[12px] font-bold text-[#333]">지마켓 광고그룹별 성과</h1>
        {loading && <span className="text-[11px] text-[#999] animate-pulse">로딩중...</span>}
        <div className="ml-auto flex flex-wrap items-center gap-1.5 text-[12px]">
          <button onClick={load} className="inline-flex items-center gap-1 px-2.5 py-1 bg-[#00a651] text-white rounded font-semibold"><RefreshCw size={13} /> 새로고침</button>
          <select value={account} onChange={e => setAccount(e.target.value)} className="border rounded px-2 py-1">
            <option value="">전체 계정</option>
            {(data?.accounts || []).map(a => <option key={a} value={a}>{a}</option>)}
          </select>
          <select value={adType} onChange={e => setAdType(e.target.value)} className="border rounded px-2 py-1">
            <option value="">전체 광고</option><option value="normal">일반광고</option><option value="smart">간편광고</option>
          </select>
          <label className="inline-flex items-center gap-1"><input type="checkbox" checked={onlySpent} onChange={e => setOnlySpent(e.target.checked)} />광고비&gt;0만</label>
          <button onClick={() => navigate('/gmarket')} className="px-2.5 py-1 bg-[#1e6fd9] text-white rounded font-semibold">대시보드</button>
        </div>
      </div>

      <div className="max-w-[1600px] mx-auto px-6 py-3 space-y-3">
        <div className="text-[12px] text-[#888]">기준일: <b className="text-[#333]">{data?.date || '-'}</b></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Card icon={<Megaphone size={18} />} color="#e67700" label="광고비 합계" value={`${fmt(t?.cost || 0)}원`} />
          <Card icon={<Eye size={18} />} color="#1e6fd9" label="노출 합계" value={fmt(t?.impressions || 0)} />
          <Card icon={<MousePointerClick size={18} />} color="#9333ea" label="클릭 합계" value={fmt(t?.clicks || 0)} />
          <Card icon={<Megaphone size={18} />} color="#00a651" label="광고그룹 수" value={`${fmt(t?.groups || 0)}개`} />
        </div>

        <div className="bg-white border border-[#e0e0e0] rounded-lg overflow-auto">
          <table className="w-full text-[12px]">
            <thead className="bg-[#f7f7f7] text-[#666]">
              <tr>
                <Th k="gmarket_id" label="계정" left />
                <Th k="ad_type" label="유형" left />
                <Th k="ad_group_name" label="광고그룹(상품)" left />
                <Th k="impressions" label="노출" />
                <Th k="clicks" label="클릭" />
                <Th k="ctr" label="클릭율%" />
                <Th k="avg_click_cost" label="평균클릭비" />
                <Th k="total_cost" label="광고비" />
                <Th k="product_count" label="상품" left />
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f0f0]">
              {rows.length === 0 ? (
                <tr><td colSpan={9} className="px-3 py-8 text-center text-[#aaa]">데이터 없음 (크롤 후 표시)</td></tr>
              ) : rows.map((r, i) => (
                <tr key={i} className="hover:bg-[#fafafa]">
                  <td className={`${cell} font-mono`}>{r.gmarket_id}</td>
                  <td className={cell}>{r.ad_type === 'smart' ? '간편' : '일반'}</td>
                  <td className={`${cell} text-[#333]`}>{r.ad_group_name}</td>
                  <td className={`${cell} text-right`}>{fmt(r.impressions)}</td>
                  <td className={`${cell} text-right text-[#9333ea]`}>{fmt(r.clicks)}</td>
                  <td className={`${cell} text-right`}>{r.ctr}</td>
                  <td className={`${cell} text-right`}>{fmt(r.avg_click_cost)}</td>
                  <td className={`${cell} text-right font-bold text-[#e67700]`}>{fmt(r.total_cost)}</td>
                  <td className={`${cell} text-[11px] text-[#777]`}>{r.product_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-[#aaa]">※ ESM 광고센터 CPC 입찰관리 그리드 기준. 광고그룹=상품 1:1인 계정은 사실상 상품별 광고비입니다. 크롤: python manage.py crawl_gmarket_adgroup</p>
      </div>
    </div>
  );
}
