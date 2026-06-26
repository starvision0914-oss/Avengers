import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, ShoppingBag, Wallet, Megaphone, Package, X } from 'lucide-react';
import api from '../../api/client';

interface Row {
  no: number; login_id: string; seller_name: string; shop_name?: string; balance: number;
  ad_spend: number; cpc_spend: number; ai_spend: number; server_spend: number; auction_spend: number;
  ad_count: number; product_count: number;
  gmarket_products: number; auction_products: number; collected_at: string | null;
  revenue: number; profit: number; net_after_ad: number; orders: number; margin: number; roas: number;
}
interface DashResp {
  date_from: string; date_to: string;
  totals: { ad_spend: number; cpc_spend: number; ai_spend: number; server_spend: number;
    balance: number; product_count: number; account_count: number;
    revenue: number; profit: number; net_after_ad: number; orders: number };
  rows: Row[];
}

const fmt = (n: number) => (n || 0).toLocaleString();
const sv = (d: Date) => d.toLocaleDateString('sv');
type PMode = 'day' | 'month' | 'year' | 'range';

export default function GmarketDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<PMode>('month');
  const [from, setFrom] = useState(sv(new Date(new Date().getFullYear(), new Date().getMonth(), 1)));
  const [to, setTo] = useState(sv(new Date()));
  const [sortKey, setSortKey] = useState<string>('no');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [costModal, setCostModal] = useState<{ seller: string; type?: string } | null>(null);
  const [market, setMarket] = useState<'gmarket' | 'auction' | 'combined'>('combined');

  const applyMode = (m: PMode) => {
    const now = new Date();
    if (m === 'day') { setFrom(sv(now)); setTo(sv(now)); }
    else if (m === 'month') { setFrom(sv(new Date(now.getFullYear(), now.getMonth(), 1))); setTo(sv(now)); }
    else if (m === 'year') { setFrom(`${now.getFullYear()}-01-01`); setTo(sv(now)); }
    setMode(m);
  };
  const setYesterday = () => {
    const d = new Date(); d.setDate(d.getDate() - 1); const s = sv(d);
    setFrom(s); setTo(s); setMode('day');
  };
  const shiftDay = (delta: number) => {
    const b = new Date((to || sv(new Date())) + 'T00:00:00'); b.setDate(b.getDate() + delta);
    const s = sv(b); setFrom(s); setTo(s); setMode('day');
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<DashResp>('/cpc/gmarket/dashboard/', { params: { date_from: from, date_to: to, market } });
      setData(data);
    } catch { /* noop */ } finally { setLoading(false); }
  }, [from, to, market]);
  useEffect(() => { load(); }, [load]);

  // 상품별광고비 수집 상태(실패 요약 + 재크롤)
  const [cstat, setCstat] = useState<any>(null);
  const [recrawling, setRecrawling] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const loadCstat = useCallback(() => {
    api.get('/cpc/gmarket/crawl-status/').then(r => setCstat(r.data)).catch(() => {});
  }, []);
  useEffect(() => {
    loadCstat();
    const t = setInterval(loadCstat, 5000);
    return () => clearInterval(t);
  }, [loadCstat]);
  const recrawlFailed = async () => {
    const ids = (cstat?.failed || []).map((f: any) => f.login_id);
    if (!ids.length) return;
    if (!confirm(`실패(미갱신) ${ids.length}계정 상품별 광고비를 재크롤할까요?\n${ids.join(', ')}`)) return;
    setRecrawling(true);
    try {
      await api.post('/cpc/gmarket/recrawl/', { accounts: ids, with_keywords: false });
    } catch { /* noop */ }
    setTimeout(() => setRecrawling(false), 3000);
    loadCstat();
  };

  const acc = (r: Row, k: string): number | string =>
    k === 'ad_only' ? (r.cpc_spend || 0) + (r.ai_spend || 0)
      : k === 'login_id' ? r.login_id
        : k === 'collected_at' ? (r.collected_at || '')
          : Number((r as any)[k] || 0);
  const rows = [...(data?.rows || [])].sort((a, b) => {
    const va = acc(a, sortKey), vb = acc(b, sortKey);
    const c = typeof va === 'string' ? String(va).localeCompare(String(vb)) : Number(va) - Number(vb);
    return sortDir === 'asc' ? c : -c;
  });
  const sortBy = (k: string) => {
    if (sortKey === k) setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(k); setSortDir('desc'); }
  };
  const sums = (data?.rows || []).reduce((s, r) => {
    s.balance += r.balance || 0; s.cpc_spend += r.cpc_spend || 0; s.ai_spend += r.ai_spend || 0;
    s.server_spend += r.server_spend || 0; s.auction_spend += r.auction_spend || 0; s.ad_spend += r.ad_spend || 0;
    s.product_count += r.product_count || 0; s.gmarket_products += r.gmarket_products || 0;
    s.auction_products += r.auction_products || 0;
    s.revenue += r.revenue || 0; s.profit += r.profit || 0; s.net_after_ad += r.net_after_ad || 0;
    return s;
  }, { balance: 0, cpc_spend: 0, ai_spend: 0, server_spend: 0, auction_spend: 0, ad_spend: 0, product_count: 0, gmarket_products: 0, auction_products: 0, revenue: 0, profit: 0, net_after_ad: 0 });
  const t = data?.totals;
  const cell = 'px-3 py-1.5';
  const arrow = (k: string) => (sortKey === k ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '');
  const Th = ({ k, label, left }: { k: string; label: string; left?: boolean }) => (
    <th className={`${cell} ${left ? 'text-left' : 'text-right'} cursor-pointer select-none hover:bg-[#eee]`} onClick={() => sortBy(k)}>{label}{arrow(k)}</th>
  );
  const pbtn = (m: PMode, label: string) => (
    <button onClick={() => applyMode(m)} className={`px-2.5 py-1 rounded text-[12px] font-semibold ${mode === m ? 'bg-[#00a651] text-white' : 'bg-white border text-[#555]'}`}>{label}</button>
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
        <h1 className="text-[12px] font-bold text-[#333]">지마켓/옥션 대시보드</h1>
        {loading && <span className="text-[11px] text-[#999] animate-pulse">로딩중...</span>}
        <div className="ml-auto flex flex-wrap items-center gap-1.5 text-[12px]">
          <button onClick={load} className="inline-flex items-center gap-1 px-2.5 py-1 bg-[#00a651] text-white rounded font-semibold"><RefreshCw size={13} /> 새로고침</button>
          {pbtn('day', '오늘')}
          <button onClick={setYesterday} className={`px-2.5 py-1 rounded text-[12px] font-semibold ${from === to && from !== sv(new Date()) ? 'bg-[#00a651] text-white' : 'bg-white border text-[#555]'}`}>어제</button>
          {pbtn('month', '월간')}{pbtn('year', '년간')}{pbtn('range', '기간별')}
          <button onClick={() => shiftDay(-1)} title="하루 전" className="px-2 py-1 rounded text-[12px] bg-white border text-[#555]">◀</button>
          <input type="date" value={from} onChange={e => { setFrom(e.target.value); setMode('range'); }} className="border rounded px-2 py-1" />
          <span>~</span>
          <input type="date" value={to} onChange={e => { setTo(e.target.value); setMode('range'); }} className="border rounded px-2 py-1" />
          <button onClick={() => shiftDay(1)} title="하루 후" className="px-2 py-1 rounded text-[12px] bg-white border text-[#555]">▶</button>
          <button onClick={() => navigate('/gmarket-my')} className="px-2.5 py-1 bg-[#9333ea] text-white rounded font-semibold">상품목록</button>
          <button onClick={() => navigate('/gmarket-adgroup')} className="px-2.5 py-1 bg-[#e67700] text-white rounded font-semibold">광고그룹별</button>
          <button onClick={() => navigate('/gmarket-roas')} className="px-2.5 py-1 bg-[#2563eb] text-white rounded font-semibold">지마켓/옥션 상품 ROAS</button>
          <div className="inline-flex rounded overflow-hidden border border-[#ccc] ml-1">
            <button onClick={() => setMarket('combined')} className={`px-3 py-1 text-[12px] font-bold ${market === 'combined' ? 'bg-[#555] text-white' : 'bg-white text-[#666]'}`}>종합</button>
            <button onClick={() => setMarket('gmarket')} className={`px-3 py-1 text-[12px] font-bold ${market === 'gmarket' ? 'bg-[#00a651] text-white' : 'bg-white text-[#666]'}`}>지마켓</button>
            <button onClick={() => setMarket('auction')} className={`px-3 py-1 text-[12px] font-bold ${market === 'auction' ? 'bg-[#e4002b] text-white' : 'bg-white text-[#666]'}`}>옥션</button>
          </div>
        </div>
      </div>

      <div className="max-w-[1600px] mx-auto px-6 py-3 space-y-3">
        {/* 상품별광고비 수집 상태 — 실패 요약 + 재크롤 */}
        {cstat && (
          <div className={`rounded-lg border px-4 py-2.5 text-[12px] ${(cstat.failed?.length ? 'bg-red-50 border-red-300' : 'bg-green-50 border-green-200')}`}>
            <div className="flex items-center flex-wrap gap-2">
              <b className="text-[#333]">상품별 광고비 수집:</b>
              <span className="text-green-700">완료 {cstat.done}/{cstat.total}</span>
              {cstat.failed?.length > 0 && <span className="text-red-600 font-bold">· 실패 {cstat.failed.length}계정</span>}
              {cstat.running && <span className="text-orange-600 inline-flex items-center gap-1"><RefreshCw size={12} className="animate-spin" />수집 중</span>}
              {cstat.failed?.length > 0 && (
                <button onClick={recrawlFailed} disabled={recrawling || cstat.running}
                  className="ml-auto inline-flex items-center gap-1 px-3 py-1.5 rounded bg-red-600 text-white font-semibold disabled:opacity-50">
                  <RefreshCw size={12} className={recrawling ? 'animate-spin' : ''} /> 실패계정 재크롤 ({cstat.failed.length})
                </button>
              )}
              {cstat.errors?.length > 0 && (
                <button onClick={() => setShowErrors(v => !v)} className="text-[11px] text-[#888] underline">
                  {showErrors ? '원인 닫기' : `원인 보기(${cstat.errors.length})`}
                </button>
              )}
            </div>
            {cstat.failed?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1.5">
                {cstat.failed.map((f: any) => (
                  <span key={f.login_id} className="px-1.5 py-0.5 rounded bg-white border border-red-200 text-red-700 text-[11px]">
                    {f.login_id} <span className="text-[#aaa]">({f.last})</span>
                  </span>
                ))}
              </div>
            )}
            {showErrors && cstat.errors?.length > 0 && (
              <div className="mt-1.5 border-t border-red-200 pt-1.5 space-y-0.5 max-h-32 overflow-y-auto">
                {cstat.errors.map((e: any, i: number) => (
                  <div key={i} className="text-[11px] text-[#a00]">{e.at} [{e.account}] {e.msg}</div>
                ))}
              </div>
            )}
          </div>
        )}
        <div className="text-[12px] text-[#888]">기간: <b className="text-[#333]">{data?.date_from} ~ {data?.date_to}</b></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Card icon={<Megaphone size={18} />} color="#e67700" label="CPC 광고비" value={`${fmt(t?.cpc_spend || 0)}원`} />
          <Card icon={<Megaphone size={18} />} color="#9333ea" label="AI매출업" value={`${fmt(t?.ai_spend || 0)}원`} />
          <Card icon={<Megaphone size={18} />} color="#dc2626" label="서버비용" value={`${fmt(t?.server_spend || 0)}원`} />
          <Card icon={<Wallet size={18} />} color="#1e6fd9" label="잔액 합계" value={`${fmt(t?.balance || 0)}원`} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Card icon={<ShoppingBag size={18} />} color="#1e6fd9" label="매출" value={`${fmt(t?.revenue || 0)}원`} />
          <Card icon={<Megaphone size={18} />} color="#e08000" label="광고비 합계" value={`${fmt(t?.ad_spend || 0)}원`} />
          <Card icon={<Wallet size={18} />} color="#7c3aed" label="순수익(−원가−광고비)" value={`${fmt(t?.net_after_ad || 0)}원`} />
        </div>
        <div className="grid grid-cols-3 gap-2">
          <Card icon={<ShoppingBag size={18} />} color="#00a651" label="계정 수" value={`${fmt(t?.account_count || 0)}개`} />
          <Card icon={<Package size={18} />} color="#9333ea" label="수집 상품 수" value={`${fmt(t?.product_count || 0)}개`} />
          <Card icon={<ShoppingBag size={18} />} color="#555" label="주문 수" value={`${fmt(t?.orders || 0)}건`} />
        </div>

        <div className="bg-white border border-[#e0e0e0] rounded-lg overflow-auto">
          <table className="w-full text-[12px]">
            <thead className="bg-[#f7f7f7] text-[#666]">
              <tr>
                <Th k="no" label="번호" left />
                <Th k="login_id" label="계정" left />
                <Th k="balance" label="잔액" />
                <Th k="cpc_spend" label="CPC" />
                <Th k="ai_spend" label="AI매출업" />
                <Th k="server_spend" label="서버비용" />
                <Th k="ad_spend" label="광고비합계" />
                <Th k="revenue" label="매출" />
                <Th k="net_after_ad" label="순수익" />
                <Th k="roas" label="ROAS" />
                <Th k="margin" label="마진%" />
                <Th k="product_count" label="상품 수" />
                <Th k="collected_at" label="최종수집" left />
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f0f0]">
              {rows.length === 0 ? (
                <tr><td colSpan={13} className="px-3 py-8 text-center text-[#aaa]">데이터 없음</td></tr>
              ) : (<>
                <tr className="bg-[#eef5ff] font-bold text-[#222] border-b-2 border-[#cfe0f5]">
                  <td className={cell}></td>
                  <td className={cell}>합계 ({t?.account_count ?? rows.length}개)</td>
                  <td className={`${cell} text-right`}>{fmt(sums.balance)}</td>
                  <td className={`${cell} text-right text-[#e67700]`}>{fmt(sums.cpc_spend)}</td>
                  <td className={`${cell} text-right text-[#9333ea]`}>{fmt(sums.ai_spend)}</td>
                  <td className={`${cell} text-right text-[#dc2626]`}>{fmt(sums.server_spend)}</td>
                  <td className={`${cell} text-right`}>{fmt(sums.ad_spend)}</td>
                  <td className={`${cell} text-right text-[#1e6fd9]`}>{fmt(sums.revenue)}</td>
                  <td className={`${cell} text-right text-[#7c3aed]`}>{fmt(sums.net_after_ad)}</td>
                  <td className={`${cell} text-right`}>{sums.ad_spend ? (sums.revenue / sums.ad_spend).toFixed(1) : '-'}</td>
                  <td className={`${cell} text-right`}>{sums.revenue ? (sums.net_after_ad * 100 / sums.revenue).toFixed(1) : '0'}%</td>
                  <td className={`${cell} text-right`}>{fmt(sums.product_count)}</td>
                  <td className={cell}></td>
                </tr>
                {rows.map(r => (
                <tr key={r.login_id} className="hover:bg-[#fafafa]">
                  <td className={`${cell} text-[#999] font-mono`}>{r.no}</td>
                  <td className={cell}><span className="font-mono">{r.login_id}</span> <span className="text-[#1e6fd9] text-[11px] font-semibold">{r.shop_name && r.shop_name !== r.login_id ? r.shop_name.slice(0, 4) : ''}</span></td>
                  <td className={`${cell} text-right`}>{fmt(r.balance)}</td>
                  <td className={`${cell} text-right text-[#e67700] cursor-pointer hover:underline`}
                    title="클릭 → CPC 내역" onClick={() => setCostModal({ seller: r.login_id, type: 'CPC' })}>{fmt(r.cpc_spend)}</td>
                  <td className={`${cell} text-right text-[#9333ea] cursor-pointer hover:underline`}
                    title="클릭 → AI매출업 내역" onClick={() => setCostModal({ seller: r.login_id, type: 'AI매출업' })}>{fmt(r.ai_spend)}</td>
                  <td className={`${cell} text-right text-[#dc2626] cursor-pointer hover:underline`}
                    onClick={() => setCostModal({ seller: r.login_id, type: '서버비용' })}>{fmt(r.server_spend)}</td>
                  <td className={`${cell} text-right font-bold cursor-pointer hover:underline`}
                    onClick={() => setCostModal({ seller: r.login_id })}>{fmt(r.ad_spend)}</td>
                  <td className={`${cell} text-right text-[#1e6fd9]`}>{fmt(r.revenue)}</td>
                  <td className={`${cell} text-right font-semibold text-[#7c3aed]`}>{fmt(r.net_after_ad)}</td>
                  <td className={`${cell} text-right ${r.roas && r.roas < 100 ? 'text-red-500' : 'text-[#555]'}`}>{r.roas || '-'}</td>
                  <td className={`${cell} text-right ${r.margin && r.margin < 20 ? 'text-red-500 font-semibold' : 'text-[#555]'}`}>{r.margin}%</td>
                  <td className={`${cell} text-right font-semibold`}>{fmt(r.product_count)}</td>
                  <td className={`${cell} text-left text-[11px] text-[#999]`}>{r.collected_at ? r.collected_at.replace('T', ' ').slice(0, 16) : '-'}</td>
                </tr>
                ))}
              </>)}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-[#aaa]">※ CPC·AI매출업 = ESM 광고센터 '당일 소진액'을 기간 내 일별로 합산. 숫자를 클릭하면 일별 내역이 모달로 보입니다. (크롤이 안 된 날은 합산에서 빠집니다)</p>
      </div>

      {costModal && <CostModal seller={costModal.seller} type={costModal.type} from={from} to={to} onClose={() => setCostModal(null)} />}
    </div>
  );
}

