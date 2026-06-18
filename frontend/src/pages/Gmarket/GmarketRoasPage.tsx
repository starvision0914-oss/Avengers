import { useState, useEffect, useCallback, useRef } from 'react';
import api from '../../api/client';
import { formatKRW } from '../../utils/format';
import GmktKeywordDetailModal from '../../components/gmarket/GmktKeywordDetailModal';

interface AcctRow {
  login_id: string; seller_name: string;
  cpc_cost: number; ai_cost: number; cpc_conv: number; ai_conv: number;
  cpc_products: number; ai_products: number;
  cpc_roas: number; ai_roas: number;
  total_cost: number; total_conv: number; roas: number;
  real_sales: number; real_roas: number;
}
interface Totals {
  cpc_cost: number; ai_cost: number; cpc_conv: number; ai_conv: number;
  cost: number; conv_amount: number;
  cpc_roas: number; ai_roas: number; roas: number;
  real_sales: number; real_roas: number;
}
const ZERO_TOTALS: Totals = { cpc_cost: 0, ai_cost: 0, cpc_conv: 0, ai_conv: 0, cost: 0, conv_amount: 0, cpc_roas: 0, ai_roas: 0, roas: 0, real_sales: 0, real_roas: 0 };
interface ProdRow {
  login_id: string; seller_id: string; seller_name: string;
  product_no: string; seller_code: string; group_name: string; site: string;
  impressions: number; clicks: number; avg_click_cost: number; cost: number;
  orders: number; conv_amount: number; conv_rate: number; roas: number;
  real_sales: number; real_roas: number; real_orders: number; status: string;
  status_stale?: boolean; status_synced_at?: string | null;
  keywords?: { keyword: string; cost: number; clicks: number; conv_amount: number; roas: number }[];
}

// 상태 셀 — 11번가 비고처럼 '마지막 크롤링한 상품번호' 판매상태(최신 스냅샷)를 그대로 표시
function StatusCell({ r }: { r: any }) {
  return (
    <span className={`font-semibold ${statusColor(r.status)}`}
      title={r.status_synced_at ? `최종 수집 ${(r.status_synced_at || '').slice(0, 10)}` : ''}>
      {r.status || '-'}
    </span>
  );
}
interface Pack { products: number; totals: { cost: number; conv_amount: number; clicks: number; impressions: number; roas: number; real_sales: number; real_roas: number }; rows: ProdRow[]; }

const now = new Date();

function roasColor(roas: number): string {
  if (!roas) return 'text-[#dc2626] font-bold';
  if (roas >= 300) return 'text-[#00a651] font-bold';
  if (roas >= 100) return 'text-[#e08000] font-semibold';
  return 'text-[#dc2626] font-semibold';
}

function statusColor(s: string): string {
  if (s === '삭제완료') return 'text-[#1e6fd9] font-bold';
  if (s === '판매중') return 'text-[#00a651]';
  if (s === '삭제' || s === '판매불가') return 'text-[#dc2626]';
  if (s === '판매중지' || s === '판매종료' || s === '품절') return 'text-[#e08000]';
  return 'text-[#888]';
}

// 비고(상품상태) 정렬 우선순위 — 판매중 → 판매중지/품절 → 삭제/판매불가 → 삭제완료 순으로 그룹화
const STATUS_ORDER: Record<string, number> = {
  '판매중': 1, '판매중지': 2, '판매종료': 3, '품절': 4, '판매불가': 5, '삭제': 6, '삭제완료': 7,
};
function statusRank(s: string): number { return STATUS_ORDER[s] ?? 9; }

const ymStr = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
const addMonths = (ym: string, n: number) => {
  const [y, m] = ym.split('-').map(Number);
  const d = new Date(y, m - 1 + n, 1);
  return ymStr(d);
};
type PMode = 'month' | 'last' | 'year' | 'range';

