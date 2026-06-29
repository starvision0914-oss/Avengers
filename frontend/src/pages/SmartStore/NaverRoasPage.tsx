import { useState, useEffect, useCallback } from 'react';
import api from '../../api/client';
import { formatKRW } from '../../utils/format';

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
  status: string;
}
interface Totals {
  cost: number; click: number; impression: number;
  conv_cnt: number; conv_amt: number; roas: number; products: number;
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
  { key: 'roas',         label: 'ROAS',    align: 'right' },
  { key: 'status',       label: '상품상태', align: 'left'  },
];

export default function NaverRoasPage() {
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
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.get('/smartstore/accounts/').then(r =>
      setAccounts(r.data.map((a: any) => ({ id: a.id, name: a.display_name || a.store_name })))
    );
  }, []);

  const load = useCallback((modeArg?: Mode, ymF = ymFrom, ymT = ymTo, aid = accountId, at = adType) => {
    const m = modeArg ?? mode;
    setMode(m);
    setLoading(true);
    api.get('/smartstore/naver-product-roas/', {
      params: { ym_from: ymF, ym_to: ymT, account_id: aid, ad_type: at, ...MODES[m].params },
    }).then(r => {
      setRows(r.data.rows || []);
      setTotals(r.data.totals);
    }).finally(() => setLoading(false));
  }, [ymFrom, ymTo, accountId, adType, mode]);

  useEffect(() => { load(); }, []); // eslint-disable-line

  const sortBy = (k: SortKey) => {
    if (sortKey === k) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(k); setSortDir(TEXT_KEYS.has(k) ? 'asc' : 'desc'); }
  };
  const arr = (k: SortKey) => sortKey === k ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ↕';

  const sorted = [...rows].sort((a, b) => {
    const sgn = sortDir === 'asc' ? 1 : -1;
    if (sortKey === 'status')
      return sgn * ((STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9));
    if (TEXT_KEYS.has(sortKey))
      return sgn * String(a[sortKey]).localeCompare(String(b[sortKey]));
    return sgn * ((Number(a[sortKey]) || 0) - (Number(b[sortKey]) || 0));
  });

  const doExport = () => {
    const p = new URLSearchParams({
      ym_from: ymFrom, ym_to: ymTo, account_id: accountId, ad_type: adType, export: '1',
      ...Object.fromEntries(Object.entries(MODES[mode].params).map(([k, v]) => [k, String(v)])),
    });
    window.open(`/api/smartstore/naver-product-roas/?${p}`);
  };

  const doCopy = () => {
    const header = COLS.map(c => c.label).join('\t');
    const lines = [header, ...sorted.map(r =>
      [r.account_name, r.product_no, r.product_name, r.impression, r.click,
       r.cost, r.conv_cnt, r.conv_amt, r.roas, r.status].join('\t')
    )];
    navigator.clipboard.writeText(lines.join('\n')).then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <div className="p-4 space-y-3 bg-[#f5f6fa] min-h-screen">

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
          <span className="text-[#555]">ROAS <b className={`text-[16px] ${roasColor(totals.roas)}`}>{totals.roas}%</b></span>
          {mode !== 'all' && (
            <span className="text-[13px] text-[#999] ml-auto">기준: {MODES[mode].crit}</span>
          )}
        </div>
      )}

      {/* ── 테이블 ── */}
      <div className="bg-white border border-[#e0e0e0] rounded-lg overflow-hidden">
        <div className="overflow-auto" style={{ maxHeight: 'calc(100vh - 270px)' }}>
          <table className="w-full border-collapse" style={{ minWidth: 1000 }}>
            <thead className="sticky top-0 z-10 bg-[#f5f6f8]">
              <tr>
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
                  <td colSpan={COLS.length} className="text-center py-16 text-[#bbb] text-[15px]">
                    {loading ? '조회 중...' : '조회 결과가 없습니다'}
                  </td>
                </tr>
              )}
              {sorted.map((r, i) => (
                <tr key={`${r.account_id}-${r.product_no}-${i}`}
                  className="hover:bg-[#f8fafc] transition-colors">
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
                  <td className="px-3 py-2 text-[14px] whitespace-nowrap">
                    <span className={statusColor(r.status)}>{r.status}</span>
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