const TYPE_COLOR: Record<string, { bg: string; text: string }> = {
  CPC:    { bg: '#e7f5ff', text: '#228be6' },
  AI매출업: { bg: '#fff3e0', text: '#e08000' },
  서버비용:  { bg: '#f3e5f5', text: '#7b1fa2' },
};

function CostModal({ seller, type, from, to, onClose }: { seller: string; type?: string; from: string; to: string; onClose: () => void }) {
  const [d, setD] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.get('/cpc/gmarket/ad-daily/', { params: { seller_id: seller, date_from: from, date_to: to } })
      .then(r => setD(r.data)).catch(() => setD(null)).finally(() => setLoading(false));
  }, [seller, from, to]);

  const rows = type ? (d?.rows || []).filter((x: any) => x.transaction_type === type) : (d?.rows || []);
  const filteredTotal = rows.reduce((s: number, x: any) => s + x.amount, 0);
  const typeLabel = type ? ` · ${type}` : '';

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-[780px] max-w-[95%] max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex flex-wrap items-center gap-2 px-5 py-3 border-b sticky top-0 bg-white">
          <h3 className="text-[12px] font-bold">광고비 거래내역 — {seller}{typeLabel}</h3>
          <span className="text-[12px] text-[#888]">{from} ~ {to}</span>
          {d && (
            <span className="text-[12px] font-bold ml-2">
              {type ? (
                <span style={{ color: TYPE_COLOR[type]?.text || '#333' }}>{type} {fmt(filteredTotal)}원</span>
              ) : (
                <>
                  <span className='text-[#e67700]'>CPC {fmt(d.cpc_spend)}</span>
                  {' · '}
                  <span className='text-[#9333ea]'>AI {fmt(d.ai_spend)}</span>
                  {' · '}합계 {fmt(d.ad_spend)}원
                </>
              )}
              <span className="text-[#aaa] font-normal ml-1">({rows.length}건)</span>
            </span>
          )}
          <button onClick={onClose} className="ml-auto text-[#888] hover:text-black"><X size={18} /></button>
        </div>
        <div className="flex-1 overflow-auto">
          <table className="w-full text-[12px]">
            <thead className="bg-[#f7f7f7] text-[#666] sticky top-0"><tr>
              <th className="px-3 py-1.5 text-left whitespace-nowrap">거래일시</th>
              <th className="px-3 py-1.5 text-left">구분</th>
              <th className="px-3 py-1.5 text-right whitespace-nowrap">금액</th>
              <th className="px-3 py-1.5 text-left">거래내용</th>
              <th className="px-3 py-1.5 text-left text-[#bbb]">마켓</th>
            </tr></thead>
            <tbody className="divide-y divide-[#f0f0f0]">
              {loading
                ? <tr><td colSpan={5} className="px-3 py-8 text-center text-[#aaa]">불러오는 중…</td></tr>
                : !rows.length
                  ? <tr><td colSpan={5} className="px-3 py-8 text-center text-[#aaa]">거래내역 없음</td></tr>
                  : rows.map((x: any, i: number) => {
                    const c = TYPE_COLOR[x.transaction_type] || { bg: '#f5f5f5', text: '#666' };
                    return (
                      <tr key={i} className={`hover:bg-[#fafafa] ${i % 2 ? 'bg-[#fafafa]' : 'bg-white'}`}>
                        <td className="px-3 py-1.5 text-[#888] whitespace-nowrap">{x.traded_at}</td>
                        <td className="px-3 py-1.5">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold" style={{ background: c.bg, color: c.text }}>{x.transaction_type}</span>
                        </td>
                        <td className="px-3 py-1.5 text-right font-medium">{x.amount.toLocaleString()}원</td>
                        <td className="px-3 py-1.5 text-[#555]">{x.comment}</td>
                        <td className="px-3 py-1.5 text-[#bbb] text-[11px]">{x.market}</td>
                      </tr>
                    );
                  })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