export default function GmarketRoasPage() {
  const curYM = ymStr(now);
  const [ymFrom, setYmFrom] = useState(curYM);
  const [ymTo, setYmTo] = useState(curYM);
  const [pmode, setPmode] = useState<PMode>('month');
  const [accts, setAccts] = useState<AcctRow[]>([]);
  const [totals, setTotals] = useState<Totals>(ZERO_TOTALS);
  const [loading, setLoading] = useState(false);
  // 계정 요약표 정렬
  const [acctSort, setAcctSort] = useState<{ key: keyof AcctRow; dir: 'asc' | 'desc' }>({ key: 'total_cost', dir: 'desc' });
  const acctSortClick = (k: keyof AcctRow) =>
    setAcctSort(s => s.key === k ? { key: k, dir: s.dir === 'asc' ? 'desc' : 'asc' }
      : { key: k, dir: (k === 'login_id' || k === 'seller_name') ? 'asc' : 'desc' });
  const acctArrow = (k: keyof AcctRow) => (acctSort.key === k ? (acctSort.dir === 'asc' ? ' ▲' : ' ▼') : '');
  const sortedAccts: AcctRow[] = (() => {
    const rows = [...accts];
    const { key, dir } = acctSort;
    const txt = (key === 'login_id' || key === 'seller_name');
    rows.sort((a, b) => txt
      ? (dir === 'asc' ? 1 : -1) * String(a[key] || '').localeCompare(String(b[key] || ''))
      : (dir === 'asc' ? 1 : -1) * ((Number(a[key]) || 0) - (Number(b[key]) || 0)));
    return rows;
  })();

  // 상세(계정 클릭) — CPC/AI 구분
  const [detailEid, setDetailEid] = useState<string | null>(null);
  const [detailName, setDetailName] = useState('');
  const [cpc, setCpc] = useState<Pack | null>(null);
  const [ai, setAi] = useState<Pack | null>(null);
  const [tab, setTab] = useState<'cpc' | 'ai'>('cpc');
  const [dLoading, setDLoading] = useState(false);
  const [dSortKey, setDSortKey] = useState<keyof ProdRow>('cost');
  const [dSortDir, setDSortDir] = useState<'asc' | 'desc'>('desc');
  const dSortBy = (k: keyof ProdRow) => {
    if (dSortKey === k) setDSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    else { setDSortKey(k); setDSortDir('desc'); }
  };

  // 상품목록 모달 (11번가식: 항목·정렬·선택·복사·엑셀·삭제완료). 모드: loss/high/all
  type LMode = 'loss' | 'high' | 'all' | 'keyword';
  const LMODES: Record<LMode, { title: string; crit: string; params: any; del: boolean }> = {
    loss: { title: '전체 적자상품', crit: 'ROAS≤100 · 광고비≥2천 · 클릭≥10', params: { cost_min: 2000, roas_max: 100, clicks_min: 10 }, del: true },
    high: { title: 'ROAS 200%↑ 상품', crit: 'ROAS≥200% (구매전환 기준)', params: { roas_min: 200 }, del: false },
    keyword: { title: 'ROAS 200%↑ 키워드(CPC)', crit: '상품·키워드 모두 ROAS≥200% · CPC만', params: { roas_min: 200, ad_type: 'cpc', kw_roas_min: 200 }, del: false },
    all: { title: '전체 상품 ROAS', crit: '광고비 발생 상품 전체', params: {}, del: false },
  };
  const [lossOpen, setLossOpen] = useState(false);
  const [lossMode, setLossMode] = useState<LMode>('loss');
  const [lossData, setLossData] = useState<any | null>(null);
  const [lossLoading, setLossLoading] = useState(false);
  const [lossSort, setLossSort] = useState<{ key: string; dir: 'asc' | 'desc' }>({ key: 'cost', dir: 'desc' });
  const [lossKwExpand, setLossKwExpand] = useState(true);   // 키워드별 행 펼침(기본 ON)
  const [lossSel, setLossSel] = useState<Set<string>>(new Set());
  const [kwBusy, setKwBusy] = useState(false);
  const [kwRunning, setKwRunning] = useState(false);   // 키워드 수집 백그라운드 실행중(폴링)
  const [lossEid, setLossEid] = useState('');          // 현재 적자/ROAS 모달이 보고있는 계정(자동갱신용)
  const [kwYears, setKwYears] = useState<number[] | null>(null);  // 연도-버킷 모드(2025/2026/전체)
  const [lossAd, setLossAd] = useState<'' | 'cpc' | 'ai'>('');    // 광고유형 필터: ''=전체(CPC+AI 합산) / cpc / ai
  const fetchLoss = (mode: LMode, eid = '', ymF = ymFrom, ymT = ymTo, ad: '' | 'cpc' | 'ai' = lossAd) => {
    setLossEid(eid);
    setLossLoading(true); setLossData(null); setLossSel(new Set());
    // 키워드 모드는 CPC 전용(고정), 그 외 모드만 토글(ad)로 CPC/AI/전체 분리
    const adParam = (mode !== 'keyword' && ad) ? { ad_type: ad } : {};
    api.get('/cpc/gmarket/loss-products/', { params: { ym_from: ymF, ym_to: ymT, eid, ...LMODES[mode].params, ...adParam } })
      .then(r => setLossData(r.data)).catch(() => setLossData(null)).finally(() => setLossLoading(false));
  };
  const setLossAdAnd = (ad: '' | 'cpc' | 'ai') => { setLossAd(ad); fetchLoss(lossMode, lossEid, ymFrom, ymTo, ad); };
  const openLoss = (mode: LMode) => { setKwYears(null); setLossMode(mode); setLossOpen(true); fetchLoss(mode, ''); };
  // 연도별 키워드 대상: 기간을 해당 연도로 맞추고 키워드모달 오픈 + 수집대상 연도 기록
  const openKwYear = (years: number[]) => {
    const yf = `${Math.min(...years)}-01`;
    const yt = years.includes(now.getFullYear()) ? curYM : `${Math.max(...years)}-12`;
    setYmFrom(yf); setYmTo(yt); setPmode('range');
    setKwYears(years); setLossMode('keyword'); setLossOpen(true);
    fetchLoss('keyword', '', yf, yt);
  };
  const gmktUrl = (r: any) => r.site === 'A'
    ? `http://itempage3.auction.co.kr/DetailView.aspx?itemno=${String(r.product_no).replace(/\D/g, '')}`
    : `http://item.gmarket.co.kr/Item?goodscode=${String(r.product_no).replace(/\D/g, '')}`;
  const lossSortClick = (k: string) =>
    setLossSort(s => s.key === k ? { key: k, dir: s.dir === 'asc' ? 'desc' : 'asc' }
      : { key: k, dir: (k === 'product_no' || k === 'seller_code' || k === 'status' || k === 'login_id') ? 'asc' : 'desc' });
  const lossArrow = (k: string) => (lossSort.key === k ? (lossSort.dir === 'asc' ? ' ▲' : ' ▼') : '');
  const lossVal = (r: any, key: string) =>
    key === 'kw_count' ? (r.keywords?.length || 0)
      : key === 'avg_click_cost' ? (r.clicks ? Math.round(r.cost / r.clicks) : 0)
        : r[key];
  const lossRows: any[] = (() => {
    const rows = [...(lossData?.rows || [])];
    const { key, dir } = lossSort;
    const sgn = dir === 'asc' ? 1 : -1;
    if (key === 'status') {
      // 비고: 상태 우선순위(판매중→판매중지→삭제…)로 정렬, 동순위는 상품번호순
      rows.sort((a, b) => sgn * ((statusRank(a.status) - statusRank(b.status))
        || String(a.product_no).localeCompare(String(b.product_no))));
      return rows;
    }
    const txt = (key === 'product_no' || key === 'seller_code' || key === 'login_id');
    rows.sort((a, b) => txt
      ? sgn * String(lossVal(a, key) || '').localeCompare(String(lossVal(b, key) || ''))
      : sgn * ((Number(lossVal(a, key)) || 0) - (Number(lossVal(b, key)) || 0)));
    return rows;
  })();
  // 화면 표 표시행 — 키워드 펼침 ON이면 키워드 1개당 1행(상품정보 반복), 체크/번호는 상품 첫 행에만.
  const lossDisp: any[] = lossKwExpand
    ? lossRows.flatMap((r: any, pi: number) => {
        const seen = new Set<string>();
        const kws = (r.keywords || []).filter((k: any) => k.keyword && !seen.has(k.keyword) && seen.add(k.keyword));
        return kws.length
          ? kws.map((k: any, ki: number) => ({ r, k, pi, first: ki === 0 }))
          : [{ r, k: null, pi, first: true }];
      })
    : lossRows.map((r: any, pi: number) => ({ r, k: undefined, pi, first: true }));
  const lossAllChecked = !!lossData && lossData.rows.length > 0 && lossSel.size === lossData.rows.length;
  const toggleLossAll = () => setLossSel(lossAllChecked ? new Set() : new Set((lossData?.rows || []).map((r: any) => r.product_no)));
  const toggleLossSel = (pno: string) => setLossSel(s => { const n = new Set(s); n.has(pno) ? n.delete(pno) : n.add(pno); return n; });
  const lossTargets = (): any[] => { const rows = lossData?.rows || []; return lossSel.size ? rows.filter((r: any) => lossSel.has(r.product_no)) : rows; };
  const copyText = (text: string) => {
    const done = () => alert('복사되었습니다');
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
    else fallbackCopy(text, done);
  };
  const fallbackCopy = (text: string, done: () => void) => {
    const ta = document.createElement('textarea'); ta.value = text;
    ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); done(); } catch { alert('복사 실패 — 수동 선택하세요'); }
    ta.remove();
  };
  const copySellerCodes = () => {
    const v = lossTargets().map((r: any) => r.seller_code).filter(Boolean).join('\n');
    if (!v) { alert('판매자코드 없음'); return; } copyText(v);
  };
  const copyProductNos = () => {
    const seen = new Set<string>();
    const v = lossTargets().map((r: any) => String(r.product_no ?? '').replace(/\D/g, ''))
      .filter((n: string) => n && !seen.has(n) && seen.add(n)).join('\n');
    if (!v) { alert('상품번호 없음'); return; } copyText(v);
  };
  // 지마켓 광고 키워드 대량등록 양식 — 키워드 1개당 1행. 희망클릭비용=평균단가×91%(정수), 광고그룹명 고정 '그룹명1'.
  const bulkRegCsv = (rows: any[], fname: string) => {
    const head = ['판매자ID', '사이트', '광고그룹명', '키워드명', '상품번호', '희망클릭비용'];
    const body: any[][] = [];
    rows.forEach((r: any) => {
      const avg = r.clicks ? Math.round(r.cost / r.clicks) : 0;
      const bid = Math.round(avg * 0.91);
      const site = r.site === 'A' ? 'A' : 'G';   // 옥션=A, 지마켓=G
      const seen = new Set<string>();
      (r.keywords || []).filter((k: any) => k.keyword && !seen.has(k.keyword) && seen.add(k.keyword))
        .forEach((k: any) => body.push([r.login_id, site, '그룹명1', k.keyword, r.product_no, bid]));
    });
    if (!body.length) { alert('키워드가 있는 상품이 없습니다 (키워드 수집 후 가능)'); return; }
    const csv = '﻿' + [head, ...body].map(a => a.map((c: any) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a'); a.href = url; a.download = fname; a.click(); URL.revokeObjectURL(url);
  };
  const lossExcel = () => {
    const rows = lossTargets();
    if (!rows.length) { alert('대상 없음'); return; }
    let head: string[]; let body: any[][];
    if (lossMode === 'keyword') {
      // 키워드 단위 상세 양식 — 계정아이디+상품번호 앞, 상품번호 정렬, (아이디·상품번호·키워드) 중복 제거
      head = ['계정아이디', '상품번호', '판매자코드', '키워드', '노출수', '클릭수', '클릭율', '평균노출순위', '평균클릭비용', '총비용', '구매수', '구매금액', '전환율', '광고수익률'];
      // 먼저 광고비 내림차순으로 모은 뒤 (상품번호+키워드) 중복 제거 → 같은 상품의 동일 키워드는 광고비 큰 1줄만
      const flatAll: any[] = [];
      rows.forEach((r: any) => (r.keywords || []).forEach((k: any) => {
        flatAll.push({ lid: k.login_id || r.login_id || '', pno: r.product_no, sc: r.seller_code, k });
      }));
      flatAll.sort((a, b) => (b.k.cost || 0) - (a.k.cost || 0));
      const seen = new Set<string>();
      const flat: any[] = [];
      for (const x of flatAll) {
        const key = `${x.pno}|${x.k.keyword}`;   // 같은 상품번호의 동일 키워드는 1개만(아이디 무관)
        if (seen.has(key)) continue;
        seen.add(key);
        flat.push(x);
      }
      // 상품번호 오름차순, 같은 상품 내 광고비 내림차순
      flat.sort((a, b) => String(a.pno).localeCompare(String(b.pno)) || ((b.k.cost || 0) - (a.k.cost || 0)));
      body = flat.map((x: any) => [x.lid, x.pno, x.sc, x.k.keyword, x.k.impressions ?? 0, x.k.clicks ?? 0,
        (x.k.click_rate ?? 0) + '%', (x.k.avg_rank || '-'), (x.k.avg_click_cost ?? 0) + '원',
        (x.k.cost ?? 0) + '원', x.k.orders ?? 0, (x.k.conv_amount ?? 0) + '원',
        (x.k.conv_rate ?? 0) + '%', (x.k.roas ?? 0) + '%']);
      if (!body.length) { alert('키워드 없음 (수집된 ROAS≥기준 키워드가 없습니다)'); return; }
    } else {
      head = ['계정', '상품번호', '판매자코드', '누적판매(25~)', '평균단가', '광고비', '키워드', '클릭', '구매수(광고센터)', '구매금액(광고센터)', 'ROAS(광고센터)', '실구매건수(참고)', '실매출(참고)', '실ROAS(참고)', '비고'];
      // 키워드별로 한 줄씩 펼침 — 한 상품에 키워드 N개면 N행, 상품정보(번호·코드·메트릭)는 각 행 반복.
      // 같은 상품 내 동일 키워드는 1개만(중복 제거). 키워드 없는 상품은 키워드 빈칸 1행.
      body = rows.flatMap((r: any) => {
        const avg = r.clicks ? Math.round(r.cost / r.clicks) : 0;
        const cum = r.cum_sold_qty || 0;
        const tail = [r.clicks, r.ad_orders, r.conv_amount, r.roas + '%', r.real_orders, r.real_sales, (r.real_roas || 0) + '%', r.status];
        const seen = new Set<string>();
        const kws = (r.keywords || []).filter((k: any) => k.keyword && !seen.has(k.keyword) && seen.add(k.keyword));
        if (!kws.length) return [[r.login_id, r.product_no, r.seller_code, cum, avg, r.cost, '', ...tail]];
        return kws.map((k: any) => [r.login_id, r.product_no, r.seller_code, cum, avg, r.cost, k.keyword, ...tail]);
      });
    }
    const csv = '﻿' + [head, ...body].map(a => a.map((c: any) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    // 파일명은 현재 모달 모드에 맞게 (적자/ROAS200상품/ROAS200키워드/상품목록)
    const fnameByMode: Record<string, string> = { loss: '적자상품', high: 'ROAS200상품', keyword: 'ROAS200키워드', all: '상품목록' };
    const fnamePart = fnameByMode[lossMode] || '상품목록';
    const a = document.createElement('a'); a.href = url; a.download = `지마켓_${fnamePart}_${ymFrom}_${ymTo}.csv`; a.click();
    URL.revokeObjectURL(url);
  };
  const markLossDeleted = () => {
    const rows = lossTargets();
    if (!rows.length) { alert('대상 적자상품이 없습니다.'); return; }
    if (!window.confirm(`지마켓에서 실제 삭제한 상품을 "삭제완료"(파란색)로 표시할까요?\n\n${rows.length}개를 처리합니다.`)) return;
    api.post('/cpc/gmarket/loss-products/mark-deleted/', { items: rows.map((r: any) => ({ login_id: r.login_id, product_no: r.product_no, seller_code: r.seller_code })) })
      .then(r => { alert(r.data?.message || '삭제완료 처리됨'); fetchLoss(lossMode); })
      .catch(() => alert('처리 실패'));
  };
  // 지마켓 적자상품 자동삭제 — 검증(dry-run) / 실삭제(다단계 확인). 셀러오피스에서 판매중지→재조회→삭제.
  const validateGmktDelete = () => {
    if (!window.confirm('🔎 지마켓 삭제 검증(dry-run)\n\n셀러오피스 접속·상품번호 입력·조회·셀렉터를 1상품으로 확인합니다.\n실제 삭제는 하지 않습니다(안전).\n\n진행할까요?')) return;
    api.post('/cpc/gmarket/loss-products/delete/', { ym_from: ymFrom, ym_to: ymTo, eid: lossEid || '' })
      .then(r => alert(r.data?.message || '검증(dry-run) 시작 — 결과는 텔레그램/로그로 확인하세요.'))
      .catch(e => alert(e?.response?.data?.error || '시작 실패 — 다른 지마켓 크롤이 실행 중일 수 있습니다.'));
  };
  const deleteGmktLoss = () => {
    const n = lossData?.count || 0;
    if (!n) { alert('대상 적자상품이 없습니다.'); return; }
    if (!window.confirm(`⚠️ 위험: 지마켓에서 상품이 실제·영구 삭제됩니다(되돌릴 수 없음).\n\n먼저 [🔎 삭제 검증]으로 셀러오피스 플로우를 확인하셨나요?\n검증을 안 하셨다면 [취소]하고 검증부터 하세요.\n\n검증을 마쳤고, 실제 삭제를 진행하시겠습니까?`)) return;
    const limStr = window.prompt(`안전을 위해 '몇 개만' 테스트 삭제할 수 있습니다.\n\n· 소량 테스트: 숫자 입력 (예: 5) — 처음엔 강력 권장\n· 전체 ${n.toLocaleString()}개 삭제: 비워두고 확인`, '5');
    if (limStr === null) return;
    const t = limStr.trim();
    const limit = t ? parseInt(t, 10) : null;
    if (limit !== null && (isNaN(limit) || limit < 1)) { alert('숫자를 입력하거나, 전체 삭제는 비워두세요.'); return; }
    const label = limit ? `${limit}개(테스트)` : `전체 ${n.toLocaleString()}개`;
    if (!window.confirm(`최종 확인 ⚠️\n\n${label} 상품을 지마켓에서 영구 삭제합니다.\n정말 진행하시겠습니까?`)) return;
    const body: any = { ym_from: ymFrom, ym_to: ymTo, eid: lossEid || '', real: 1 };
    if (limit) body.limit = limit;
    api.post('/cpc/gmarket/loss-products/delete/', body)
      .then(r => alert(r.data?.message || '실삭제 시작 — 진행상황은 텔레그램/로그로 확인하세요.'))
      .catch(e => alert(e?.response?.data?.error || '시작 실패 — 다른 지마켓 크롤이 실행 중일 수 있습니다.'));
  };
  const kwCrawl = () => {
    // 연도-버킷 모드: 해당 연도 CPC ROAS200%↑ 상품 전체를 연 단위 누적(상품당 1회)으로 수집
    if (kwYears) {
      const tot = lossData?.count || 0;
      if (!window.confirm(`${kwYears.join('·')}년 CPC ROAS200%↑ 상품(약 ${tot}개)의 키워드를 연 단위로 수집할까요?\n동시크롤 금지로 순차 실행됩니다. 상품이 많으면 수십분~수시간 걸릴 수 있어요(백그라운드 진행).`)) return;
      setKwBusy(true);
      api.post('/cpc/gmarket/keyword-crawl/', { years: kwYears, roas_min: 200 })
        .then(r => alert(r.data?.message || '연도 키워드 수집 시작'))
        .catch(e => alert(e?.response?.data?.error || '시작 실패(다른 크롤 실행 중일 수 있음)'))
        .finally(() => setKwBusy(false));
      return;
    }
    const rows = lossTargets();
    const pnos = rows.map((r: any) => String(r.product_no)).filter(Boolean);
    if (!pnos.length) { alert('대상 상품 없음'); return; }
    if (!window.confirm(`${pnos.length}개 상품의 CPC 키워드를 광고센터에서 수집할까요?\n상품당 ~5초 소요됩니다. 완료 후 새로고침하면 광고비 오른쪽에 표시됩니다.`)) return;
    setKwBusy(true);
    api.post('/cpc/gmarket/keyword-crawl/', { ym_from: ymFrom, ym_to: ymTo, roas_min: 0, product_nos: pnos })
      .then(r => alert(r.data?.message || '키워드 수집 시작'))
      .catch(e => alert(e?.response?.data?.error || '키워드 수집 시작 실패(다른 크롤 실행 중일 수 있음)'))
      .finally(() => setKwBusy(false));
  };
  const kwUpload = (file: File) => {
    const fd = new FormData();
    fd.append('file', file); fd.append('ym_from', ymFrom); fd.append('ym_to', ymTo);
    api.post('/cpc/gmarket/keyword-upload/', fd)
      .then(r => alert(r.data?.message || `엑셀 ${r.data?.count}개 상품 수집 시작`))
      .catch(e => alert(e?.response?.data?.error || '엑셀 업로드 실패'));
  };

  // 키워드 누계(중복제거) 모달 — 상품번호/판매자코드 토글 + 정렬
  const [kwDetail, setKwDetail] = useState<{ productNo: string; sellerCode?: string; keywords: any[] } | null>(null);

  const [kwCumOpen, setKwCumOpen] = useState(false);
  const [kwCumRows, setKwCumRows] = useState<any[]>([]);
  const [kwCumLoading, setKwCumLoading] = useState(false);
  const [kwCumGroupby, setKwCumGroupby] = useState<'product' | 'seller'>('product');
  const [kwCumEid, setKwCumEid] = useState('');
  const [kwCumSort, setKwCumSort] = useState<{ key: string; dir: 'asc' | 'desc' }>({ key: 'product_no', dir: 'asc' });
  const fetchKwCum = (groupby: 'product' | 'seller', eid: string) => {
    setKwCumLoading(true); setKwCumRows([]);
    api.get('/cpc/gmarket/keyword-cumulative/', { params: { groupby, eid } })
      .then(r => setKwCumRows(r.data?.rows || [])).catch(() => setKwCumRows([])).finally(() => setKwCumLoading(false));
  };
  const openKwCum = (eid = '') => { setKwCumEid(eid); setKwCumGroupby('product'); setKwCumSort({ key: 'product_no', dir: 'asc' }); setKwCumOpen(true); fetchKwCum('product', eid); };
  const kwCumSortClick = (k: string) => setKwCumSort(s => s.key === k ? { key: k, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key: k, dir: (k === 'product_no' || k === 'seller_code' || k === 'keyword') ? 'asc' : 'desc' });
  const kwCumArrow = (k: string) => (kwCumSort.key === k ? (kwCumSort.dir === 'asc' ? ' ▲' : ' ▼') : '');
  const kwCumSorted = (() => {
    const rows = [...kwCumRows];
    const { key, dir } = kwCumSort;
    const txt = (key === 'product_no' || key === 'seller_code');
    // 기본(상품번호 정렬)일 때 상품번호→판매자코드 다단계
    if (key === 'product_no') {
      rows.sort((a, b) => (dir === 'asc' ? 1 : -1) * (String(a.product_no).localeCompare(String(b.product_no)) || String(a.seller_code).localeCompare(String(b.seller_code))));
    } else {
      rows.sort((a, b) => txt
        ? (dir === 'asc' ? 1 : -1) * String(a[key] || '').localeCompare(String(b[key] || ''))
        : (dir === 'asc' ? 1 : -1) * ((Number(a[key]) || 0) - (Number(b[key]) || 0)));
    }
    return rows;
  })();
  const kwCumDisp: any[] = lossKwExpand
    ? kwCumSorted.flatMap((r: any) => {
        const seen = new Set<string>();
        const kws = (r.keywords || []).filter((k: any) => k.keyword && !seen.has(k.keyword) && seen.add(k.keyword));
        return kws.length ? kws.map((k: any, ki: number) => ({ r, k, first: ki === 0 })) : [{ r, k: null, first: true }];
      })
    : kwCumSorted.map((r: any) => ({ r, k: undefined, first: true }));
  const kwCumExcel = () => {
    const rows = kwCumSorted;
    if (!rows.length) { alert('다운로드할 키워드가 없습니다'); return; }
    // 키워드별 한 줄씩 펼침 — 키워드 1개당 1행(키워드 자체 실적 + 상품 합계 반복). 키워드 없으면 빈칸 1행.
    const head = ['상품번호', '판매자코드', '키워드', '키워드ROAS%', '키워드광고비', '키워드클릭', '키워드구매금액',
                  '상품광고비', '상품구매금액', '상품ROAS%', '실매출', '실ROAS%'];
    const body = rows.flatMap((r: any) => {
      const ptail = [r.cost ?? 0, r.conv_amount ?? 0, (r.roas ?? 0) + '%', r.real_sales ?? 0, (r.real_roas ?? 0) + '%'];
      const seen = new Set<string>();
      const kws = (r.keywords || []).filter((k: any) => k.keyword && !seen.has(k.keyword) && seen.add(k.keyword));
      if (!kws.length) return [[r.product_no, r.seller_code, '', '', 0, 0, 0, ...ptail]];
      return kws.map((k: any) => [r.product_no, r.seller_code, k.keyword, (k.roas ?? 0) + '%',
        k.cost ?? 0, k.clicks ?? 0, k.conv_amount ?? 0, ...ptail]);
    });
    const csv = '﻿' + [head, ...body].map(a => a.map((c: any) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a'); a.href = url;
    a.download = `지마켓_키워드누계_${kwCumGroupby === 'seller' ? '판매자코드' : '상품번호'}_${kwCumEid || '전체'}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  // 집중대상(실매출·고ROAS) 모달 — 전체/상세 공용, 엑셀·키워드수집
  const [focusOpen, setFocusOpen] = useState(false);
  const [focusRows, setFocusRows] = useState<any[]>([]);
  const [focusLoading, setFocusLoading] = useState(false);
  const [focusMode, setFocusMode] = useState<'focus' | 'hidden'>('focus');
  const [focusEid, setFocusEid] = useState('');
  const [focusBusy, setFocusBusy] = useState(false);
  const [focusSort, setFocusSort] = useState<{ key: string; dir: 'asc' | 'desc' }>({ key: 'real_sales', dir: 'desc' });
  const [focusAd, setFocusAd] = useState<'' | 'cpc' | 'ai'>('cpc');  // 광고유형: ''=전체 / cpc(기본) / ai
  const fetchFocus = (mode: 'focus' | 'hidden', eid: string, ad: '' | 'cpc' | 'ai' = focusAd) => {
    setFocusLoading(true); setFocusRows([]);
    api.get('/cpc/gmarket/focus-targets/', { params: { mode, eid, ad_type: ad } })
      .then(r => setFocusRows(r.data?.rows || [])).catch(() => setFocusRows([])).finally(() => setFocusLoading(false));
  };
  const setFocusAdAnd = (ad: '' | 'cpc' | 'ai') => { setFocusAd(ad); fetchFocus(focusMode, focusEid, ad); };
  const openFocus = (eid = '') => { setFocusEid(eid); setFocusMode('focus'); setFocusSort({ key: 'real_sales', dir: 'desc' }); setFocusOpen(true); fetchFocus('focus', eid); };
  const focusSortClick = (k: string) => setFocusSort(s => s.key === k ? { key: k, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key: k, dir: (k === 'product_no' || k === 'seller_code' || k === 'login_id' || k === 'product_name') ? 'asc' : 'desc' });
  const focusArrow = (k: string) => (focusSort.key === k ? (focusSort.dir === 'asc' ? ' ▲' : ' ▼') : '');
  const focusSorted = (() => {
    const rows = [...focusRows]; const { key, dir } = focusSort;
    const txt = (key === 'product_no' || key === 'seller_code' || key === 'login_id' || key === 'product_name');
    rows.sort((a, b) => txt
      ? (dir === 'asc' ? 1 : -1) * String(a[key] || '').localeCompare(String(b[key] || ''))
      : (dir === 'asc' ? 1 : -1) * ((Number(a[key]) || 0) - (Number(b[key]) || 0)));
    return rows;
  })();
  const focusDisp: any[] = lossKwExpand
    ? focusSorted.flatMap((r: any) => {
        const seen = new Set<string>();
        const kws = (r.keywords || []).filter((k: any) => k.keyword && !seen.has(k.keyword) && seen.add(k.keyword));
        return kws.length ? kws.map((k: any, ki: number) => ({ r, k, first: ki === 0 })) : [{ r, k: null, first: true }];
      })
    : focusSorted.map((r: any) => ({ r, k: undefined, first: true }));
  const focusExcel = () => {
    const rows = focusSorted; if (!rows.length) { alert('대상 없음'); return; }
    const head = ['상품번호', '계정', '판매자코드', '상품명', '광고비', '광고전환ROAS%', '실매출', '실ROAS%', '클릭', '키워드'];
    // 키워드 1개당 1행(상품정보 반복), 키워드 없으면 빈칸 1행
    const body = rows.flatMap((r: any) => {
      const b = [r.product_no, r.login_id, r.seller_code, r.product_name, r.cost, r.conv_roas, r.real_sales, r.real_roas, r.clicks];
      const seen = new Set<string>();
      const kws = (r.keywords || []).filter((k: any) => k.keyword && !seen.has(k.keyword) && seen.add(k.keyword));
      return kws.length ? kws.map((k: any) => [...b, k.keyword]) : [[...b, '']];
    });
    const csv = '﻿' + [head, ...body].map(a => a.map((c: any) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a'); a.href = url; a.download = `지마켓_집중대상_${focusMode}_${focusEid || '전체'}.csv`; a.click(); URL.revokeObjectURL(url);
  };
  const focusKwCrawl = () => {
    const pnos = focusSorted.map((r: any) => String(r.product_no)).filter(Boolean);
    if (!pnos.length) { alert('대상 상품 없음'); return; }
    if (!window.confirm(`집중대상 ${pnos.length}개 상품의 CPC 키워드를 수집할까요?\n상품당 ~5초 소요. 완료 후 새로고침하면 키워드 누계에 반영됩니다.`)) return;
    setFocusBusy(true);
    api.post('/cpc/gmarket/keyword-crawl/', { ym_from: ymFrom, ym_to: ymTo, roas_min: 0, product_nos: pnos })
      .then(r => alert(r.data?.message || '키워드 수집 시작'))
      .catch(e => alert(e?.response?.data?.error || '키워드 수집 시작 실패(다른 크롤 실행중일 수 있음)'))
      .finally(() => setFocusBusy(false));
  };

  // 1년(12개월) 초과 방지 — from을 to-11개월로 당김
  const clampYear = (f: string, t: string): [string, string] => {
    if (f > t) [f, t] = [t, f];
    if (f < addMonths(t, -23)) f = addMonths(t, -23);
    return [f, t];
  };
  const applyPMode = (m: PMode) => {
    setPmode(m);
    if (m === 'month') { setYmFrom(curYM); setYmTo(curYM); }
    else if (m === 'last') { const p = addMonths(curYM, -1); setYmFrom(p); setYmTo(p); }
    else if (m === 'year') { setYmFrom(`${now.getFullYear()}-01`); setYmTo(curYM); }
  };
  const periodLabel = ymFrom === ymTo ? ymFrom : `${ymFrom} ~ ${ymTo}`;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/cpc/gmarket/roas-accounts/', { params: { ym_from: ymFrom, ym_to: ymTo } });
      setAccts(data.accounts || []);
      setTotals({ ...ZERO_TOTALS, ...(data.totals || {}) });
    } finally { setLoading(false); }
  }, [ymFrom, ymTo]);

  useEffect(() => { load(); }, [load]);

  const openDetail = async (eid: string, name: string) => {
    setDetailEid(eid); setDetailName(name); setTab('cpc'); setCpc(null); setAi(null); setDLoading(true);
    try {
      const { data } = await api.get('/cpc/gmarket/product-roas/', { params: { ym_from: ymFrom, ym_to: ymTo, eid } });
      setCpc(data.cpc); setAi(data.ai);
    } finally { setDLoading(false); }
  };

  // 키워드 수집 실시간 반영 — 백그라운드 수집이 끝나면 열린 모달(적자/ROAS200/상세)을 자동 재조회(새로고침 불필요)
  const refetchOpenRef = useRef<() => void>(() => {});
  refetchOpenRef.current = () => {
    if (lossOpen) fetchLoss(lossMode, lossEid);
    if (detailEid) openDetail(detailEid, detailName);
  };
  const wasKwRunningRef = useRef(false);
  useEffect(() => {
    const t = setInterval(() => {
      api.get('/cpc/gmarket/keyword-status/').then(r => {
        const running = !!r.data?.running;
        setKwRunning(running);
        if (wasKwRunningRef.current && !running) refetchOpenRef.current();  // 수집 완료 순간 자동 반영
        wasKwRunningRef.current = running;
      }).catch(() => {});
    }, 5000);
    return () => clearInterval(t);
  }, []);

  const detailPack = tab === 'cpc' ? cpc : ai;
  const detailRows = [...(detailPack?.rows || [])].sort((a, b) => {
    const va = a[dSortKey], vb = b[dSortKey];
    const c = typeof va === 'string' || typeof vb === 'string'
      ? String(va).localeCompare(String(vb))
      : Number(va || 0) - Number(vb || 0);
    return dSortDir === 'asc' ? c : -c;
  });
  // 상세 모달 표시행 — 키워드 펼침 ON이면 키워드 1개당 1행(상품정보 반복, 연속행은 흐리게)
  const detailDisp: any[] = lossKwExpand
    ? detailRows.flatMap((r: any) => {
        const seen = new Set<string>();
        const kws = (r.keywords || []).filter((k: any) => k.keyword && !seen.has(k.keyword) && seen.add(k.keyword));
        return kws.length
          ? kws.map((k: any, ki: number) => ({ r, k, first: ki === 0 }))
          : [{ r, k: null, first: true }];
      })
    : detailRows.map((r: any) => ({ r, k: undefined, first: true }));
  // 상세(계정) 모달용 — 그 계정 한정 적자/ROAS200 모달, 엑셀 다운로드, 키워드 수집
  const openLossEid = (mode: LMode, eid: string) => { setKwYears(null); setLossMode(mode); setLossOpen(true); fetchLoss(mode, eid); };
  const detailExcel = () => {
    const rows = detailRows;
    if (!rows.length) { alert('대상 없음'); return; }
    const head = ['상품번호', '판매자코드', tab === 'ai' ? '그룹명' : '사이트', '노출', '클릭', '광고비', '구매수', '구매금액(광고전환)', 'ROAS', '실매출', '실ROAS', '비고', '키워드', '키워드ROAS%'];
    // 키워드별 한 줄씩 펼침 — 키워드 N개면 N행(상품정보 반복), 없으면 키워드 빈칸 1행
    const body = rows.flatMap((r: any) => {
      const base = [r.product_no, r.seller_code, tab === 'ai' ? r.group_name : (r.site === 'A' ? '옥션' : 'G마켓'),
        r.impressions, r.clicks, r.cost, r.orders, r.conv_amount, r.roas + '%', r.real_sales, r.real_roas + '%', r.status];
      const seen = new Set<string>();
      const kws = (r.keywords || []).filter((k: any) => k.keyword && !seen.has(k.keyword) && seen.add(k.keyword));
      if (!kws.length) return [[...base, '', '']];
      return kws.map((k: any) => [...base, k.keyword, Math.round(k.roas || 0) + '%']);
    });
    const csv = '﻿' + [head, ...body].map(a => a.map((c: any) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a'); a.href = url; a.download = `지마켓_${detailEid}_${tab}_상품ROAS_${ymFrom}_${ymTo}.csv`; a.click();
    URL.revokeObjectURL(url);
  };
  const detailKwCrawl = () => {
    // 키워드 수집은 ROAS≥200% 상품만 대상(고성과 키워드 추출 용도)
    const pnos = detailRows.filter((r: any) => (r.roas || 0) >= 200).map((r: any) => String(r.product_no)).filter(Boolean);
    if (!pnos.length) { alert('ROAS≥200% 상품이 없습니다 (키워드 수집 대상 없음)'); return; }
    if (!window.confirm(`${detailName} 계정 ROAS≥200% 상품 ${pnos.length}개의 CPC 키워드를 수집할까요?\n상품당 ~5초 소요됩니다. 완료 후 새로고침하면 표시됩니다.`)) return;
    setKwBusy(true);
    api.post('/cpc/gmarket/keyword-crawl/', { ym_from: ymFrom, ym_to: ymTo, roas_min: 200, product_nos: pnos })
      .then(r => alert(r.data?.message || '키워드 수집 시작'))
      .catch(e => alert(e?.response?.data?.error || '키워드 수집 시작 실패(다른 크롤 실행 중일 수 있음)'))
      .finally(() => setKwBusy(false));
  };
  const dArrow = (k: keyof ProdRow) => (dSortKey === k ? (dSortDir === 'asc' ? ' ▲' : ' ▼') : '');
  const DTh = ({ k, label, align = 'right' }: { k: keyof ProdRow; label: string; align?: 'left' | 'right' | 'center' }) => {
    const a = align === 'left' ? 'text-left' : align === 'center' ? 'text-center' : 'text-right';
    return <th className={`px-2 py-2 ${a} cursor-pointer select-none hover:bg-[#eaeaea]`} onClick={() => dSortBy(k)}>{label}{dArrow(k)}</th>;
  };

  return (
    <div className="p-4 space-y-3">
      {/* 헤더 + 기간 + 전체관리 */}
      <div className="flex items-center gap-2 flex-wrap">
        <h2 className="text-lg font-bold text-[#222]">지마켓/옥션 상품 ROAS</h2>
        {kwRunning && <span className="px-2 py-1 text-[11px] font-semibold bg-[#4f46e5] text-white rounded animate-pulse">🔑 키워드 수집중… 완료 시 자동 반영</span>}
        {([['month', '이번달'], ['last', '지난달'], ['year', '년간'], ['range', '기간별']] as [PMode, string][]).map(([m, lbl]) => (
          <button key={m} onClick={() => applyPMode(m)}
            className={`px-2.5 py-1 rounded text-[12px] font-semibold ${pmode === m ? 'bg-[#1d4ed8] text-white' : 'bg-white border text-[#555]'}`}>{lbl}</button>
        ))}
        <input type="month" value={ymFrom} max={curYM}
          onChange={e => { const [f, t] = clampYear(e.target.value, ymTo); setYmFrom(f); setYmTo(t); setPmode('range'); }}
          className="border rounded px-2 py-1 text-sm" />
        <span className="text-[#888]">~</span>
        <input type="month" value={ymTo} max={curYM}
          onChange={e => { const [f, t] = clampYear(ymFrom, e.target.value); setYmFrom(f); setYmTo(t); setPmode('range'); }}
          className="border rounded px-2 py-1 text-sm" />
        <button onClick={load} className="px-2.5 py-1 text-[12px] font-semibold bg-[#2563eb] text-white rounded hover:bg-[#1d4ed8]">새로고침</button>
        <span className="text-[11px] text-[#999]">{periodLabel}</span>
        <button onClick={() => openLoss('high')} title="ROAS≥200% 상품 — 목록·정렬·선택·복사·엑셀" className="ml-auto px-2.5 py-1 text-[12px] font-semibold bg-[#7c3aed] text-white rounded hover:bg-[#6429c4]">전체 ROAS200%↑ 상품 📋</button>
        <button onClick={() => openLoss('loss')} title="ROAS≤100 · 광고비≥2천 · 클릭≥10 — 목록·정렬·선택·복사·삭제완료" className="px-2.5 py-1 text-[12px] font-semibold bg-[#c2410c] text-white rounded hover:bg-[#9a3412]">전체 적자상품 📋</button>
        <button onClick={() => openLoss('all')} title="광고비 발생 상품 전체 — 목록·정렬·선택·복사·엑셀" className="px-2.5 py-1 text-[12px] font-semibold bg-[#1d7a46] text-white rounded hover:bg-[#155c34]">전체 상품ROAS 📋</button>
        <button onClick={() => openKwCum('')} title="수집 키워드 누계(중복제거) — 상품번호/판매자코드별, 정렬가능" className="px-2.5 py-1 text-[12px] font-semibold bg-[#4f46e5] text-white rounded hover:bg-[#4338ca]">🔑 키워드 누계 📋</button>
        <button onClick={() => openFocus('')} title="집중대상 — 실매출·고ROAS 상위 + 숨은기회(잘팔리는데 광고적음). 엑셀·키워드수집" className="px-2.5 py-1 text-[12px] font-semibold bg-[#c2410c] text-white rounded hover:bg-[#9a3412]">🎯 집중대상 📋</button>
      </div>

      {/* 합계 카드 — CPC ROAS / AI ROAS / 합계 ROAS 각각 별도 */}
      <div className="flex gap-3 flex-wrap">
        <Card label="CPC 광고비" value={formatKRW(totals.cpc_cost)} sub={`매출 ${formatKRW(totals.cpc_conv)}`} />
        <Card label="CPC ROAS" value={`${totals.cpc_roas}%`} color={roasColor(totals.cpc_roas)} />
        <Card label="AI 광고비" value={formatKRW(totals.ai_cost)} sub={`매출 ${formatKRW(totals.ai_conv)}`} />
        <Card label="AI ROAS" value={`${totals.ai_roas}%`} color={roasColor(totals.ai_roas)} />
        <Card label="합계 광고비" value={formatKRW(totals.cost)} sub={`광고전환 ${formatKRW(totals.conv_amount)}`} />
        <Card label="합계 ROAS(광고전환)" value={`${totals.roas}%`} color={roasColor(totals.roas)} />
        <Card label="실매출 ROAS" value={`${totals.real_roas}%`} sub={`실매출 ${formatKRW(totals.real_sales)}`} color={roasColor(totals.real_roas)} />
      </div>
      <p className="text-[11px] text-[#999]">
        ※ 상품별 <b>광고비(총비용)는 참고용</b>입니다(신뢰값은 광고센터 스냅샷). · <b>광고전환 ROAS</b>=광고리포트 전환매출 기준 · <b>실매출 ROAS</b>=매출자료 상품코드 매칭(전역) 기준. · 광고리포트는 월 단위 누적(일별 없음, 최대 2년 집계).
      </p>

      {/* 계정 요약 테이블 */}
      <div className="bg-white rounded shadow overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead className="bg-[#f5f6f8] text-[#555] select-none">
            <tr>
              <th onClick={() => acctSortClick('login_id')} className="px-2 py-2 text-left cursor-pointer hover:text-[#1d4ed8]">계정(상호){acctArrow('login_id')}</th>
              <th onClick={() => acctSortClick('cpc_cost')} className="px-2 py-2 text-right cursor-pointer hover:text-[#1d4ed8]">CPC 광고비{acctArrow('cpc_cost')}</th>
              <th onClick={() => acctSortClick('cpc_roas')} className="px-2 py-2 text-right cursor-pointer hover:text-[#1d4ed8]">CPC ROAS{acctArrow('cpc_roas')}</th>
              <th onClick={() => acctSortClick('ai_cost')} className="px-2 py-2 text-right cursor-pointer hover:text-[#1d4ed8]">AI 광고비{acctArrow('ai_cost')}</th>
              <th onClick={() => acctSortClick('ai_roas')} className="px-2 py-2 text-right cursor-pointer hover:text-[#1d4ed8]">AI ROAS{acctArrow('ai_roas')}</th>
              <th onClick={() => acctSortClick('total_cost')} className="px-2 py-2 text-right cursor-pointer hover:text-[#1d4ed8]">합계 광고비{acctArrow('total_cost')}</th>
              <th onClick={() => acctSortClick('roas')} className="px-2 py-2 text-right cursor-pointer hover:text-[#1d4ed8]">합계 ROAS{acctArrow('roas')}</th>
              <th onClick={() => acctSortClick('real_sales')} className="px-2 py-2 text-right cursor-pointer hover:text-[#1d4ed8]">실매출{acctArrow('real_sales')}</th>
              <th onClick={() => acctSortClick('real_roas')} className="px-2 py-2 text-right cursor-pointer hover:text-[#1d4ed8]">실 ROAS{acctArrow('real_roas')}</th>
              <th onClick={() => acctSortClick('cpc_products')} className="px-2 py-2 text-right cursor-pointer hover:text-[#1d4ed8]">상품수(CPC/AI){acctArrow('cpc_products')}</th>
              <th className="px-2 py-2 text-center">상세</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={11} className="text-center py-6 text-[#888]">불러오는 중…</td></tr>}
            {!loading && accts.length === 0 && <tr><td colSpan={11} className="text-center py-6 text-[#888]">데이터가 없습니다. (크롤 후 표시)</td></tr>}
            {sortedAccts.map(a => (
              <tr key={a.login_id} onClick={() => openDetail(a.login_id, a.seller_name)}
                className="border-t hover:bg-[#f0f7ff] cursor-pointer">
                <td className="px-2 py-1.5 font-semibold text-[#1d4ed8]">{a.seller_name} <span className="text-[#999] font-normal">({a.login_id})</span></td>
                <td className="px-2 py-1.5 text-right">{formatKRW(a.cpc_cost)}</td>
                <td className={`px-2 py-1.5 text-right ${roasColor(a.cpc_roas)}`}>{a.cpc_roas}%</td>
                <td className="px-2 py-1.5 text-right">{formatKRW(a.ai_cost)}</td>
                <td className={`px-2 py-1.5 text-right ${roasColor(a.ai_roas)}`}>{a.ai_roas}%</td>
                <td className="px-2 py-1.5 text-right font-semibold">{formatKRW(a.total_cost)}</td>
                <td className={`px-2 py-1.5 text-right ${roasColor(a.roas)}`}>{a.roas}%</td>
                <td className="px-2 py-1.5 text-right text-[#1d7a46]">{formatKRW(a.real_sales)}</td>
                <td className={`px-2 py-1.5 text-right ${roasColor(a.real_roas)}`}>{a.real_roas}%</td>
                <td className="px-2 py-1.5 text-right text-[#666]">{a.cpc_products}/{a.ai_products}</td>
                <td className="px-2 py-1.5 text-center">
                  <button onClick={e => { e.stopPropagation(); openDetail(a.login_id, a.seller_name); }}
                    className="px-2 py-0.5 text-[12px] font-semibold bg-[#2563eb] text-white rounded hover:bg-[#1d4ed8]">상세</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 상세 모달 — CPC/AI 구분 */}
      {detailEid && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setDetailEid(null)}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[88vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3 px-4 py-3 border-b">
              <span className="font-bold text-[#222]">{detailName} <span className="text-[#999] text-sm font-normal">({detailEid})</span> · {periodLabel} 상품 ROAS</span>
              <div className="ml-auto flex items-center gap-1 flex-wrap justify-end">
                <button onClick={() => openLossEid('high', detailEid!)} title="이 계정 ROAS≥200% 상품 — 목록·복사·엑셀·키워드" className="px-2 py-1 text-[11px] font-semibold bg-[#7c3aed] text-white rounded hover:bg-[#6429c4]">ROAS200%↑</button>
                <button onClick={() => openLossEid('loss', detailEid!)} title="이 계정 적자상품 — ROAS≤100·광고비≥2천·클릭≥10" className="px-2 py-1 text-[11px] font-semibold bg-[#c2410c] text-white rounded hover:bg-[#9a3412]">적자상품</button>
                <button onClick={detailExcel} title="현재 탭 상품을 엑셀(CSV)로 다운로드" className="px-2 py-1 text-[11px] font-semibold bg-[#1d7a46] text-white rounded hover:bg-[#155c34]">⬇ 엑셀</button>
                <button onClick={() => bulkRegCsv(detailRows, `지마켓_대량등록_${detailEid}_${tab}.csv`)}
                  title="키워드 대량등록 양식(판매자ID·사이트·광고그룹명·키워드명·상품번호·희망클릭비용=평균단가×91%)"
                  className="px-2 py-1 text-[11px] font-semibold bg-[#b45309] text-white rounded hover:bg-[#92400e]">⬇ 대량등록양식</button>
                <button onClick={detailKwCrawl} disabled={kwBusy} title="이 계정 상품들의 CPC 키워드 수집(상품당 ~5초)" className="px-2 py-1 text-[11px] font-semibold bg-[#4f46e5] text-white rounded hover:bg-[#4338ca] disabled:opacity-50">🔑 키워드</button>
                <button onClick={() => openFocus(detailEid!)} title="이 계정 집중대상 — 실매출·고ROAS + 숨은기회" className="px-2 py-1 text-[11px] font-semibold bg-[#c2410c] text-white rounded hover:bg-[#9a3412]">🎯 집중대상</button>
                <span className="w-px h-4 bg-gray-300 mx-1" />
                <button onClick={() => setTab('cpc')} className={`px-3 py-1 text-sm rounded ${tab === 'cpc' ? 'bg-[#1d7a46] text-white' : 'bg-gray-100'}`}>CPC {cpc ? `(${cpc.products})` : ''}</button>
                <button onClick={() => setTab('ai')} className={`px-3 py-1 text-sm rounded ${tab === 'ai' ? 'bg-[#7c3aed] text-white' : 'bg-gray-100'}`}>AI매출업 {ai ? `(${ai.products})` : ''}</button>
                <button onClick={() => setDetailEid(null)} className="px-2 py-1 text-sm text-[#888]">✕</button>
              </div>
            </div>
            {detailPack && (
              <div className="px-4 py-2 text-[12px] text-[#555] bg-[#fafbfc] border-b flex gap-4">
                <span>광고비 <b>{formatKRW(detailPack.totals.cost)}</b></span>
                <span>구매금액 <b>{formatKRW(detailPack.totals.conv_amount)}</b></span>
                <span>클릭 <b>{detailPack.totals.clicks.toLocaleString()}</b></span>
                <span>ROAS <b className={roasColor(detailPack.totals.roas)}>{detailPack.totals.roas}%</b></span>
              </div>
            )}
            <div className="overflow-auto">
              {dLoading && <div className="text-center py-8 text-[#888]">불러오는 중…</div>}
              {!dLoading && detailPack && (
                <table className="w-full text-[12px]">
                  <thead className="bg-[#f5f6f8] text-[#555] sticky top-0">
                    <tr>
                      <DTh k="product_no" label="상품번호" align="left" />
                      <DTh k="seller_code" label="판매자코드" align="left" />
                      {tab === 'ai' && <DTh k="group_name" label="그룹명" align="left" />}
                      {tab === 'cpc' && <DTh k="site" label="사이트" align="center" />}
                      <DTh k="impressions" label="노출" />
                      <DTh k="clicks" label="클릭" />
                      <DTh k="cost" label="광고비" />
                      <DTh k="orders" label="구매수" />
                      <DTh k="conv_amount" label="구매금액(광고전환)" />
                      <DTh k="roas" label="ROAS" />
                      <DTh k="real_sales" label="실매출" />
                      <DTh k="real_roas" label="실ROAS" />
                      <DTh k="status" label="비고(상태)" align="center" />
                      <th className="px-2 py-2 text-left">키워드<span className="text-[10px] text-[#999] font-normal">(수집)</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {detailDisp.length === 0 && <tr><td colSpan={14} className="text-center py-6 text-[#888]">데이터 없음</td></tr>}
                    {detailDisp.map((d: any, i: number) => {
                      const r = d.r; const k = d.k; const cont = !d.first;
                      const dim = cont ? 'opacity-40' : '';
                      return (
                      <tr key={r.product_no + '_' + (k ? k.keyword : '') + '_' + i} className={`border-t hover:bg-[#f7f7f7] ${cont ? 'border-t-0' : ''}`}>
                        <td className={`px-2 py-1 font-mono ${dim}`}>{r.product_no}</td>
                        <td className={`px-2 py-1 font-mono text-[#666] ${dim}`}>{r.seller_code || '-'}</td>
                        {tab === 'ai' && <td className={`px-2 py-1 truncate max-w-[180px] ${dim}`}>{r.group_name}</td>}
                        {tab === 'cpc' && <td className={`px-2 py-1 text-center ${dim}`}>{r.site === 'A' ? '옥션' : 'G마켓'}</td>}
                        <td className={`px-2 py-1 text-right ${dim}`}>{r.impressions.toLocaleString()}</td>
                        <td className={`px-2 py-1 text-right ${dim}`}>{r.clicks.toLocaleString()}</td>
                        <td className={`px-2 py-1 text-right ${dim}`}>{formatKRW(r.cost)}</td>
                        <td className={`px-2 py-1 text-right ${dim}`}>{r.orders}</td>
                        <td className={`px-2 py-1 text-right ${dim}`}>{formatKRW(r.conv_amount)}</td>
                        <td className={`px-2 py-1 text-right ${roasColor(r.roas)} ${dim}`}>{r.roas}%</td>
                        <td className={`px-2 py-1 text-right text-[#1d7a46] ${dim}`}>{formatKRW(r.real_sales)}</td>
                        <td className={`px-2 py-1 text-right ${roasColor(r.real_roas)} ${dim}`}>{r.real_roas}%</td>
                        <td className={`px-2 py-1 text-center ${dim}`}><StatusCell r={r} /></td>
                        <td className="px-2 py-1">
                          {k === undefined ? (
                            (r.keywords && r.keywords.length) ? (
                              <div className="flex flex-wrap gap-1 max-w-[300px] cursor-pointer" title="클릭 — 키워드별 상세"
                                onClick={() => setKwDetail({ productNo: r.product_no, sellerCode: r.seller_code, keywords: r.keywords })}>
                                {r.keywords.slice(0, 8).map((kk: any, j: number) => (
                                  <span key={j} className={`px-1 py-0.5 rounded text-[10px] ${kk.roas >= 200 ? 'bg-[#ede9fe] text-[#6429c4] font-semibold' : 'bg-gray-100 text-[#666]'}`}>
                                    {kk.keyword}
                                  </span>
                                ))}
                                {r.keywords.length > 8 && <span className="text-[10px] text-[#6429c4] font-semibold">+{r.keywords.length - 8}</span>}
                              </div>
                            ) : <span className="text-[#ccc] text-[11px]">-</span>
                          ) : k ? (
                            <span className="text-[#333]">{k.keyword}</span>
                          ) : <span className="text-[#ccc] text-[11px]">-</span>}
                        </td>
                      </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 전체 적자상품 모달 (11번가식) */}
      {lossOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setLossOpen(false)}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[88vh] overflow-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-5 py-3 border-b border-[#eee] sticky top-0 bg-white flex-wrap">
              <h3 className="text-[13px] font-bold text-[#333]">{LMODES[lossMode].title}</h3>
              <span className="text-[11px] text-[#888]">{LMODES[lossMode].crit}</span>
              {lossMode !== 'keyword' && (
                <span className="inline-flex rounded overflow-hidden border border-[#d0d0d0]" title="광고유형: 전체=CPC+AI 합산 / CPC만 / AI매출업만">
                  {([['', '전체'], ['cpc', 'CPC'], ['ai', 'AI매출업']] as ['' | 'cpc' | 'ai', string][]).map(([v, lbl]) => (
                    <button key={v} onClick={() => setLossAdAnd(v)}
                      className={`px-2 py-0.5 text-[11px] font-semibold ${lossAd === v ? 'bg-[#7c3aed] text-white' : 'bg-white text-[#555] hover:bg-[#f0f0f0]'}`}>{lbl}</button>
                  ))}
                </span>
              )}
              {lossData && <span className="text-[12px] text-[#c2410c] font-semibold">{lossData.count.toLocaleString()}개{lossData.capped ? '+' : ''}</span>}
              {lossData && <span className="text-[11px] text-[#999]">{lossData.ym_from}~{lossData.ym_to}</span>}
              {lossSel.size > 0 && <span className="text-[11px] text-[#1e6fd9] font-semibold">선택 {lossSel.size}</span>}
              <button onClick={copySellerCodes} className="ml-auto px-2.5 py-1 text-[12px] font-semibold bg-[#1e6fd9] text-white rounded hover:bg-[#1857ad]">📋 판매자코드 복사</button>
              <button onClick={copyProductNos} title="상품번호(숫자만) 복사" className="px-2.5 py-1 text-[12px] font-semibold bg-[#0d9488] text-white rounded hover:bg-[#0f766e]">📋 상품번호코드 복사</button>
              <button onClick={lossExcel} className="px-2.5 py-1 text-[12px] font-semibold bg-[#1d7a46] text-white rounded hover:bg-[#155c34]">⬇ 엑셀</button>
              <button onClick={() => bulkRegCsv(lossTargets(), `지마켓_대량등록_${lossData?.ym_from || ''}_${lossData?.ym_to || ''}.csv`)}
                title="키워드 대량등록 양식(판매자ID·사이트·광고그룹명·키워드명·상품번호·희망클릭비용). 선택 없으면 전체, 희망클릭비용=평균단가×91%"
                className="px-2.5 py-1 text-[12px] font-semibold bg-[#b45309] text-white rounded hover:bg-[#92400e]">⬇ 대량등록양식</button>
              <button onClick={() => setLossKwExpand(v => !v)} title="키워드를 한 줄씩 펼치기/접기"
                className={`px-2.5 py-1 text-[12px] font-semibold rounded ${lossKwExpand ? 'bg-[#4338ca] text-white' : 'bg-gray-100 text-[#555]'}`}>
                {lossKwExpand ? '키워드 펼침 ON' : '키워드 펼침 OFF'}</button>
              {/* 키워드 수집은 적자상품엔 불필요 — loss 모드에선 숨김(high/all 모드에서만 노출) */}
              {lossMode !== 'loss' && (<>
                <button onClick={kwCrawl} disabled={kwBusy} title="선택(없으면 전체) 상품의 CPC 키워드를 광고센터에서 수집 — 상품당 ~5초. 완료 후 새로고침" className="px-2.5 py-1 text-[12px] font-semibold bg-[#4f46e5] text-white rounded hover:bg-[#4338ca] disabled:opacity-50">🔑 키워드 수집</button>
                <label title="엑셀(첫 열=상품번호) 업로드 → 키워드 수집" className="px-2.5 py-1 text-[12px] font-semibold bg-[#0d9488] text-white rounded hover:bg-[#0f766e] cursor-pointer">📤 엑셀업로드
                  <input type="file" accept=".xlsx,.xls" hidden onChange={e => { const f = e.target.files?.[0]; if (f) kwUpload(f); (e.target as HTMLInputElement).value = ''; }} />
                </label>
              </>)}
              {LMODES[lossMode].del && <button onClick={markLossDeleted} title="지마켓에서 직접 삭제 완료한 상품을 '삭제완료'로 표시" className="px-2.5 py-1 text-[12px] font-bold bg-[#dc2626] text-white rounded hover:bg-[#b91c1c]">✓ 삭제완료 처리</button>}
              {LMODES[lossMode].del && <button onClick={validateGmktDelete} title="셀러오피스 접속·셀렉터를 1상품으로 검증(실제 삭제 안 함)" className="px-2.5 py-1 text-[12px] font-semibold bg-[#0369a1] text-white rounded hover:bg-[#075985]">🔎 삭제 검증</button>}
              {LMODES[lossMode].del && <button onClick={deleteGmktLoss} title="⚠️ 위험: 셀러오피스에서 실제 영구 삭제(검증 후 진행)" className="px-2.5 py-1 text-[12px] font-bold bg-[#7f1d1d] text-white rounded hover:bg-[#601515]">🗑 실제 삭제</button>}
              <button onClick={() => setLossOpen(false)} className="text-[#999] hover:text-[#333] text-[13px]">✕</button>
            </div>
            <div className="px-5 py-2 border-b border-[#f0f0f0] bg-[#fafafa] text-[11px] flex flex-wrap gap-x-3">
              <span className="text-[#888] font-semibold">비고:</span>
              <span className="text-[#1e6fd9] font-bold">🔵 삭제완료</span>
              <span className="text-[#dc2626] font-semibold">🔴 삭제/판매불가</span>
              <span className="text-[#e08000]">🟠 판매중지/품절</span>
              <span className="text-[#00a651]">🟢 판매중</span>
              <span className="text-[#999]">※ 판매상태 = 마지막 크롤링한 상품번호 기준(최신 스냅샷)</span>
              <span className="text-[#999]">선택 없으면 전체 대상</span>
              <span className="text-[#1d4ed8] font-semibold ml-2">※ 구매수·구매금액·ROAS = 광고센터 기준</span>
              <span className="text-[#aaa]">실구매·실매출 = 매출자료(참고)</span>
            </div>
            <div className="p-4">
              {lossLoading && <div className="text-center text-[#888] py-8">불러오는 중…</div>}
              {!lossLoading && lossData && lossRows.length === 0 && <div className="text-center text-[#888] py-8">대상 적자상품이 없습니다.</div>}
              {!lossLoading && lossData && lossRows.length > 0 && (
                <table className="w-full text-[12px]">
                  <thead><tr className="bg-[#f7f7f7] text-[#666] border-b border-[#e0e0e0] select-none">
                    <th className="px-2 py-1.5 text-center"><input type="checkbox" checked={lossAllChecked} onChange={toggleLossAll} /></th>
                    <th className="px-2 py-1.5 text-center">번호</th>
                    <th onClick={() => lossSortClick('login_id')} className="px-2 py-1.5 text-left cursor-pointer hover:text-[#1d4ed8]">계정{lossArrow('login_id')}</th>
                    <th onClick={() => lossSortClick('product_no')} className="px-2 py-1.5 text-left cursor-pointer hover:text-[#1d4ed8]">상품번호{lossArrow('product_no')}</th>
                    <th onClick={() => lossSortClick('seller_code')} className="px-2 py-1.5 text-left cursor-pointer hover:text-[#1d4ed8]">판매자코드{lossArrow('seller_code')}</th>
                    <th onClick={() => lossSortClick('cum_sold_qty')} className="px-2 py-1.5 text-right cursor-pointer hover:text-[#1d4ed8]" title="2025-01-01 ~ 현재 누적 판매수량(판매자코드 전역매칭, 지마켓+옥션)">누적판매<span className="text-[10px] text-[#999] font-normal">(25~)</span>{lossArrow('cum_sold_qty')}</th>
                    <th onClick={() => lossSortClick('avg_click_cost')} className="px-2 py-1.5 text-right cursor-pointer hover:text-[#1d4ed8]" title="평균단가=광고비/클릭">평균단가{lossArrow('avg_click_cost')}</th>
                    <th onClick={() => lossSortClick('cost')} className="px-2 py-1.5 text-right cursor-pointer hover:text-[#1d4ed8]">광고비{lossArrow('cost')}</th>
                    <th onClick={() => lossSortClick('kw_count')} className="px-2 py-1.5 text-left cursor-pointer hover:text-[#1d4ed8]" title="수집된 CPC 키워드(광고비순) — 클릭시 키워드 수로 정렬">키워드{lossArrow('kw_count')}</th>
                    <th onClick={() => lossSortClick('clicks')} className="px-2 py-1.5 text-right cursor-pointer hover:text-[#1d4ed8]">클릭{lossArrow('clicks')}</th>
                    <th onClick={() => lossSortClick('ad_orders')} className="px-2 py-1.5 text-right cursor-pointer hover:text-[#1d4ed8]" title="광고센터 구매수">구매수{lossArrow('ad_orders')}</th>
                    <th onClick={() => lossSortClick('conv_amount')} className="px-2 py-1.5 text-right cursor-pointer hover:text-[#1d4ed8]" title="광고센터 구매금액(광고전환)">구매금액{lossArrow('conv_amount')}</th>
                    <th onClick={() => lossSortClick('roas')} className="px-2 py-1.5 text-right cursor-pointer hover:text-[#1d4ed8]" title="광고센터 광고수익률">ROAS{lossArrow('roas')}</th>
                    <th onClick={() => lossSortClick('real_orders')} className="px-2 py-1.5 text-right cursor-pointer hover:text-[#1d4ed8]" title="매출자료 매칭 — 참고용">실구매(참고){lossArrow('real_orders')}</th>
                    <th onClick={() => lossSortClick('real_sales')} className="px-2 py-1.5 text-right cursor-pointer hover:text-[#1d4ed8]" title="매출자료 매칭 — 참고용">실매출(참고){lossArrow('real_sales')}</th>
                    <th onClick={() => lossSortClick('real_roas')} className="px-2 py-1.5 text-right cursor-pointer hover:text-[#1d4ed8]" title="실매출 효율 = 실매출÷광고비. 광고전환ROAS는 낮아도 실ROAS가 높으면 실제론 흑자(삭제 주의)">실ROAS(참고){lossArrow('real_roas')}</th>
                    <th onClick={() => lossSortClick('status')} className="px-2 py-1.5 text-center cursor-pointer hover:text-[#1d4ed8]">비고{lossArrow('status')}</th>
                  </tr></thead>
                  <tbody>
                    {lossDisp.map((d: any, i: number) => {
                      const r = d.r; const k = d.k;
                      const cont = !d.first;   // 같은 상품의 연속(키워드) 행
                      return (
                      <tr key={r.product_no + '_' + (k ? k.keyword : '') + '_' + i}
                        className={`border-b border-[#f0f0f0] hover:bg-[#fafafa] ${lossSel.has(r.product_no) ? 'bg-[#eef5ff]' : ''} ${cont ? 'border-t-0' : ''}`}>
                        <td className="px-2 py-1.5 text-center">{d.first && <input type="checkbox" checked={lossSel.has(r.product_no)} onChange={() => toggleLossSel(r.product_no)} />}</td>
                        <td className="px-2 py-1.5 text-center text-[#999]">{d.first ? d.pi + 1 : ''}</td>
                        <td className={`px-2 py-1.5 text-[#555] ${cont ? 'opacity-40' : ''}`}>{r.login_id}</td>
                        <td className={`px-2 py-1.5 font-mono ${cont ? 'opacity-40' : ''}`}><a href={gmktUrl(r)} target="_blank" rel="noreferrer" className="text-[#1d4ed8] hover:underline">{r.product_no}</a></td>
                        <td className={`px-2 py-1.5 font-mono text-[#666] ${cont ? 'opacity-40' : ''}`}>{r.seller_code || '-'}</td>
                        <td className={`px-2 py-1.5 text-right font-semibold ${(r.cum_sold_qty || 0) > 0 ? 'text-[#1d7a46]' : 'text-[#bbb]'} ${cont ? 'opacity-40' : ''}`}>{(r.cum_sold_qty || 0).toLocaleString()}</td>
                        <td className={`px-2 py-1.5 text-right text-[#555] ${cont ? 'opacity-40' : ''}`}>{formatKRW(r.clicks ? Math.round(r.cost / r.clicks) : 0)}</td>
                        <td className={`px-2 py-1.5 text-right ${cont ? 'opacity-40' : ''}`}>{formatKRW(r.cost)}</td>
                        <td className="px-2 py-1.5 text-left max-w-[280px]">
                          {k === undefined ? (
                            (r.keywords && r.keywords.length) ? (
                              <div className="flex flex-wrap gap-1 cursor-pointer" title="클릭 — 키워드별 상세"
                                onClick={() => setKwDetail({ productNo: r.product_no, sellerCode: r.seller_code, keywords: r.keywords })}>
                                {r.keywords.slice(0, 6).map((kk: any, j: number) => (
                                  <span key={j} className="px-1.5 py-0.5 bg-[#eef2ff] text-[#4338ca] rounded text-[11px] whitespace-nowrap">{kk.keyword}</span>
                                ))}
                                {r.keywords.length > 6 && <span className="text-[#4338ca] text-[11px] self-center font-semibold">+{r.keywords.length - 6}</span>}
                              </div>
                            ) : <span className="text-[#ccc]">-</span>
                          ) : k ? (
                            <span className="text-[#333]">{k.keyword}</span>
                          ) : <span className="text-[#ccc]">-</span>}
                        </td>
                        <td className={`px-2 py-1.5 text-right ${cont ? 'opacity-40' : ''}`}>{(r.clicks || 0).toLocaleString()}</td>
                        <td className={`px-2 py-1.5 text-right ${cont ? 'opacity-40' : ''}`}>{(r.ad_orders || 0).toLocaleString()}</td>
                        <td className={`px-2 py-1.5 text-right ${cont ? 'opacity-40' : ''}`}>{formatKRW(r.conv_amount)}</td>
                        <td className={`px-2 py-1.5 text-right font-semibold text-[#dc2626] ${cont ? 'opacity-40' : ''}`}>{r.roas}%</td>
                        <td className={`px-2 py-1.5 text-right font-semibold ${cont ? 'opacity-40' : ''}`}>{(r.real_orders || 0).toLocaleString()}</td>
                        <td className={`px-2 py-1.5 text-right text-[#1d7a46] ${cont ? 'opacity-40' : ''}`}>{formatKRW(r.real_sales)}</td>
                        <td className={`px-2 py-1.5 text-right font-semibold ${roasColor(r.real_roas || 0)} ${cont ? 'opacity-40' : ''}`} title={(r.real_roas || 0) > 100 ? '실매출 기준으론 흑자 — 삭제 주의' : ''}>{r.real_roas || 0}%</td>
                        <td className={`px-2 py-1.5 text-center ${cont ? 'opacity-40' : ''}`}><StatusCell r={r} /></td>
                      </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 키워드 누계(중복제거) 모달 */}
      {kwCumOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setKwCumOpen(false)}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[88vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-5 py-3 border-b border-[#eee] flex-wrap">
              <h3 className="text-[13px] font-bold text-[#333]">🔑 키워드 누계 (중복제거)</h3>
              <span className="text-[11px] text-[#888]">{kwCumEid || '전체 계정'} · 연도버킷 합산 · ROAS≥100 키워드</span>
              <span className="text-[12px] text-[#4f46e5] font-semibold">{kwCumSorted.length.toLocaleString()}행</span>
              <div className="ml-auto flex items-center gap-1">
                <button onClick={() => { setKwCumGroupby('product'); fetchKwCum('product', kwCumEid); }} className={`px-2.5 py-1 text-[12px] font-semibold rounded ${kwCumGroupby === 'product' ? 'bg-[#4f46e5] text-white' : 'bg-gray-100 text-[#555]'}`}>상품번호 기준</button>
                <button onClick={() => { setKwCumGroupby('seller'); fetchKwCum('seller', kwCumEid); }} className={`px-2.5 py-1 text-[12px] font-semibold rounded ${kwCumGroupby === 'seller' ? 'bg-[#4f46e5] text-white' : 'bg-gray-100 text-[#555]'}`}>판매자코드 기준</button>
                <button onClick={kwCumExcel} title="현재 표(키워드 누계)를 엑셀(CSV)로 다운로드" className="px-2.5 py-1 text-[12px] font-semibold bg-[#1d7a46] text-white rounded hover:bg-[#155c34]">⬇ 엑셀</button>
                <button onClick={() => setKwCumOpen(false)} className="px-2 py-1 text-sm text-[#888]">✕</button>
              </div>
            </div>
            <div className="overflow-auto">
              {kwCumLoading && <div className="text-center py-8 text-[#888]">불러오는 중…</div>}
              {!kwCumLoading && (
                <table className="w-full text-[12px]">
                  <thead className="bg-[#f5f6f8] text-[#555] sticky top-0">
                    <tr>
                      {[['product_no', '상품번호', 'left'], ['seller_code', '판매자코드', 'left'], ['keyword_count', '키워드수', 'right'],
                        ['impressions', '노출(합)', 'right'], ['clicks', '클릭(합)', 'right'], ['cost', '광고비(합)', 'right'],
                        ['avg_click_cost', '평균광고비', 'right'], ['conv_amount', '구매금액(광고센터)', 'right'], ['roas', 'ROAS', 'right'],
                        ['real_sales', '실매출', 'right'], ['real_roas', '실ROAS', 'right'],
                        ['keywords', '키워드', 'left']].map(([k, lbl, al]) => (
                        <th key={k} onClick={() => k !== 'keywords' && kwCumSortClick(k)}
                          className={`px-2 py-2 select-none ${k !== 'keywords' ? 'cursor-pointer hover:bg-[#eaeaea]' : ''} ${al === 'left' ? 'text-left' : 'text-right'}`}>{lbl}{k !== 'keywords' ? kwCumArrow(k) : ''}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {kwCumDisp.length === 0 && <tr><td colSpan={12} className="text-center py-6 text-[#888]">데이터 없음 (키워드 수집 후 표시)</td></tr>}
                    {kwCumDisp.map((d: any, i: number) => {
                      const r = d.r; const k = d.k; const cont = !d.first; const dim = cont ? 'opacity-40' : '';
                      return (
                      <tr key={r.product_no + '_' + (k ? k.keyword : '') + '_' + i} className={`border-t hover:bg-[#f7f7f7] ${cont ? 'border-t-0' : ''}`}>
                        <td className={`px-2 py-1 font-mono ${dim}`}>{r.product_no}</td>
                        <td className={`px-2 py-1 font-mono text-[#666] ${dim}`}>{r.seller_code || '-'}{r.product_count > 1 && kwCumGroupby === 'seller' && <span className="ml-1 text-[10px] text-[#4f46e5]">({r.product_count}상품)</span>}</td>
                        <td className={`px-2 py-1 text-right font-semibold ${dim}`}>{r.keyword_count}</td>
                        <td className={`px-2 py-1 text-right ${dim}`}>{(r.impressions || 0).toLocaleString()}</td>
                        <td className={`px-2 py-1 text-right ${dim}`}>{(r.clicks || 0).toLocaleString()}</td>
                        <td className={`px-2 py-1 text-right ${dim}`}>{formatKRW(r.cost || 0)}</td>
                        <td className={`px-2 py-1 text-right text-[#92400e] ${dim}`}>{formatKRW(r.avg_click_cost || 0)}</td>
                        <td className={`px-2 py-1 text-right text-[#1d7a46] ${dim}`}>{formatKRW(r.conv_amount || 0)}</td>
                        <td className={`px-2 py-1 text-right ${roasColor(r.roas)} ${dim}`}>{r.roas}%</td>
                        <td className={`px-2 py-1 text-right text-[#0369a1] ${dim}`}>{formatKRW(r.real_sales || 0)}</td>
                        <td className={`px-2 py-1 text-right ${roasColor(r.real_roas)} ${dim}`}>{r.real_roas}%</td>
                        <td className="px-2 py-1">
                          {k === undefined ? (
                            <div className="flex flex-wrap gap-1 max-w-[320px]">
                              {(r.keywords || []).slice(0, 10).map((kk: any, j: number) => (
                                <span key={j} title={`광고비 ${formatKRW(kk.cost)} · 클릭 ${kk.clicks} · ROAS ${kk.roas}%`}
                                  className={`px-1 py-0.5 rounded text-[10px] ${kk.roas >= 200 ? 'bg-[#ede9fe] text-[#6429c4] font-semibold' : 'bg-gray-100 text-[#666]'}`}>
                                  {kk.keyword}
                                </span>
                              ))}
                              {(r.keywords || []).length > 10 && <span className="text-[10px] text-[#999]">+{r.keywords.length - 10}</span>}
                            </div>
                          ) : k ? (
                            <span className="text-[#333]">{k.keyword}</span>
                          ) : <span className="text-[#ccc]">-</span>}
                        </td>
                      </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 집중대상 모달 */}
      {focusOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setFocusOpen(false)}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[88vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-5 py-3 border-b border-[#eee] flex-wrap">
              <h3 className="text-[13px] font-bold text-[#333]">🎯 집중대상</h3>
              <span className="text-[11px] text-[#888]">{focusEid || '전체 계정'} · 2026년 기준</span>
              <span className="text-[12px] text-[#c2410c] font-semibold">{focusSorted.length.toLocaleString()}개</span>
              <button onClick={() => { setFocusMode('focus'); fetchFocus('focus', focusEid); }} className={`px-2.5 py-1 text-[12px] font-semibold rounded ${focusMode === 'focus' ? 'bg-[#c2410c] text-white' : 'bg-gray-100 text-[#555]'}`}>집중대상(실매출·ROAS≥200)</button>
              <button onClick={() => { setFocusMode('hidden'); fetchFocus('hidden', focusEid); }} className={`px-2.5 py-1 text-[12px] font-semibold rounded ${focusMode === 'hidden' ? 'bg-[#c2410c] text-white' : 'bg-gray-100 text-[#555]'}`}>⭐숨은기회(잘팔리는데 광고적음)</button>
              <span className="inline-flex rounded overflow-hidden border border-[#d0d0d0]" title="광고유형: 전체=CPC+AI 합산 / CPC만 / AI매출업만">
                {([['', '전체'], ['cpc', 'CPC'], ['ai', 'AI매출업']] as ['' | 'cpc' | 'ai', string][]).map(([v, lbl]) => (
                  <button key={v} onClick={() => setFocusAdAnd(v)}
                    className={`px-2 py-0.5 text-[11px] font-semibold ${focusAd === v ? 'bg-[#7c3aed] text-white' : 'bg-white text-[#555] hover:bg-[#f0f0f0]'}`}>{lbl}</button>
                ))}
              </span>
              <div className="ml-auto flex items-center gap-1">
                <button onClick={focusExcel} className="px-2.5 py-1 text-[12px] font-semibold bg-[#1d7a46] text-white rounded hover:bg-[#155c34]">⬇ 엑셀</button>
                <button onClick={() => bulkRegCsv(focusSorted, `지마켓_대량등록_집중대상_${focusMode}_${focusEid || '전체'}.csv`)}
                  title="키워드 대량등록 양식(판매자ID·사이트·광고그룹명·키워드명·상품번호·희망클릭비용=평균단가×91%)"
                  className="px-2.5 py-1 text-[12px] font-semibold bg-[#b45309] text-white rounded hover:bg-[#92400e]">⬇ 대량등록양식</button>
                <button onClick={focusKwCrawl} disabled={focusBusy} title="집중대상 상품들의 CPC 키워드 수집(상품당 ~5초)" className="px-2.5 py-1 text-[12px] font-semibold bg-[#4f46e5] text-white rounded hover:bg-[#4338ca] disabled:opacity-50">🔑 키워드 수집</button>
                <button onClick={() => setFocusOpen(false)} className="px-2 py-1 text-sm text-[#888]">✕</button>
              </div>
            </div>
            <div className="px-5 py-1.5 text-[11px] text-[#777] border-b border-[#f0f0f0] bg-[#fafafa]">
              {focusMode === 'hidden' ? '잘 팔리는데(실매출≥10만) 광고는 거의 안 하는 상품 — 광고 늘리면 매출 폭발 가능' : '실매출 발생 + 광고전환ROAS≥200% — 가격·무료배송·상품명 키워드 집중 대상'} · 실매출=판매자코드 매칭
            </div>
            <div className="overflow-auto">
              {focusLoading && <div className="text-center py-8 text-[#888]">불러오는 중…</div>}
              {!focusLoading && (
                <table className="w-full text-[12px]">
                  <thead className="bg-[#f5f6f8] text-[#555] sticky top-0">
                    <tr>
                      {[['product_no', '상품번호', 'left'], ['login_id', '계정', 'left'], ['seller_code', '판매자코드', 'left'],
                        ['product_name', '상품명', 'left'], ['cost', '광고비', 'right'], ['conv_roas', '광고전환ROAS', 'right'],
                        ['real_sales', '실매출', 'right'], ['real_roas', '실ROAS', 'right'], ['clicks', '클릭', 'right']].map(([k, lbl, al]) => (
                        <th key={k} onClick={() => focusSortClick(k)} className={`px-2 py-2 cursor-pointer select-none hover:bg-[#eaeaea] ${al === 'left' ? 'text-left' : 'text-right'}`}>{lbl}{focusArrow(k)}</th>
                      ))}
                      <th className="px-2 py-2 text-left">키워드</th>
                    </tr>
                  </thead>
                  <tbody>
                    {focusDisp.length === 0 && <tr><td colSpan={10} className="text-center py-6 text-[#888]">대상 없음</td></tr>}
                    {focusDisp.map((d: any, i: number) => {
                      const r = d.r; const k = d.k; const cont = !d.first; const dim = cont ? 'opacity-40' : '';
                      return (
                      <tr key={r.product_no + '_' + (k ? k.keyword : '') + '_' + i} className={`border-t hover:bg-[#f7f7f7] ${cont ? 'border-t-0' : ''}`}>
                        <td className={`px-2 py-1 font-mono ${dim}`}>{r.product_no}</td>
                        <td className={`px-2 py-1 text-[#666] ${dim}`}>{r.login_id}</td>
                        <td className={`px-2 py-1 font-mono text-[#666] ${dim}`}>{r.seller_code || '-'}</td>
                        <td className={`px-2 py-1 truncate max-w-[220px] ${dim}`} title={r.product_name}>{r.product_name}</td>
                        <td className={`px-2 py-1 text-right ${dim}`}>{formatKRW(r.cost || 0)}</td>
                        <td className={`px-2 py-1 text-right ${roasColor(r.conv_roas)} ${dim}`}>{r.conv_roas}%</td>
                        <td className={`px-2 py-1 text-right font-semibold text-[#0369a1] ${dim}`}>{formatKRW(r.real_sales || 0)}</td>
                        <td className={`px-2 py-1 text-right ${roasColor(r.real_roas)} ${dim}`}>{r.real_roas}%</td>
                        <td className={`px-2 py-1 text-right ${dim}`}>{(r.clicks || 0).toLocaleString()}</td>
                        <td className="px-2 py-1">
                          {k === undefined ? (
                            (r.keywords && r.keywords.length) ? (
                              <div className="flex flex-wrap gap-1 max-w-[300px] cursor-pointer" title="클릭 — 키워드별 상세"
                                onClick={() => setKwDetail({ productNo: r.product_no, sellerCode: r.seller_code, keywords: r.keywords })}>
                                {r.keywords.slice(0, 8).map((kk: any, j: number) => (
                                  <span key={j} className="px-1 py-0.5 rounded text-[10px] bg-gray-100 text-[#666]">{kk.keyword}</span>
                                ))}
                                {r.keywords.length > 8 && <span className="text-[10px] text-[#6429c4] font-semibold">+{r.keywords.length - 8}</span>}
                              </div>
                            ) : <span className="text-[#ccc] text-[11px]">-</span>
                          ) : k ? <span className="text-[#333]">{k.keyword}</span> : <span className="text-[#ccc] text-[11px]">-</span>}
                        </td>
                      </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {kwDetail && (
        <GmktKeywordDetailModal
          productNo={kwDetail.productNo} sellerCode={kwDetail.sellerCode}
          keywords={kwDetail.keywords} onClose={() => setKwDetail(null)} />
      )}
    </div>
  );
}

function Card({ label, value, color, sub }: { label: string; value: string; color?: string; sub?: string }) {
  return (
    <div className="bg-white rounded shadow px-4 py-2 min-w-[160px]">
      <div className="text-[11px] text-[#888]">{label}</div>
      <div className={`text-lg font-bold ${color || 'text-[#222]'}`}>{value}</div>
      {sub && <div className="text-[10px] text-[#aaa]">{sub}</div>}
    </div>
  );
}
