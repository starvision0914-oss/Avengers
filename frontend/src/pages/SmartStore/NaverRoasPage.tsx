import { useState, useEffect, useCallback, useRef } from 'react';
import { PlayCircle } from 'lucide-react';
import api from '../../api/client';
import { formatKRW } from '../../utils/format';

interface LossRow {
  account_id: number;
  id: number;
  product_no: string;
  channel_product_no: string;
  seller_code: string;
  name: string;
  cost: number;
  clicks: number;
  sales: number;
  roas: number;
}

interface Row {
  account_id: number;
  account_name: string;
  product_no: string;
  product_name: string;
  cost: number;
  click: number;
  impression: number;
  conv_cnt: number;
  conv_amt: number;
  roas: number;
  real_sales: number;
  real_roas: number;
  status: string;
}
interface Totals {
  cost: number; click: number; impression: number;
  conv_cnt: number; conv_amt: number; roas: number; products: number;
  real_sales: number; real_roas: number;
}
interface SearchTermRow {
  account_id: number;
  account_name: string;
  keyword: string;
  impression: number;
  click: number;
  cost: number;
  conv_cnt: number;
  conv_amt: number;
  roas: number;
}

const now = new Date();
const ymStr = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
const addMonths = (ym: string, n: number) => {
  const [y, m] = ym.split('-').map(Number);
  return ymStr(new Date(y, m - 1 + n, 1));
};

function roasColor(r: number) {
  if (!r) return 'text-[#dc2626] font-bold';
  if (r >= 300) return 'text-[#16a34a] font-bold';
  if (r >= 100) return 'text-[#d97706] font-semibold';
  return 'text-[#dc2626] font-semibold';
}
function statusColor(s: string) {
  if (s === '판매중') return 'text-[#16a34a] font-semibold';
  if (s === '판매중지' || s === '품절') return 'text-[#d97706] font-semibold';
  if (s === '판매금지') return 'text-[#dc2626] font-semibold';
  return 'text-[#999]';
}
const STATUS_ORDER: Record<string, number> = { '판매중': 1, '판매중지': 2, '품절': 3, '승인대기': 4, '판매금지': 5 };

type Mode = 'all' | 'loss' | 'high';
const MODES: Record<Mode, { label: string; bg: string; text: string; crit: string; params: Record<string, any> }> = {
  all:  { label: '전체',    bg: '#f3f4f6', text: '#374151', crit: '광고비 발생 전체', params: {} },
  loss: { label: '적자상품', bg: '#fee2e2', text: '#dc2626', crit: '광고비≥2000 · ROAS≤100 · 클릭≥10', params: { cost_min: 2000, roas_max: 100, clicks_min: 10 } },
  high: { label: '우수상품', bg: '#dcfce7', text: '#16a34a', crit: 'ROAS≥200%', params: { roas_min: 200 } },
};

type SortKey = keyof Row;
const TEXT_KEYS = new Set<SortKey>(['product_no', 'product_name', 'account_name', 'status']);

const COLS: { key: SortKey; label: string; align: 'left' | 'right' }[] = [
  { key: 'account_name', label: '계정',    align: 'left'  },
  { key: 'product_no',   label: '상품번호', align: 'left'  },
  { key: 'product_name', label: '상품명',   align: 'left'  },
  { key: 'impression',   label: '노출수',   align: 'right' },
  { key: 'click',        label: '클릭수',   align: 'right' },
  { key: 'cost',         label: '광고비',   align: 'right' },
  { key: 'conv_cnt',     label: '구매수',   align: 'right' },
  { key: 'conv_amt',     label: '구매금액', align: 'right' },
  { key: 'roas',         label: 'ROAS(광고센터)', align: 'right' },
  { key: 'real_sales',   label: '실매출(정산)', align: 'right' },
  { key: 'real_roas',    label: 'ROAS(실매출)', align: 'right' },
  { key: 'status',       label: '상품상태', align: 'left'  },
];

export default function NaverRoasPage() {
  const [view, setView] = useState<'product' | 'keyword'>('product');
  const curYM = ymStr(now);
  const [ymFrom, setYmFrom] = useState(curYM);
  const [ymTo,   setYmTo]   = useState(curYM);
  const [accountId, setAccountId] = useState('');
  const [adType,    setAdType]    = useState('');
  const [mode,  setMode]  = useState<Mode>('all');
  const [rows,  setRows]  = useState<Row[]>([]);
  const [totals, setTotals] = useState<Totals | null>(null);
  const [loading, setLoading] = useState(false);
  const [accounts, setAccounts] = useState<{ id: number; name: string }[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>('cost');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState('');
  const loadTicket = useRef(0);
  const [copied, setCopied] = useState(false);

  // ── 적자상품 모드(기간 자유 선택, 예: 1년) — 화면에 뜬 행을 골라 판매중지/광고OFF.
  // NaverProductRoasView의 product_no는 mallProductId(channel_product_no)라 별도 매칭 불필요.
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const rowKey = (r: Row) => `${r.account_id}-${r.product_no}`;
  const toggleSelect = (r: Row) => setSelected(prev => {
    const next = new Set(prev);
    const k = rowKey(r);
    if (next.has(k)) next.delete(k); else next.add(k);
    return next;
  });
  const [actionMsg, setActionMsg] = useState('');
  const [actionBusy, setActionBusy] = useState(false);

  const selectedItems = () => rows.filter(r => selected.has(rowKey(r)))
    .map(r => ({ account_id: r.account_id, product_no: r.product_no }));

  const bulkSuspend = () => {
    const items = selectedItems();
    if (!items.length) { alert('선택된 상품이 없습니다.'); return; }
    if (!confirm(`선택한 ${items.length}개 상품을 판매중지할까요?`)) return;
    setActionBusy(true); setActionMsg('');
    api.post('/smartstore/naver-product-roas/suspend/', { items })
      .then(r => setActionMsg(r.data.message))
      .catch(e => setActionMsg(e?.response?.data?.message || '판매중지 요청 실패'))
      .finally(() => setActionBusy(false));
  };
  const bulkAdOff = () => {
    // 사용자 지시(2026-09-04): 판매중지/품절 상품은 광고 꺼봐야 의미 없으니, 선택 중
    // 판매중(SALE) 상품만 실제 광고 OFF 대상으로 삼는다(나머지는 조용히 제외).
    const saleRows = rows.filter(r => selected.has(rowKey(r)) && r.status === '판매중');
    const skipped = selected.size - saleRows.length;
    if (!saleRows.length) { alert('선택한 상품 중 판매중 상태가 없습니다. (광고 OFF는 판매중 상품에만 적용됩니다)'); return; }
    const items = saleRows.map(r => ({ account_id: r.account_id, product_no: r.product_no }));
    const msg = skipped > 0
      ? `선택한 ${selected.size}개 중 판매중 ${items.length}개만 광고 OFF합니다(판매중 아닌 ${skipped}개 제외). 진행할까요?`
      : `선택한 ${items.length}개 상품의 광고를 OFF할까요?`;
    if (!confirm(msg)) return;
    setActionBusy(true); setActionMsg('');
    api.post('/smartstore/naver-product-roas/ad-off/', { items })
      .then(r => setActionMsg(r.data.message))
      .catch(e => setActionMsg(e?.response?.data?.message || '광고 OFF 요청 실패'))
      .finally(() => setActionBusy(false));
  };

  // ── 실매출 기준 적자상품(판매중지) — 11번가/지마켓과 달리 광고센터 전환매출이 아니라
  // 실제 정산매출로 판정(오탐 방지). 조건: ROAS≤100 · 광고비≥3000 · 클릭≥10 (이번달)
  const [showLoss, setShowLoss] = useState(false);
  const [lossRows, setLossRows] = useState<LossRow[]>([]);
  const [lossLoading, setLossLoading] = useState(false);
  const [lossMsg, setLossMsg] = useState('');
  const lossParams = { roas_max: 100, cost_min: 3000, clicks_min: 10 };

  const loadLoss = useCallback(() => {
    setLossLoading(true);
    api.get('/smartstore/loss-products/', { params: lossParams })
      .then(r => setLossRows(r.data.items || []))
      .finally(() => setLossLoading(false));
  }, []);

  const openLoss = () => { setShowLoss(true); setLossMsg(''); loadLoss(); };

  const suspendLoss = () => {
    if (!lossRows.length) { alert('대상 적자상품이 없습니다.'); return; }
    if (!confirm(`실매출 ROAS≤100% · 광고비≥3,000원 상품 ${lossRows.length}개를 판매중지할까요?`)) return;
    api.post('/smartstore/loss-products/suspend/', lossParams)
      .then(r => setLossMsg(r.data.message || '판매중지 시작됨'))
      .catch(e => setLossMsg(e?.response?.data?.message || '판매중지 요청 실패'));
  };

  useEffect(() => {
    api.get('/smartstore/accounts/').then(r =>
      setAccounts(r.data.map((a: any) => ({ id: a.id, name: a.display_name || a.store_name })))
    );
  }, []);

  const load = useCallback((modeArg?: Mode, ymF = ymFrom, ymT = ymTo, aid = accountId, at = adType) => {
    const m = modeArg ?? mode;
    const ticket = ++loadTicket.current;
    setMode(m);
    setLoading(true);
    // 조회 중엔 이전(다른 기간/모드) 데이터를 화면에 남겨두지 않는다 — 남겨두면 사용자가
    // 그 사이에 체크박스를 눌러도 응답 도착 후 목록이 바뀌면서 선택이 통째로 사라져
    // "선택 광고 OFF"를 눌러도 아무 반응이 없는 것처럼 보이는 버그가 있었음(2026-09-04).
    setRows([]);
    setSelected(new Set());
    api.get('/smartstore/naver-product-roas/', {
      params: { ym_from: ymF, ym_to: ymT, account_id: aid, ad_type: at, ...MODES[m].params },
    }).then(r => {
      if (ticket !== loadTicket.current) return; // 더 최신 요청이 이미 나감 — 이 응답은 버림
      setRows(r.data.rows || []);
      setTotals(r.data.totals);
    }).finally(() => { if (ticket === loadTicket.current) setLoading(false); });
  }, [ymFrom, ymTo, accountId, adType, mode]);

  useEffect(() => { load(); }, []); // eslint-disable-line

  const sortBy = (k: SortKey) => {
    if (sortKey === k) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(k); setSortDir(TEXT_KEYS.has(k) ? 'asc' : 'desc'); }
  };
  const arr = (k: SortKey) => sortKey === k ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ↕';

  const sorted = [...rows]
    .filter(r => !statusFilter || r.status === statusFilter)
    .sort((a, b) => {
      // 적자상품 모드에서는 정렬 기준과 무관하게 판매중 상품을 항상 먼저 보여준다(2026-09-04 지시).
      if (mode === 'loss' && sortKey !== 'status') {
        const so = (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9);
        if (so !== 0) return so;
      }
      const sgn = sortDir === 'asc' ? 1 : -1;
      if (sortKey === 'status')
        return sgn * ((STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9));
      if (TEXT_KEYS.has(sortKey))
        return sgn * String(a[sortKey]).localeCompare(String(b[sortKey]));
      return sgn * ((Number(a[sortKey]) || 0) - (Number(b[sortKey]) || 0));
    });

  const doExport = () => {
    const header = COLS.map(c => c.label).join(',');
    const lines = [header, ...sorted.map(r =>
      [r.account_name, r.product_no, r.product_name, r.impression, r.click,
       r.cost, r.conv_cnt, r.conv_amt, r.roas, r.real_sales, r.real_roas, r.status]
        .map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')
    )];
    const csv = '﻿' + lines.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `naver_product_roas_${ymFrom}_${ymTo}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const doCopy = () => {
    const header = COLS.map(c => c.label).join('\t');
    const lines = [header, ...sorted.map(r =>
      [r.account_name, r.product_no, r.product_name, r.impression, r.click,
       r.cost, r.conv_cnt, r.conv_amt, r.roas, r.real_sales, r.real_roas, r.status].join('\t')
    )];
    navigator.clipboard.writeText(lines.join('\n')).then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <div className="p-4 space-y-3 bg-[#f5f6fa] min-h-screen">

      {/* ── 뷰 전환 탭 ── */}
      <div className="flex gap-1.5">
        {([['product', '상품별 ROAS'], ['keyword', '검색어']] as const).map(([v, label]) => (
          <button key={v} onClick={() => setView(v)}
            className={`px-4 py-1.5 text-[14px] font-semibold rounded-t border-b-2 transition-colors ${
              view === v ? 'bg-white border-[#2563eb] text-[#2563eb]' : 'bg-transparent border-transparent text-[#888] hover:text-[#555]'}`}>
            {label}
          </button>
        ))}
      </div>

      {view === 'keyword' && <NaverSearchTermSection accounts={accounts} />}

      {view === 'product' && <>
      {/* ── 컨트롤 바 ── */}
      <div className="bg-white border border-[#e0e0e0] rounded-lg px-4 py-3 flex flex-wrap items-center gap-2">
        <h1 className="text-[17px] font-bold text-[#222] mr-1">네이버 상품별 ROAS</h1>

        {/* 기간 */}
        <input type="month" value={ymFrom} max={ymTo}
          onChange={e => setYmFrom(e.target.value)}
          className="border border-[#ddd] rounded px-2 py-1 text-[14px] text-[#333] bg-white" />
        <span className="text-[#aaa]">~</span>
        <input type="month" value={ymTo} min={ymFrom} max={curYM}
          onChange={e => setYmTo(e.target.value)}
          className="border border-[#ddd] rounded px-2 py-1 text-[14px] text-[#333] bg-white" />
        {[['이번달', () => { setYmFrom(curYM); setYmTo(curYM); }],
          ['지난달', () => { const p = addMonths(curYM, -1); setYmFrom(p); setYmTo(p); }],
          ['올해',   () => { setYmFrom(`${now.getFullYear()}-01`); setYmTo(curYM); }],
        ].map(([lbl, fn]: any) => (
          <button key={lbl as string} onClick={fn}
            className="px-2 py-1 text-[13px] rounded border border-[#ddd] text-[#555] hover:border-[#2563eb] hover:text-[#2563eb]">{lbl}</button>
        ))}

        {/* 계정 / 광고유형 */}
        <select value={accountId} onChange={e => setAccountId(e.target.value)}
          className="border border-[#ddd] rounded px-2 py-1 text-[14px] text-[#333] bg-white">
          <option value="">전체 계정</option>
          {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <select value={adType} onChange={e => setAdType(e.target.value)}
          className="border border-[#ddd] rounded px-2 py-1 text-[14px] text-[#333] bg-white">
          <option value="">CPC+AI</option>
          <option value="cpc">CPC</option>
          <option value="ai">AI</option>
        </select>
        <button onClick={() => load(mode, ymFrom, ymTo, accountId, adType)}
          className="px-4 py-1.5 text-[14px] font-semibold text-white rounded bg-[#2563eb] hover:bg-[#1d4ed8]">
          {loading ? '조회중...' : '조회'}
        </button>

        {/* 모드 */}
        <div className="flex gap-1.5 ml-1">
          {(Object.keys(MODES) as Mode[]).map(m => (
            <button key={m} onClick={() => load(m, ymFrom, ymTo, accountId, adType)}
              title={MODES[m].crit}
              className="px-3 py-1.5 text-[14px] font-semibold rounded border transition-colors"
              style={mode === m
                ? { background: MODES[m].text, color: '#fff', borderColor: MODES[m].text }
                : { background: MODES[m].bg, color: MODES[m].text, borderColor: 'transparent' }}>
              {MODES[m].label}
            </button>
          ))}
        </div>

        {/* 복사 / 엑셀 */}
        <div className="flex gap-1.5 ml-auto">
          <button onClick={openLoss} title="실매출 기준(광고센터 전환매출 아님) — ROAS≤100 · 광고비≥3,000 · 클릭≥10 (이번달)"
            className="px-3 py-1.5 text-[14px] font-bold text-white rounded bg-[#c2410c] hover:bg-[#9a3412]">
            🛑 적자상품 판매중지
          </button>
          <button onClick={doCopy}
            className="px-3 py-1.5 text-[14px] rounded border border-[#ddd] text-[#555] hover:text-[#222]">
            {copied ? '✓ 복사됨' : '복사'}
          </button>
          <button onClick={doExport}
            className="px-3 py-1.5 text-[14px] rounded border border-[#ddd] text-[#555] hover:text-[#222]">
            엑셀↓
          </button>
        </div>
      </div>

      {/* ── 요약 ── */}
      {totals && (
        <div className="bg-white border border-[#e0e0e0] rounded-lg px-5 py-2.5 flex gap-6 flex-wrap items-center text-[14px]">
          <span className="text-[#555]">상품 <b className="text-[#222] text-[16px]">{totals.products.toLocaleString()}</b>개</span>
          <span className="text-[#555]">광고비 <b className="text-[#f97316] text-[16px]">{formatKRW(totals.cost)}</b></span>
          <span className="text-[#555]">클릭 <b className="text-[#222] text-[16px]">{totals.click.toLocaleString()}</b></span>
          <span className="text-[#555]">구매금액 <b className="text-[#2563eb] text-[16px]">{formatKRW(totals.conv_amt)}</b></span>
          <span className="text-[#555]">ROAS(광고센터) <b className={`text-[16px] ${roasColor(totals.roas)}`}>{totals.roas}%</b></span>
          <span className="text-[#555]">실매출 <b className="text-[#16a34a] text-[16px]">{formatKRW(totals.real_sales)}</b></span>
          <span className="text-[#555]">ROAS(실매출) <b className={`text-[16px] ${roasColor(totals.real_roas)}`}>{totals.real_roas}%</b></span>
          {mode !== 'all' && (
            <span className="text-[13px] text-[#999] ml-auto">기준: {MODES[mode].crit}</span>
          )}
        </div>
      )}

      {/* ── 적자상품 모드: 선택 판매중지/광고OFF (기간 제약 없음, 화면에 뜬 행 대상) ── */}
      {mode === 'loss' && (
        <div className="bg-white border border-[#e0e0e0] rounded-lg px-5 py-2.5 flex items-center gap-3 text-[13px]">
          <span className="text-[#555]">선택 <b className="text-[#222]">{selected.size}</b>개</span>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            title="상품상태로 목록 필터링 (기본은 판매중이 항상 맨 위)"
            className="px-2 py-1 rounded border border-[#ddd] text-[#555] bg-white">
            <option value="">상태: 전체</option>
            {Object.keys(STATUS_ORDER).map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <button onClick={() => setSelected(new Set(sorted.map(rowKey)))}
            className="px-2.5 py-1 rounded border border-[#ddd] text-[#555] hover:border-[#2563eb] hover:text-[#2563eb]">전체선택</button>
          <button onClick={() => setSelected(new Set())}
            className="px-2.5 py-1 rounded border border-[#ddd] text-[#555] hover:border-[#2563eb] hover:text-[#2563eb]">선택해제</button>
          <button onClick={() => setSelected(new Set(sorted.filter(r => r.real_roas <= 100).map(rowKey)))}
            title="실매출 기준 ROAS가 100% 이하인(정산 매출로도 적자인) 상품만 선택"
            className="px-2.5 py-1 rounded border border-[#dc2626] text-[#dc2626] hover:bg-[#fef2f2]">실매출 100%이하 선택</button>
          <button onClick={bulkSuspend} disabled={actionBusy || selected.size === 0}
            className="px-3 py-1.5 font-bold text-white rounded bg-[#c2410c] hover:bg-[#9a3412] disabled:opacity-40">🛑 선택 판매중지</button>
          <button onClick={bulkAdOff} disabled={actionBusy || selected.size === 0}
            className="px-3 py-1.5 font-bold text-white rounded bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-40">📴 선택 광고 OFF</button>
          {actionMsg && <span className="text-[#16a34a] font-semibold">{actionMsg}</span>}
        </div>
      )}

      {/* ── 테이블 ── */}
      <div className="bg-white border border-[#e0e0e0] rounded-lg overflow-hidden">
        <div className="overflow-auto" style={{ maxHeight: 'calc(100vh - 270px)' }}>
          <table className="w-full border-collapse" style={{ minWidth: 1000 }}>
            <thead className="sticky top-0 z-10 bg-[#f5f6f8]">
              <tr>
                {mode === 'loss' && <th className="px-3 py-2.5 border-b border-[#e5e7eb] w-8"></th>}
                {COLS.map(c => (
                  <th key={c.key}
                    onClick={() => sortBy(c.key)}
                    className={`px-3 py-2.5 text-[13px] font-semibold text-[#555] whitespace-nowrap cursor-pointer select-none hover:text-[#2563eb] border-b border-[#e5e7eb] ${c.align === 'right' ? 'text-right' : 'text-left'}`}>
                    {c.label}<span className="text-[#ccc] ml-0.5">{arr(c.key)}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f3f4f6]">
              {sorted.length === 0 && (
                <tr>
                  <td colSpan={COLS.length + (mode === 'loss' ? 1 : 0)} className="text-center py-16 text-[#bbb] text-[15px]">
                    {loading ? '조회 중...' : '조회 결과가 없습니다'}
                  </td>
                </tr>
              )}
              {sorted.map((r, i) => (
                <tr key={`${r.account_id}-${r.product_no}-${i}`}
                  className="hover:bg-[#f8fafc] transition-colors">
                  {mode === 'loss' && (
                    <td className="px-3 py-2">
                      <input type="checkbox" checked={selected.has(rowKey(r))} onChange={() => toggleSelect(r)} />
                    </td>
                  )}
                  <td className="px-3 py-2 text-[14px] text-[#333] font-medium whitespace-nowrap">{r.account_name}</td>
                  <td className="px-3 py-2 text-[14px] whitespace-nowrap">
                    <a href={`https://smartstore.naver.com/main/products/${r.product_no}`}
                      target="_blank" rel="noreferrer"
                      className="text-[#2563eb] hover:underline">{r.product_no}</a>
                  </td>
                  <td className="px-3 py-2 text-[14px] text-[#333] max-w-[240px]">
                    <span className="block truncate" title={r.product_name}>{r.product_name || '-'}</span>
                  </td>
                  <td className="px-3 py-2 text-[14px] text-right text-[#555]">{r.impression.toLocaleString()}</td>
                  <td className="px-3 py-2 text-[14px] text-right text-[#555]">{r.click.toLocaleString()}</td>
                  <td className="px-3 py-2 text-[14px] text-right font-semibold text-[#f97316]">{r.cost.toLocaleString()}</td>
                  <td className="px-3 py-2 text-[14px] text-right text-[#555]">{r.conv_cnt.toLocaleString()}</td>
                  <td className="px-3 py-2 text-[14px] text-right font-semibold text-[#2563eb]">{r.conv_amt.toLocaleString()}</td>
                  <td className="px-3 py-2 text-[14px] text-right">
                    <span className={roasColor(r.roas)}>{r.roas.toLocaleString()}%</span>
                  </td>
                  <td className="px-3 py-2 text-[14px] text-right font-semibold text-[#16a34a]">{r.real_sales.toLocaleString()}</td>
                  <td className="px-3 py-2 text-[14px] text-right">
                    <span className={roasColor(r.real_roas)}>{r.real_roas.toLocaleString()}%</span>
                  </td>
                  <td className="px-3 py-2 text-[14px] whitespace-nowrap">
                    <span className={statusColor(r.status)}>{r.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      </>}

      {/* ── 적자상품(실매출기준) 판매중지 모달 ── */}
      {showLoss && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowLoss(false)}>
          <div className="bg-white rounded-lg shadow-xl w-[900px] max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-5 py-3 border-b border-[#eee]">
              <h3 className="text-[15px] font-bold text-[#222]">적자상품 (실매출 기준) — ROAS≤100% · 광고비≥3,000원 · 클릭≥10</h3>
              <button onClick={suspendLoss} disabled={lossLoading || !lossRows.length}
                className="ml-auto px-3 py-1.5 text-[13px] font-bold text-white rounded bg-[#c2410c] hover:bg-[#9a3412] disabled:opacity-40">
                🛑 전체 판매중지
              </button>
              <button onClick={() => setShowLoss(false)} className="px-2 py-1 text-[#999] hover:text-[#333]">✕</button>
            </div>
            {lossMsg && <div className="px-5 py-2 text-[13px] text-[#c2410c] bg-[#fff7ed] border-b border-[#fed7aa]">{lossMsg}</div>}
            <div className="overflow-auto flex-1">
              <table className="w-full border-collapse">
                <thead className="sticky top-0 bg-[#f5f6f8]">
                  <tr>
                    {['상품번호', '상품명', '광고비', '실매출', 'ROAS', '클릭'].map((h, i) => (
                      <th key={h} className={`px-3 py-2 text-[12px] font-semibold text-[#555] border-b ${i >= 2 ? 'text-right' : 'text-left'}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f3f4f6]">
                  {lossLoading && <tr><td colSpan={6} className="text-center py-10 text-[#bbb]">조회 중...</td></tr>}
                  {!lossLoading && lossRows.length === 0 && <tr><td colSpan={6} className="text-center py-10 text-[#bbb]">대상 적자상품이 없습니다.</td></tr>}
                  {lossRows.map(r => (
                    <tr key={`${r.account_id}-${r.id}`}>
                      <td className="px-3 py-2 text-[13px]">{r.product_no}</td>
                      <td className="px-3 py-2 text-[13px] max-w-[260px] truncate" title={r.name}>{r.name}</td>
                      <td className="px-3 py-2 text-[13px] text-right text-[#f97316] font-semibold">{formatKRW(r.cost)}</td>
                      <td className="px-3 py-2 text-[13px] text-right">{formatKRW(r.sales)}</td>
                      <td className="px-3 py-2 text-[13px] text-right text-[#dc2626] font-semibold">{r.roas}%</td>
                      <td className="px-3 py-2 text-[13px] text-right">{r.clicks.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 검색어 리포트 (계정 단위 — 네이버 API 제약상 상품별 매칭 불가) ──
function NaverSearchTermSection({ accounts }: { accounts: { id: number; name: string }[] }) {
  const curYM = ymStr(now);
  const [ym, setYm] = useState(curYM);
  const [accountId, setAccountId] = useState('');
  const [sort, setSort] = useState<'conv_amt' | 'cost' | 'click'>('conv_amt');
  const [rows, setRows] = useState<SearchTermRow[]>([]);
  const [availYms, setAvailYms] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    api.get('/smartstore/naver-search-terms/', { params: { ym, account_id: accountId, sort } })
      .then(r => { setRows(r.data.rows || []); setAvailYms(r.data.available_yms || []); })
      .finally(() => setLoading(false));
  }, [ym, accountId, sort]);

  const loadStatus = useCallback(() => {
    api.get('/smartstore/naver-search-terms/crawl/').then(r => setBusy(!!r.data.busy)).catch(() => {});
  }, []);

  useEffect(() => { load(); loadStatus(); }, []); // eslint-disable-line
  useEffect(() => { load(); }, [ym, accountId, sort]); // eslint-disable-line

  const handleCrawl = async () => {
    setMsg('');
    try {
      const r = await api.post('/smartstore/naver-search-terms/crawl/', { ym });
      if (r.data.status === 'busy') setMsg(r.data.error || '이미 실행 중입니다.');
      else setMsg(`수집 시작됨 (${ym}) — 완료까지 계정당 1~2분 정도 걸립니다.`);
    } catch (e: any) {
      setMsg(e?.response?.data?.error || '수집 시작 실패');
    }
    loadStatus();
  };

  const totalCost = rows.reduce((s, r) => s + r.cost, 0);
  const totalConv = rows.reduce((s, r) => s + r.conv_amt, 0);

  return (
    <div className="space-y-3">
      <div className="bg-white border border-[#e0e0e0] rounded-lg px-4 py-3 flex flex-wrap items-center gap-2">
        <select value={ym} onChange={e => setYm(e.target.value)}
          className="border border-[#ddd] rounded px-2 py-1 text-[14px] text-[#333] bg-white">
          {(availYms.includes(ym) ? availYms : [ym, ...availYms]).map(y => <option key={y} value={y}>{y}</option>)}
        </select>
        <select value={accountId} onChange={e => setAccountId(e.target.value)}
          className="border border-[#ddd] rounded px-2 py-1 text-[14px] text-[#333] bg-white">
          <option value="">전체 계정</option>
          {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <select value={sort} onChange={e => setSort(e.target.value as any)}
          className="border border-[#ddd] rounded px-2 py-1 text-[14px] text-[#333] bg-white">
          <option value="conv_amt">구매금액순</option>
          <option value="cost">광고비순</option>
          <option value="click">클릭순</option>
        </select>
        <button onClick={handleCrawl} disabled={busy}
          className="flex items-center gap-1 px-3 py-1.5 text-[14px] font-semibold text-white rounded disabled:opacity-50"
          style={{ background: busy ? '#aaa' : '#0284c7' }}>
          <PlayCircle size={13} className={busy ? 'animate-spin' : ''} />
          {busy ? '수집 중…' : '수집'}
        </button>
        {loading && <span className="text-[12px] text-[#999] animate-pulse">불러오는 중…</span>}
        {msg && <span className="text-[12px] text-[#0284c7] font-semibold">{msg}</span>}
        <span className="text-[12px] text-[#999] ml-auto">
          ※ 계정 단위 집계입니다(네이버 API 제약상 상품별 매칭 불가) — 클릭 또는 구매가 있는 검색어만 표시
        </span>
      </div>

      {rows.length > 0 && (
        <div className="bg-white border border-[#e0e0e0] rounded-lg px-5 py-2.5 flex gap-6 flex-wrap items-center text-[14px]">
          <span className="text-[#555]">검색어 <b className="text-[#222] text-[16px]">{rows.length.toLocaleString()}</b>개</span>
          <span className="text-[#555]">광고비 <b className="text-[#f97316] text-[16px]">{formatKRW(totalCost)}</b></span>
          <span className="text-[#555]">구매금액 <b className="text-[#2563eb] text-[16px]">{formatKRW(totalConv)}</b></span>
        </div>
      )}

      <div className="bg-white border border-[#e0e0e0] rounded-lg overflow-hidden">
        <div className="overflow-auto" style={{ maxHeight: 'calc(100vh - 320px)' }}>
          <table className="w-full border-collapse" style={{ minWidth: 900 }}>
            <thead className="sticky top-0 z-10 bg-[#f5f6f8]">
              <tr>
                {['계정', '검색어', '노출수', '클릭수', '광고비', '구매수', '구매금액', 'ROAS'].map((h, i) => (
                  <th key={h} className={`px-3 py-2.5 text-[13px] font-semibold text-[#555] whitespace-nowrap border-b border-[#e5e7eb] ${i >= 2 ? 'text-right' : 'text-left'}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f3f4f6]">
              {rows.length === 0 && (
                <tr><td colSpan={8} className="text-center py-16 text-[#bbb] text-[15px]">
                  {loading ? '조회 중...' : '조회 결과가 없습니다 — 우측 상단 "수집" 버튼을 눌러주세요.'}
                </td></tr>
              )}
              {rows.map((r, i) => (
                <tr key={`${r.account_id}-${r.keyword}-${i}`} className="hover:bg-[#f8fafc] transition-colors">
                  <td className="px-3 py-2 text-[14px] text-[#333] font-medium whitespace-nowrap">{r.account_name}</td>
                  <td className="px-3 py-2 text-[14px] text-[#333]">{r.keyword}</td>
                  <td className="px-3 py-2 text-[14px] text-right text-[#555]">{r.impression.toLocaleString()}</td>
                  <td className="px-3 py-2 text-[14px] text-right text-[#555]">{r.click.toLocaleString()}</td>
                  <td className="px-3 py-2 text-[14px] text-right font-semibold text-[#f97316]">{r.cost.toLocaleString()}</td>
                  <td className="px-3 py-2 text-[14px] text-right text-[#555]">{r.conv_cnt.toLocaleString()}</td>
                  <td className="px-3 py-2 text-[14px] text-right font-semibold text-[#2563eb]">{r.conv_amt.toLocaleString()}</td>
                  <td className="px-3 py-2 text-[14px] text-right">
                    <span className={roasColor(r.roas)}>{r.roas.toLocaleString()}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
