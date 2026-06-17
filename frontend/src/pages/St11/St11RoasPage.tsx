import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import { formatKRW, todayStr, ymd } from '../../utils/format';
import type { PeriodMode } from '../../types/cpc';
import PeriodSelector from '../../components/cpc/PeriodSelector';
import DateNavigator from '../../components/cpc/DateNavigator';
import DateRangePicker from '../../components/cpc/DateRangePicker';

interface RoasRow {
  login_id: string; name: string; grade: number | null;
  sales: number; profit: number; cost: number;
  roas: number | null; net_after_ad: number;
  conv_amount?: number; conv_roas?: number | null;
}
interface RoasResp {
  period: string; date_from: string; date_to: string; target_roas: number;
  totals: { sales: number; cost: number; profit: number; roas: number | null; net_after_ad: number; conv_amount?: number; conv_roas?: number | null; count: number; above_target: number; below_target: number };
  rows: RoasRow[];
}

const TARGET = 500;

// 적자모달 비고(판매상태) 정렬 우선순위 + 색상
const LOSS_STATUS_ORDER: Record<string, number> = {
  '삭제완료': 0, '삭제됨': 1, '판매금지': 2, '중복등록': 3,
  '판매중': 4, '판매중지': 5, '품절': 6, '재고부족': 7, '미등록': 8, '삭제(코드보존)': 9,
};
function lossStatusColor(s: string): string {
  if (s === '삭제완료') return 'text-[#1e6fd9] font-bold';
  if (s === '삭제됨' || s === '판매금지') return 'text-[#dc2626] font-semibold';
  if (s === '중복등록') return 'text-[#7c3aed] font-semibold';
  if (s === '판매중') return 'text-[#15803d]';
  return 'text-[#e08000]';   // 판매중지/품절/미등록 등
}

function roasColor(roas: number | null): string {
  if (roas === null) return 'text-[#dc2626] font-bold';      // 매출0 = 적자
  if (roas >= TARGET) return 'text-[#00a651] font-bold';      // 목표 달성
  if (roas >= 200) return 'text-[#e08000] font-semibold';     // 본전 근처
  return 'text-[#dc2626] font-semibold';                       // 적자권
}

// periodMode + 기준일(date) → 조회 시작/종료일 (오늘 이후로는 안 넘어감)
function rangeOf(mode: PeriodMode, date: string, rStart: string, rEnd: string): { from: string; to: string } {
  const today = todayStr();
  const [y, m] = date.split('-').map(Number);
  const cap = (d: string) => (d > today ? today : d);
  if (mode === 'yearly') return { from: `${y}-01-01`, to: cap(`${y}-12-31`) };
  if (mode === 'monthly') return { from: `${y}-${String(m).padStart(2, '0')}-01`, to: cap(ymd(new Date(y, m, 0))) };
  if (mode === 'range') return { from: rStart, to: rEnd };
  return { from: date, to: date }; // daily
}

// 모달 기간 프리셋 → date_from/date_to (adoffice는 전일까지라 to=어제)
function modalRange(p: string, cFrom: string, cTo: string): { from: string; to: string } {
  const y = new Date(); y.setDate(y.getDate() - 1);
  const yest = ymd(y);
  const Y = y.getFullYear(), M = y.getMonth();
  if (p === 'year') return { from: `${Y}-01-01`, to: yest };
  if (p === 'thismonth') return { from: ymd(new Date(Y, new Date().getMonth(), 1)), to: yest };
  if (p === 'lastmonth') {
    const lm = new Date(new Date().getFullYear(), new Date().getMonth() - 1, 1);
    return { from: ymd(lm), to: ymd(new Date(lm.getFullYear(), lm.getMonth() + 1, 0)) };
  }
  if (p === 'custom') return { from: cFrom, to: cTo };
  // recent(최근한달)
  const r = new Date(y); r.setDate(r.getDate() - 29);
  return { from: ymd(r), to: yest };
}

const MODAL_PERIODS: { key: string; label: string }[] = [
  { key: 'recent', label: '최근한달' }, { key: 'thismonth', label: '당월' },
  { key: 'lastmonth', label: '전월' }, { key: 'year', label: '연간' }, { key: 'custom', label: '기간' },
];

export default function St11RoasPage() {
  const nav = useNavigate();
  const [periodMode, setPeriodMode] = useState<PeriodMode>('daily');
  const [date, setDate] = useState<string>(todayStr());
  const [rangeStart, setRangeStart] = useState<string>(todayStr());
  const [rangeEnd, setRangeEnd] = useState<string>(todayStr());
  const [data, setData] = useState<RoasResp | null>(null);
  const [loading, setLoading] = useState(false);

  // 크롤링(상품/키워드 수집) — 기간 지정
  const yyy = (() => { const d = new Date(); d.setDate(d.getDate() - 1); return ymd(d); })();
  const [crawlFrom, setCrawlFrom] = useState('2026-01-01');
  const [crawlTo, setCrawlTo] = useState(yyy);
  const [crawlRunning, setCrawlRunning] = useState(false);
  useEffect(() => {
    const chk = () => api.get('/cpc/crawler/eleven-cost/status/').then(r => setCrawlRunning(!!r.data?.running)).catch(() => {});
    chk(); const t = setInterval(chk, 5000); return () => clearInterval(t);
  }, []);
  const startCrawl = async () => {
    try {
      const r = await api.post('/cpc/crawler/eleven-product-daily/run/', { date_from: crawlFrom, date_to: crawlTo });
      if (r.data?.status === 'started') { setCrawlRunning(true); alert(`크롤링 시작! (${crawlFrom} ~ ${crawlTo})\n계정마다 시간이 걸리니 진행 중엔 강제중지로 멈출 수 있어요.`); }
      else alert(r.data?.error || '시작 실패');
    } catch (e: any) { alert(e?.response?.data?.error || '시작 실패 — 이미 다른 크롤이 실행 중일 수 있습니다.'); }
  };
  const stopCrawl = async () => {
    if (!window.confirm('실행 중인 크롤을 강제 중지할까요?')) return;
    try { const r = await api.post('/cpc/crawler/eleven-cost/stop/'); setCrawlRunning(false); alert(r.data?.message || '중지했습니다.'); }
    catch { alert('중지 실패'); }
  };

  // 상품코드별 ROAS 상세 모달 (판단 오른쪽 '상세' 버튼)
  const [detail, setDetail] = useState<{ login_id: string; name: string } | null>(null);
  const [detailData, setDetailData] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [mSort, setMSort] = useState<{ key: string; dir: 'asc' | 'desc' }>({ key: 'cost', dir: 'desc' });
  const [mStatusFilter, setMStatusFilter] = useState('');   // 상세 모달 비고(판매상태) 필터
  const [roasOp, setRoasOp] = useState<'all' | 'gte' | 'lte'>('all');
  const [roasVal, setRoasVal] = useState('');
  const [mPeriod, setMPeriod] = useState('recent');
  const [mFrom, setMFrom] = useState(todayStr());
  const [mTo, setMTo] = useState(todayStr());

  const fetchDetail = useCallback((login_id: string, op: 'all' | 'gte' | 'lte', val: string, period: string, cf: string, ct: string) => {
    setDetailLoading(true);
    const { from, to } = modalRange(period, cf, ct);
    const params: any = { eleven_id: login_id, date_from: from, date_to: to };
    if (op === 'gte' && val !== '') params.roas_min = val;
    if (op === 'lte' && val !== '') params.roas_max = val;
    api.get('/cpc/eleven-product-roas/', { params })
      .then(r => setDetailData(r.data))
      .catch(() => setDetailData(null))
      .finally(() => setDetailLoading(false));
  }, []);
  const openDetail = useCallback((login_id: string, name: string) => {
    setDetail({ login_id, name }); setDetailData(null);
    setRoasOp('all'); setRoasVal(''); setMSort({ key: 'cost', dir: 'desc' }); setMPeriod('year');
    setMView('product'); setKwData(null); setMStatusFilter('');
    fetchDetail(login_id, 'all', '', 'year', '', '');
  }, [fetchDetail]);
  const mSortClick = (key: string) =>
    setMSort(s => s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: key === 'product_no' ? 'asc' : 'desc' });
  const mArrow = (key: string) => mSort.key === key ? (mSort.dir === 'asc' ? ' ▲' : ' ▼') : '';
  const excelDownload = async () => {
    if (!detail) return;
    const { from, to } = modalRange(mPeriod, mFrom, mTo);
    const params: any = { eleven_id: detail.login_id, export: 1, date_from: from, date_to: to };
    if (roasOp === 'gte' && roasVal !== '') params.roas_min = roasVal;
    if (roasOp === 'lte' && roasVal !== '') params.roas_max = roasVal;
    try {
      const r = await api.get('/cpc/eleven-product-roas/', { params, responseType: 'blob' });
      const url = URL.createObjectURL(r.data as Blob);
      const a = document.createElement('a');
      a.href = url; a.download = `roas_${detail.login_id}_${detailData?.period || ''}.csv`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    } catch { alert('엑셀 다운로드 실패'); }
  };
  // 키워드 보기(ROAS 200%↑) + 적자상품 다운로드
  const [mView, setMView] = useState<'product' | 'keyword'>('product');
  const [kwData, setKwData] = useState<any | null>(null);
  const [kwLoading, setKwLoading] = useState(false);
  const fetchKeywords = (login_id: string) => {
    setMView('keyword'); setKwData(null); setKwLoading(true);
    const { from, to } = modalRange(mPeriod, mFrom, mTo);
    api.get('/cpc/eleven-keyword-roas/', { params: { eleven_id: login_id, date_from: from, date_to: to, roas_min: 200 } })
      .then(r => setKwData(r.data)).catch(() => setKwData(null)).finally(() => setKwLoading(false));
  };
  const blobDownload = async (url: string, params: any, fname: string) => {
    try {
      const r = await api.get(url, { params, responseType: 'blob' });
      const u = URL.createObjectURL(r.data as Blob);
      const a = document.createElement('a'); a.href = u; a.download = fname;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(u);
    } catch { alert('다운로드 실패'); }
  };
  const downloadKeywords300 = () => {
    if (!detail) return;
    const { from, to } = modalRange(mPeriod, mFrom, mTo);
    blobDownload('/cpc/eleven-keyword-roas/', { eleven_id: detail.login_id, export: 1, date_from: from, date_to: to, roas_min: 200 }, `키워드ROAS200_${detail.login_id}.csv`);
  };

  // 전체 계정 다운로드 (2026 연간 기준) — 페이지 상단 버튼
  const ALL_FROM = '2026-01-01';
  const allDlKw300 = () => blobDownload('/cpc/eleven-keyword-roas/', { date_from: ALL_FROM, date_to: yyy, roas_min: 200, export: 1 }, `전체_키워드ROAS200_2026.csv`);
  const allDlLoss = () => { const r = modalRange(lossPeriod, lossFrom, lossTo); const p: any = { date_from: r.from, date_to: r.to, roas_max: 100, cost_min: 2000, clicks_min: 10, export: 1 }; if (lossEid) p.eleven_id = lossEid; blobDownload('/cpc/eleven-product-roas/', p, `적자상품_${lossEid || '전체'}_${r.from}_${r.to}.csv`); };
  const allDlProducts = () => blobDownload('/cpc/eleven-product-roas/', { date_from: ALL_FROM, date_to: yyy, export: 1 }, `전체_상품ROAS_2026.csv`);

  // 전체 ROAS200%↑ 키워드 모달 (복사·엑셀)
  const [kwAllOpen, setKwAllOpen] = useState(false);
  const [kwAllData, setKwAllData] = useState<any | null>(null);
  const [kwAllLoading, setKwAllLoading] = useState(false);
  const [kwAllPeriod, setKwAllPeriod] = useState('year');
  const [kwAllFrom, setKwAllFrom] = useState(todayStr());
  const [kwAllTo, setKwAllTo] = useState(todayStr());
  const fetchKwAll = (period: string, from: string, to: string) => {
    setKwAllLoading(true); setKwAllData(null);
    const r = modalRange(period, from, to);
    api.get('/cpc/eleven-keyword-roas/', { params: { date_from: r.from, date_to: r.to, roas_min: 200 } })
      .then(res => setKwAllData(res.data)).catch(() => setKwAllData(null)).finally(() => setKwAllLoading(false));
  };
  const openKwAll = () => { setKwAllPeriod('year'); setKwAllOpen(true); fetchKwAll('year', kwAllFrom, kwAllTo); };
  const kwAllExcel = () => { const r = modalRange(kwAllPeriod, kwAllFrom, kwAllTo); blobDownload('/cpc/eleven-keyword-roas/', { date_from: r.from, date_to: r.to, roas_min: 200, export: 1 }, `전체_키워드ROAS200_${r.from}_${r.to}.csv`); };
  const copyKwAllSeller = () => { const u = [...new Set((kwAllData?.rows || []).map((r: any) => r.seller_code).filter(Boolean))]; if (!u.length) { alert('판매자코드 없음'); return; } copyText(u.join('\n')); };
  const copyKwAllProdNos = () => { const seen = new Set<string>(); const nums = (kwAllData?.rows || []).map((r: any) => String(r.product_no ?? '').replace(/\D/g, '')).filter((n: string) => n && !seen.has(n) && seen.add(n)); if (!nums.length) { alert('상품번호 없음'); return; } copyText(nums.join('\n')); };

  // 전체 적자상품 모달 (2026 누적) + 상품번호 복사
  const [lossOpen, setLossOpen] = useState(false);
  const [lossData, setLossData] = useState<any | null>(null);
  const [lossLoading, setLossLoading] = useState(false);
  const [lossPeriod, setLossPeriod] = useState('year');
  const [lossFrom, setLossFrom] = useState(todayStr());
  const [lossTo, setLossTo] = useState(todayStr());
  const [lossEid, setLossEid] = useState('');        // '' = 전체계정, 값 = 특정계정
  const [lossName, setLossName] = useState('');      // 특정계정 이름(표시용)
  const fetchLoss = (period: string, from: string, to: string, eid = '') => {
    setLossLoading(true); setLossData(null); setLossStatusFilter('');
    const r = modalRange(period, from, to);
    const params: any = { date_from: r.from, date_to: r.to, roas_max: 100, cost_min: 2000, clicks_min: 10 };
    if (eid) params.eleven_id = eid;
    api.get('/cpc/eleven-product-roas/', { params })
      .then(res => setLossData(res.data)).catch(() => setLossData(null)).finally(() => setLossLoading(false));
  };
  // 상세 모달 → 그 계정 적자상품 모달 열기 (전체 적자모달 UI 재사용)
  const openLossForAccount = (eid: string, name: string) => {
    setLossEid(eid); setLossName(name); setLossPeriod(mPeriod); setLossOpen(true);
    fetchLoss(mPeriod, mFrom, mTo, eid);
  };
  const [lossSort, setLossSort] = useState<{ key: string; dir: 'asc' | 'desc' }>({ key: 'cost', dir: 'desc' });
  const [lossStatusFilter, setLossStatusFilter] = useState('');   // 비고(판매상태) 필터, '' = 전체
  const lossSortClick = (key: string) =>
    setLossSort(s => s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' }
      : { key, dir: (key === 'eleven_id' || key === 'product_no' || key === 'seller_code' || key === 'status') ? 'asc' : 'desc' });
  const lossArrow = (key: string) => lossSort.key === key ? (lossSort.dir === 'asc' ? ' ▲' : ' ▼') : '';
  const lossSortedRows: any[] = useMemo(() => {
    let rows = [...(lossData?.rows || [])];
    if (lossStatusFilter) rows = rows.filter(r => (r.status || '미등록') === lossStatusFilter);
    const { key, dir } = lossSort;
    const txt = (key === 'eleven_id' || key === 'seller_code' || key === 'product_no');
    rows.sort((a, b) => {
      if (key === 'status') {   // 비고: 상태 우선순위 순서로 정렬(Number 변환 불가라 기존엔 정렬 안 됐음)
        const ao = LOSS_STATUS_ORDER[a.status] ?? 99, bo = LOSS_STATUS_ORDER[b.status] ?? 99;
        const r = ao - bo || String(a.status || '').localeCompare(String(b.status || ''));
        return dir === 'asc' ? r : -r;
      }
      if (txt) { const r = String(a[key] || '').localeCompare(String(b[key] || '')); return dir === 'asc' ? r : -r; }
      const av = Number(a[key]) || 0, bv = Number(b[key]) || 0; return dir === 'asc' ? av - bv : bv - av;
    });
    return rows;
  }, [lossData, lossSort, lossStatusFilter]);
  const lossStatusCounts: Record<string, number> = useMemo(() => {
    const c: Record<string, number> = {};
    (lossData?.rows || []).forEach((r: any) => { const s = r.status || '미등록'; c[s] = (c[s] || 0) + 1; });
    return c;
  }, [lossData]);
  const markDeleted = () => {
    const rows = lossData?.rows || [];
    if (!rows.length) { alert('대상 적자상품이 없습니다.'); return; }
    if (!window.confirm(`11번가에서 실제 삭제하신 상품을 "삭제완료"(파란색)로 표시할까요?\n\n현재 화면의 ${rows.length}개를 처리합니다.`)) return;
    api.post('/cpc/eleven-loss-products/mark-deleted/', { items: rows.map((r: any) => ({ eleven_id: r.eleven_id, product_no: r.product_no })) })
      .then(r => { alert(r.data?.message || '삭제완료 처리됨'); fetchLoss(lossPeriod, lossFrom, lossTo, lossEid); })
      .catch(() => alert('처리 실패'));
  };
  // 1단계: 검증(dry-run) — 1상품으로 셀러오피스 접속·셀렉터만 확인(삭제 안 함)
  const validateLossDelete = () => {
    if (!window.confirm('🔎 삭제 검증(dry-run)\n\n셀러오피스 접속·상품검색·삭제 셀렉터를 1상품으로 확인합니다.\n실제 삭제는 하지 않습니다(안전).\n\n진행할까요?')) return;
    api.post('/cpc/eleven-loss-products/delete/', { date_from: ALL_FROM, date_to: yyy, roas_max: 100, cost_min: 2000, clicks_min: 10 })
      .then(r => alert(r.data?.message || '검증(dry-run) 시작 — 결과는 텔레그램/로그로 확인하세요.'))
      .catch(e => alert(e?.response?.data?.error || '시작 실패 — 다른 크롤이 실행 중일 수 있습니다.'));
  };
  // 2단계: 검증 후 실삭제 — 위험 경고 + 검증여부 확인 + 소량 테스트 + 최종확인
  const deleteLossProducts = () => {
    const n = lossData?.count || 0;
    if (!n) { alert('삭제할 적자상품이 없습니다.'); return; }
    if (!window.confirm(`⚠️ 위험: 11번가에서 상품이 실제·영구 삭제됩니다(되돌릴 수 없음).\n\n먼저 [🔎 삭제 검증]으로 셀러오피스 접속·셀렉터를 확인하셨나요?\n검증을 안 하셨다면 [취소]하고 검증부터 하세요.\n\n검증을 마쳤고, 실제 삭제를 진행하시겠습니까?`)) return;
    const limStr = window.prompt(`안전을 위해 '몇 개만' 테스트 삭제할 수 있습니다.\n\n· 소량 테스트: 숫자 입력 (예: 5) — 처음엔 강력 권장\n· 전체 ${n.toLocaleString()}개 삭제: 비워두고 확인\n\n(소량으로 실제 삭제가 잘 되는지 먼저 확인하세요)`, '5');
    if (limStr === null) return;
    const t = limStr.trim();
    const limit = t ? parseInt(t, 10) : null;
    if (limit !== null && (isNaN(limit) || limit < 1)) { alert('숫자를 입력하거나, 전체 삭제는 비워두세요.'); return; }
    const label = limit ? `${limit}개(테스트)` : `전체 ${n.toLocaleString()}개`;
    if (!window.confirm(`최종 확인 ⚠️\n\n${label} 상품을 11번가에서 영구 삭제합니다.\n정말 진행하시겠습니까?`)) return;
    const body: any = { date_from: ALL_FROM, date_to: yyy, roas_max: 100, cost_min: 2000, clicks_min: 10, real: 1 };
    if (limit) body.limit = limit;
    api.post('/cpc/eleven-loss-products/delete/', body)
      .then(r => alert(r.data?.message || '실삭제 시작 — 진행상황은 텔레그램/로그로 확인하세요.'))
      .catch(e => alert(e?.response?.data?.error || '시작 실패 — 다른 크롤이 실행 중일 수 있습니다.'));
  };
  const openLoss = () => {
    setLossOpen(true); setLossPeriod('year'); setLossEid(''); setLossName('');
    fetchLoss('year', lossFrom, lossTo, '');
  };
  const copyText = (text: string) => {
    const done = () => alert('복사되었습니다');
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
    } else fallbackCopy(text, done);
  };
  const fallbackCopy = (text: string, done: () => void) => {
    const ta = document.createElement('textarea'); ta.value = text;
    ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); done(); } catch { alert('복사 실패 — 수동 선택하세요'); }
    ta.remove();
  };
  const copyLossProductNos = () => {
    const nos = (lossData?.rows || []).map((r: any) => r.seller_code).filter(Boolean).join('\n');
    if (!nos) { alert('판매자코드 없음'); return; }
    copyText(nos);
  };
  // 상품번호코드 복사 — 11번가 상품관리 검색칸 붙여넣기용. 반드시 숫자만(비숫자 제거).
  const copyLossProdNos = () => {
    const seen = new Set<string>();
    const nums = (lossData?.rows || [])
      .map((r: any) => String(r.product_no ?? '').replace(/\D/g, ''))
      .filter((n: string) => n && !seen.has(n) && seen.add(n));
    if (!nums.length) { alert('상품번호 없음'); return; }
    copyText(nums.join('\n'));
  };

  const mSortedRows: any[] = useMemo(() => {
    if (!detailData?.rows) return [];
    let rows = detailData.rows as any[];
    if (mStatusFilter) rows = rows.filter((r: any) => (r.status || '미등록') === mStatusFilter);
    const dir = mSort.dir === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {
      if (mSort.key === 'product_no') return String(a.product_no).localeCompare(String(b.product_no)) * dir;
      return ((Number(a[mSort.key]) || 0) - (Number(b[mSort.key]) || 0)) * dir;
    });
  }, [detailData, mSort, mStatusFilter]);
  const mStatusCounts: Record<string, number> = useMemo(() => {
    const c: Record<string, number> = {};
    ((detailData?.rows || []) as any[]).forEach((r: any) => { const s = r.status || '미등록'; c[s] = (c[s] || 0) + 1; });
    return c;
  }, [detailData]);

  const fetchRoas = useCallback((mode: PeriodMode, d: string, rs: string, re: string) => {
    const { from, to } = rangeOf(mode, d, rs, re);
    setLoading(true);
    api.get('/cpc/eleven-roas/', { params: { period: 'range', date_from: from, date_to: to } })
      .then(r => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const load = useCallback(() => fetchRoas(periodMode, date, rangeStart, rangeEnd), [fetchRoas, periodMode, date, rangeStart, rangeEnd]);

  // 일간/월간/년간은 기준일/모드 바뀌면 즉시 조회 (기간별은 '조회' 버튼으로만). 마운트 시에도 1회 실행됨.
  useEffect(() => { if (periodMode !== 'range') fetchRoas(periodMode, date, rangeStart, rangeEnd); }, [periodMode, date, fetchRoas]);

  const onPrev = () => {
    const d = new Date(date);
    if (periodMode === 'yearly') d.setFullYear(d.getFullYear() - 1);
    else if (periodMode === 'monthly') d.setMonth(d.getMonth() - 1);
    else d.setDate(d.getDate() - 1);
    setDate(ymd(d));
  };
  const onNext = () => {
    const d = new Date(date);
    if (periodMode === 'yearly') d.setFullYear(d.getFullYear() + 1);
    else if (periodMode === 'monthly') d.setMonth(d.getMonth() + 1);
    else d.setDate(d.getDate() + 1);
    const nd = ymd(d);
    if (nd <= todayStr()) setDate(nd);
  };

  // 정렬 상태 — 기본: ROAS 낮은 순(적자 먼저)
  type SortKey = 'name' | 'grade' | 'sales' | 'cost' | 'roas' | 'conv_amount' | 'conv_roas' | 'net_after_ad' | 'judgment';
  const [sortKey, setSortKey] = useState<SortKey>('roas');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const judgeRank = (r: RoasRow) =>
    (r.roas !== null && r.roas >= TARGET) ? 2 : (r.cost > 0 ? 0 : 1); // 광고점검0 < -1 < 유지2

  const onSort = (key: SortKey) => {
    if (key === sortKey) setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(key); setSortDir(key === 'name' || key === 'roas' || key === 'judgment' || key === 'grade' ? 'asc' : 'desc'); }
  };

  const sortedRows = useMemo(() => {
    if (!data) return [];
    const dir = sortDir === 'asc' ? 1 : -1;
    const rows = [...data.rows];
    rows.sort((a, b) => {
      if (sortKey === 'name') return a.name.localeCompare(b.name) * dir;
      let av: number, bv: number;
      if (sortKey === 'roas') { av = a.roas === null ? -1 : a.roas; bv = b.roas === null ? -1 : b.roas; }
      else if (sortKey === 'conv_roas') { av = a.conv_roas == null ? -1 : a.conv_roas; bv = b.conv_roas == null ? -1 : b.conv_roas; }
      else if (sortKey === 'grade') { av = a.grade ?? 999; bv = b.grade ?? 999; }
      else if (sortKey === 'judgment') { av = judgeRank(a); bv = judgeRank(b); }
      else { av = (a as any)[sortKey] ?? 0; bv = (b as any)[sortKey] ?? 0; }
      return (av - bv) * dir;
    });
    return rows;
  }, [data, sortKey, sortDir]);

  const arrow = (key: SortKey) => sortKey === key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';

  const t = data?.totals;

  return (
    <div className="p-3 md:p-5 max-w-[1100px] mx-auto">
      <div className="flex items-center gap-3 mb-3">
        <button onClick={() => nav('/st11')} className="text-[#888] hover:text-[#333] text-[12px]">← 11번가</button>
        <h1 className="text-[20px] font-bold text-[#333]">11번가 ROAS 대시보드</h1>
        <span className="text-[12px] text-[#888]">목표 ROAS <b className="text-[#00a651]">{TARGET}%</b> 이상</span>
        <div className="ml-auto flex items-center gap-2 flex-wrap">
          {periodMode === 'range'
            ? <DateRangePicker startDate={rangeStart} endDate={rangeEnd}
                onStartChange={setRangeStart} onEndChange={setRangeEnd}
                onSearch={() => fetchRoas('range', date, rangeStart, rangeEnd)} />
            : <DateNavigator date={date} periodMode={periodMode}
                onPrev={onPrev} onNext={onNext} onToday={() => setDate(todayStr())}
                onDateChange={setDate} />}
          <button onClick={load} className="px-3 py-1 text-[11px] font-semibold bg-[#e67700] text-white rounded hover:bg-[#bf5600]">새로고침</button>
          <PeriodSelector value={periodMode} onChange={setPeriodMode} />
        </div>
      </div>

      {/* 크롤링(수집) 바 — 기간 지정 */}
      <div className="flex items-center gap-2 mb-3 flex-wrap text-[12px] bg-[#fff8f0] border border-[#ffe0c0] rounded px-3 py-2">
        <span className="font-semibold text-[#c2410c]">📥 상품·키워드 ROAS 크롤링</span>
        <span className="text-[#888] ml-1">기간</span>
        <input type="date" value={crawlFrom} onChange={e => setCrawlFrom(e.target.value)} className="border border-[#ccc] rounded px-1.5 py-1 text-[12px]" />
        <span>~</span>
        <input type="date" value={crawlTo} onChange={e => setCrawlTo(e.target.value)} className="border border-[#ccc] rounded px-1.5 py-1 text-[12px]" />
        <button onClick={startCrawl} disabled={crawlRunning}
          className="px-3 py-1 text-[12px] font-semibold bg-[#c2410c] text-white rounded hover:bg-[#9a3412] disabled:opacity-40 disabled:cursor-not-allowed">
          {crawlRunning ? '크롤링 중…' : '수집 시작'}</button>
        <button onClick={stopCrawl} disabled={!crawlRunning}
          className="px-3 py-1 text-[12px] font-semibold bg-[#dc2626] text-white rounded hover:bg-[#b91c1c] disabled:opacity-40 disabled:cursor-not-allowed">강제중지</button>
        <span className={`text-[12px] ${crawlRunning ? 'text-[#c2410c] font-semibold' : 'text-[#999]'}`}>{crawlRunning ? '● 진행 중' : '대기'}</span>
        <span className="ml-auto text-[#bbb] text-[11px] hidden lg:inline">전체관리(2026):</span>
        <button onClick={openKwAll} title="전체 계정 ROAS200%↑ 키워드 — 판매자코드·상품번호 복사 · 엑셀" className="px-2.5 py-1 text-[12px] font-semibold bg-[#7c3aed] text-white rounded hover:bg-[#6429c4]">전체 ROAS200%↑ 키워드 📋</button>
        <button onClick={openLoss} title="ROAS≤100·광고비≥2천·클릭≥10 (2026 누적). 클릭 시 상품번호 목록·복사" className="px-2.5 py-1 text-[12px] font-semibold bg-[#c2410c] text-white rounded hover:bg-[#9a3412]">전체 적자상품 📋</button>
        <button onClick={allDlProducts} className="px-2.5 py-1 text-[12px] font-semibold bg-[#1d7a46] text-white rounded hover:bg-[#155c34]">전체 상품ROAS ⬇</button>
      </div>

      {/* 요약 카드 */}
      {t && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2 mb-4">
          <Card label="광고비" value={formatKRW(t.cost)} sub="CPC" />
          <Card label="광고전환매출" value={formatKRW(t.conv_amount || 0)} sub="광고센터" />
          <Card label="광고전환ROAS" value={t.conv_roas != null ? `${t.conv_roas}%` : '-'}
            valueClass={(t.conv_roas ?? 0) >= TARGET ? 'text-[#00a651]' : 'text-[#dc2626]'} sub="광고센터" />
          <Card label="실매출" value={formatKRW(t.sales)} sub="정산매출" />
          <Card label="실ROAS" value={t.roas !== null ? `${t.roas}%` : '-'}
            valueClass={t.roas !== null && t.roas >= TARGET ? 'text-[#00a651]' : 'text-[#dc2626]'}
            sub={`목표 ${TARGET}%`} />
          <Card label="광고차감 순익" value={formatKRW(t.net_after_ad)}
            valueClass={t.net_after_ad >= 0 ? 'text-[#00a651]' : 'text-[#dc2626]'} />
        </div>
      )}

      {loading && <div className="text-center text-[#888] py-8">불러오는 중…</div>}

      {/* 계정별 표 (적자 먼저) */}
      {data && !loading && (
        <div className="bg-white border border-[#e0e0e0] rounded overflow-hidden">
          <table className="w-full text-[12px] md:text-[12px]">
            <thead>
              <tr className="bg-[#f7f7f7] text-[#666] border-b border-[#e0e0e0] select-none">
                <th className="text-center px-2 py-2 w-[40px]">#</th>
                <th onClick={() => onSort('name')} className="text-left px-3 py-2 cursor-pointer hover:text-[#1e6fd9]">계정{arrow('name')}</th>
                <th onClick={() => onSort('grade')} className="text-center px-3 py-2 cursor-pointer hover:text-[#1e6fd9]">등급{arrow('grade')}</th>
                <th onClick={() => onSort('cost')} className="text-right px-3 py-2 cursor-pointer hover:text-[#1e6fd9]">광고비{arrow('cost')}</th>
                <th onClick={() => onSort('conv_amount')} title="광고센터(adoffice)가 집계한 광고 전환매출 (직접+간접)" className="text-right px-3 py-2 cursor-pointer hover:text-[#1e6fd9]">광고전환매출{arrow('conv_amount')}</th>
                <th onClick={() => onSort('conv_roas')} className="text-right px-3 py-2 cursor-pointer hover:text-[#1e6fd9]">광고전환ROAS{arrow('conv_roas')}</th>
                <th onClick={() => onSort('sales')} title="실제 정산매출 (판매자코드 전역매칭, 광고 외 유입 포함)" className="text-right px-3 py-2 cursor-pointer hover:text-[#1e6fd9]">실매출{arrow('sales')}</th>
                <th onClick={() => onSort('roas')} className="text-right px-3 py-2 cursor-pointer hover:text-[#1e6fd9]">실ROAS{arrow('roas')}</th>
                <th onClick={() => onSort('net_after_ad')} className="text-right px-3 py-2 cursor-pointer hover:text-[#1e6fd9]">광고차감 순익{arrow('net_after_ad')}</th>
                <th onClick={() => onSort('judgment')} className="text-center px-3 py-2 cursor-pointer hover:text-[#1e6fd9]">판단{arrow('judgment')}</th>
                <th className="text-center px-3 py-2">캠페인</th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((r, i) => (
                <tr key={r.login_id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa]">
                  <td className="px-2 py-1.5 text-center text-[#999]">{i + 1}</td>
                  <td className="px-3 py-1.5 font-medium text-[#333]">{r.name}<span className="text-[#bbb] text-[11px] ml-1">{r.login_id}</span></td>
                  <td className="px-3 py-1.5 text-center">{r.grade != null ? <span className="text-[11px] px-1.5 py-0.5 rounded bg-[#eef3fb] text-[#1e6fd9] font-semibold">{r.grade}등급</span> : <span className="text-[#ccc]">-</span>}</td>
                  <td className="px-3 py-1.5 text-right">{formatKRW(r.cost)}</td>
                  <td className="px-3 py-1.5 text-right text-[#777]">{formatKRW(r.conv_amount || 0)}</td>
                  <td className={`px-3 py-1.5 text-right ${roasColor(r.conv_roas ?? null)}`}>{r.conv_roas != null ? `${r.conv_roas}%` : '-'}</td>
                  <td className="px-3 py-1.5 text-right font-medium">{formatKRW(r.sales)}</td>
                  <td className={`px-3 py-1.5 text-right ${roasColor(r.roas)}`}>{r.roas !== null ? `${r.roas}%` : '매출0'}</td>
                  <td className={`px-3 py-1.5 text-right ${r.net_after_ad >= 0 ? 'text-[#333]' : 'text-[#dc2626]'}`}>{formatKRW(r.net_after_ad)}</td>
                  <td className="px-3 py-1.5 text-center">
                    {r.roas !== null && r.roas >= TARGET
                      ? <span className="text-[11px] px-2 py-0.5 rounded bg-[#e6f7ec] text-[#00a651]">유지</span>
                      : (r.cost > 0
                        ? <span className="text-[11px] px-2 py-0.5 rounded bg-[#fdecec] text-[#dc2626]">광고 점검</span>
                        : <span className="text-[11px] px-2 py-0.5 rounded bg-[#eee] text-[#888]">-</span>)}
                  </td>
                  <td className="px-3 py-1.5 text-center">
                    <button onClick={() => openDetail(r.login_id, r.name)}
                      className="text-[11px] px-2 py-0.5 rounded bg-[#1e6fd9] text-white hover:bg-[#1857ad]">상세 ▸</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.rows.length === 0 && <div className="text-center text-[#888] py-8">데이터 없음</div>}
        </div>
      )}
      <p className="text-[12px] text-[#999] mt-3">
        ※ ROAS = 매출 ÷ 광고비 × 100. <b className="text-[#dc2626]">"광고 점검"</b> 계정(500% 미만/매출0)의 광고 입찰·키워드를 줄이면 광고비가 절감되고 ROAS가 올라갑니다.
      </p>

      {/* 캠페인 상세 모달 */}
      {detail && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setDetail(null)}>
          <div className="bg-white rounded-lg shadow-xl max-w-[900px] w-[95%] max-h-[85vh] overflow-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-5 py-3 border-b border-[#eee] sticky top-0 bg-white flex-wrap">
              <h3 className="text-[12px] font-bold text-[#333]">{detail.name} <span className="text-[#bbb] text-[12px]">{detail.login_id}</span> 상품코드별 ROAS</h3>
              {detailData?.date_from && <span className="text-[11px] px-1.5 py-0.5 rounded bg-[#eef3fb] text-[#1e6fd9]">{detailData.date_from} ~ {detailData.date_to}</span>}
              {detailData?.collected_at && (
                <span className={`text-[11px] px-1.5 py-0.5 rounded ${String(detailData.collected_at).slice(0, 10) === todayStr() ? 'bg-[#fff3e0] text-[#e67700] font-semibold' : 'text-[#888]'}`}>
                  업데이트 {String(detailData.collected_at).replace('T', ' ').slice(0, 16)}{String(detailData.collected_at).slice(0, 10) === todayStr() ? ' (오늘)' : ''}
                </span>
              )}
              <button onClick={() => setDetail(null)} className="ml-auto text-[#999] hover:text-[#333] text-[12px]">✕</button>
            </div>
            <div className="p-4">
              {detailLoading && <div className="text-center text-[#888] py-6">불러오는 중…</div>}
              {!detailLoading && (!detailData || (detailData.rows || []).length === 0) && (
                <div className="text-center text-[#888] py-6">수집된 상품 데이터가 없습니다.<br /><span className="text-[12px]">(adoffice 상품보고서 수집 후 표시됩니다)</span></div>
              )}
              {/* 기간 선택 */}
              {detail && (
                <div className="flex items-center gap-1.5 mb-2 flex-wrap text-[12px]">
                  <span className="text-[#888]">기간</span>
                  {MODAL_PERIODS.map(p => (
                    <button key={p.key}
                      onClick={() => { setMPeriod(p.key); if (p.key !== 'custom') fetchDetail(detail.login_id, roasOp, roasVal, p.key, mFrom, mTo); }}
                      className={`px-2 py-0.5 text-[12px] rounded ${mPeriod === p.key ? 'bg-[#333] text-white' : 'bg-[#eee] text-[#555]'}`}>{p.label}</button>
                  ))}
                  {mPeriod === 'custom' && (
                    <>
                      <input type="date" value={mFrom} onChange={e => setMFrom(e.target.value)} className="border border-[#ccc] rounded px-1 py-0.5 text-[12px]" />
                      <span>~</span>
                      <input type="date" value={mTo} onChange={e => setMTo(e.target.value)} className="border border-[#ccc] rounded px-1 py-0.5 text-[12px]" />
                      <button onClick={() => fetchDetail(detail.login_id, roasOp, roasVal, 'custom', mFrom, mTo)} className="px-2 py-0.5 text-[12px] bg-[#1e6fd9] text-white rounded">조회</button>
                    </>
                  )}
                </div>
              )}
              {/* 상품 뷰: 필터 + 버튼들 */}
              {mView === 'product' && !detailLoading && detailData && (
                <div className="flex items-center gap-2 mb-3 flex-wrap text-[12px]">
                  <span className="text-[#888]">ROAS 필터</span>
                  <select value={roasOp} onChange={e => setRoasOp(e.target.value as any)}
                    className="border border-[#ccc] rounded px-1.5 py-1 text-[12px]">
                    <option value="all">전체</option>
                    <option value="gte">이상(≥)</option>
                    <option value="lte">이하(≤)</option>
                  </select>
                  <input type="number" value={roasVal} onChange={e => setRoasVal(e.target.value)}
                    placeholder="예: 500" disabled={roasOp === 'all'}
                    className="border border-[#ccc] rounded px-2 py-1 w-[80px] text-[12px] disabled:bg-[#f5f5f5]" />
                  <span className="text-[#888]">%</span>
                  <button onClick={() => detail && fetchDetail(detail.login_id, roasOp, roasVal, mPeriod, mFrom, mTo)}
                    className="px-2.5 py-1 text-[12px] font-semibold bg-[#1e6fd9] text-white rounded hover:bg-[#1857ad]">적용</button>
                  <button onClick={() => detail && fetchKeywords(detail.login_id)}
                    className="ml-auto px-2.5 py-1 text-[12px] font-semibold bg-[#7c3aed] text-white rounded hover:bg-[#6429c4]">ROAS 200%↑ 키워드</button>
                  <button onClick={() => detail && openLossForAccount(detail.login_id, detail.name)} title="이 계정의 적자상품 모달 — 판매자코드 복사 · 엑셀 · 삭제완료 처리"
                    className="px-2.5 py-1 text-[12px] font-semibold bg-[#c2410c] text-white rounded hover:bg-[#9a3412]">적자상품 📋 (ROAS≤100·광고비≥2천·클릭≥10)</button>
                  <button onClick={excelDownload}
                    className="px-2.5 py-1 text-[12px] font-semibold bg-[#1d7a46] text-white rounded hover:bg-[#155c34]">⬇ 엑셀</button>
                </div>
              )}
              {mView === 'product' && !detailLoading && detailData && (detailData.rows || []).length > 0 && (
                <>
                  <div className="text-[12px] text-[#555] mb-2">
                    필터결과 <b>{detailData.count.toLocaleString()}</b>개 상품 · 계정 광고비 <b>{formatKRW(detailData.totals.cost)}</b>
                    {' · '}광고전환매출 <b className="text-[#777]">{formatKRW(detailData.totals.conv_amount || 0)}</b> (ROAS <b className={Number(detailData.totals.conv_roas) >= TARGET ? 'text-[#00a651]' : 'text-[#dc2626]'}>{detailData.totals.conv_roas ?? '-'}%</b>)
                    {' · '}실매출 <b>{formatKRW(detailData.totals.sales)}</b> (ROAS <b className={Number(detailData.totals.roas) >= TARGET ? 'text-[#00a651]' : 'text-[#dc2626]'}>{detailData.totals.roas}%</b>)
                    {detailData.count > detailData.rows.length && <span className="text-[#999] ml-1">(상위 {detailData.rows.length}개 표시 · 전체는 엑셀로)</span>}
                  </div>
                  <table className="w-full text-[12px] [&_td]:whitespace-nowrap [&_th]:whitespace-nowrap [&_td]:px-3 [&_th]:px-3">
                    <thead>
                      <tr className="bg-[#f7f7f7] text-[#666] border-b border-[#e0e0e0] select-none">
                        <th onClick={() => mSortClick('product_no')} className="text-left px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">상품번호{mArrow('product_no')}</th>
                        <th className="text-left px-2 py-1.5">판매자코드</th>
                        <th onClick={() => mSortClick('cost')} className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">광고비{mArrow('cost')}</th>
                        <th onClick={() => mSortClick('conv_amount')} title="광고센터(adoffice)가 집계한 광고 전환매출 (직접+간접)" className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">광고전환매출{mArrow('conv_amount')}</th>
                        <th onClick={() => mSortClick('conv_roas_pct')} className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">광고전환ROAS{mArrow('conv_roas_pct')}</th>
                        <th onClick={() => mSortClick('sales')} title="실제 정산매출 (판매자코드 전역매칭, 광고 외 유입 포함)" className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">실매출{mArrow('sales')}</th>
                        <th onClick={() => mSortClick('roas_pct')} className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">실매출ROAS{mArrow('roas_pct')}</th>
                        <th onClick={() => mSortClick('clicks')} className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">클릭{mArrow('clicks')}</th>
                        <th onClick={() => mSortClick('impressions')} className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">노출{mArrow('impressions')}</th>
                        <th className="text-center px-2 py-1.5 align-top">
                          <span>비고</span>
                          <select
                            value={mStatusFilter}
                            onChange={e => setMStatusFilter(e.target.value)}
                            className={`block mx-auto mt-1 border rounded px-1 py-0.5 text-[11px] font-normal ${mStatusFilter ? 'border-[#1e6fd9] text-[#1e6fd9]' : 'border-[#ddd] text-[#666]'}`}
                          >
                            <option value="">전체 ({(detailData?.rows || []).length})</option>
                            {Object.keys(mStatusCounts)
                              .sort((a, b) => (LOSS_STATUS_ORDER[a] ?? 99) - (LOSS_STATUS_ORDER[b] ?? 99))
                              .map(st => <option key={st} value={st}>{st} ({mStatusCounts[st]})</option>)}
                          </select>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {mSortedRows.map((c: any) => {
                        const roas = Number(c.roas_pct ?? 0);
                        const convRoas = Number(c.conv_roas_pct ?? 0);
                        return (
                          <tr key={c.product_no} className="border-b border-[#f0f0f0] hover:bg-[#fafafa]">
                            <td className="px-2 py-1.5 font-medium text-[#333]">
                              <a href={`https://www.11st.co.kr/products/${c.product_no}`} target="_blank" rel="noreferrer" className="text-[#1e6fd9] hover:underline">{c.product_no}</a>
                            </td>
                            <td className="px-2 py-1.5 text-[#555]">{c.seller_code || '-'}</td>
                            <td className="px-2 py-1.5 text-right">{formatKRW(c.cost || 0)}</td>
                            <td className="px-2 py-1.5 text-right text-[#777]">{formatKRW(c.conv_amount || 0)}</td>
                            <td className={`px-2 py-1.5 text-right ${convRoas >= TARGET ? 'text-[#00a651]' : convRoas >= 200 ? 'text-[#e08000]' : 'text-[#dc2626]'}`}>{convRoas ? `${convRoas.toFixed(0)}%` : (c.cost ? '0%' : '-')}</td>
                            <td className="px-2 py-1.5 text-right font-medium">{formatKRW(c.sales || 0)}</td>
                            <td className={`px-2 py-1.5 text-right font-semibold ${roas >= TARGET ? 'text-[#00a651]' : roas >= 200 ? 'text-[#e08000]' : 'text-[#dc2626]'}`}>{roas ? `${roas.toFixed(0)}%` : (c.cost ? '0%' : '-')}</td>
                            <td className="px-2 py-1.5 text-right">{(c.clicks || 0).toLocaleString()}</td>
                            <td className="px-2 py-1.5 text-right">{(c.impressions || 0).toLocaleString()}</td>
                            <td className="px-2 py-1.5 text-center"><span className={lossStatusColor(c.status || '미등록')}>{c.status || '-'}</span></td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </>
              )}

              {/* 키워드 뷰 (ROAS 200%↑) */}
              {mView === 'keyword' && (
                <>
                  <div className="flex items-center gap-2 mb-3 flex-wrap text-[12px]">
                    <button onClick={() => setMView('product')} className="px-2.5 py-1 text-[12px] font-semibold bg-[#555] text-white rounded">← 상품으로</button>
                    <span className="text-[#333] font-semibold">ROAS 200% 이상 키워드</span>
                    {kwData?.count != null && <span className="text-[#888]">{kwData.count.toLocaleString()}개 (광고비순 상위 1000)</span>}
                    <button onClick={downloadKeywords300} className="ml-auto px-2.5 py-1 text-[12px] font-semibold bg-[#1d7a46] text-white rounded hover:bg-[#155c34]">⬇ 키워드 엑셀</button>
                  </div>
                  {kwLoading && <div className="text-center text-[#888] py-6">불러오는 중…</div>}
                  {!kwLoading && kwData && (kwData.rows || []).length === 0 && <div className="text-center text-[#888] py-6">ROAS 200% 이상 키워드가 없습니다.</div>}
                  {!kwLoading && kwData && (kwData.rows || []).length > 0 && (
                    <table className="w-full text-[12px] [&_td]:whitespace-nowrap [&_th]:whitespace-nowrap [&_td]:px-3 [&_th]:px-3">
                      <thead><tr className="bg-[#f7f7f7] text-[#666] border-b border-[#e0e0e0]">
                        <th className="text-left px-2 py-1.5">상품번호</th>
                        <th className="text-left px-2 py-1.5">판매자코드</th>
                        <th className="text-left px-2 py-1.5">키워드</th>
                        <th className="text-right px-2 py-1.5">광고비</th>
                        <th className="text-right px-2 py-1.5">전환매출</th>
                        <th className="text-right px-2 py-1.5">ROAS</th>
                        <th className="text-right px-2 py-1.5">클릭</th>
                        <th className="text-right px-2 py-1.5">전환</th>
                      </tr></thead>
                      <tbody>
                        {kwData.rows.map((c: any, i: number) => (
                          <tr key={i} className="border-b border-[#f0f0f0] hover:bg-[#fafafa]">
                            <td className="px-2 py-1.5"><a href={`https://www.11st.co.kr/products/${c.product_no}`} target="_blank" rel="noreferrer" className="text-[#1e6fd9] hover:underline">{c.product_no}</a></td>
                            <td className="px-2 py-1.5 text-[#555]">{c.seller_code || '-'}</td>
                            <td className="px-2 py-1.5 font-medium text-[#333]">{c.keyword}</td>
                            <td className="px-2 py-1.5 text-right">{formatKRW(c.cost || 0)}</td>
                            <td className="px-2 py-1.5 text-right">{formatKRW(c.conv_amount || 0)}</td>
                            <td className="px-2 py-1.5 text-right font-semibold text-[#00a651]">{Number(c.roas_pct).toFixed(0)}%</td>
                            <td className="px-2 py-1.5 text-right">{(c.clicks || 0).toLocaleString()}</td>
                            <td className="px-2 py-1.5 text-right">{c.conversions || 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 전체 적자상품 모달 (2026 누적) */}
      {kwAllOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setKwAllOpen(false)}>
          <div className="bg-white rounded-lg shadow-xl max-w-[980px] w-[95%] max-h-[85vh] overflow-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-5 py-3 border-b border-[#eee] sticky top-0 bg-white flex-wrap">
              <h3 className="text-[12px] font-bold text-[#333]">전체 ROAS200%↑ 키워드</h3>
              {kwAllData && <span className="text-[12px] text-[#7c3aed] font-semibold">{(kwAllData.count || 0).toLocaleString()}개</span>}
              <button onClick={copyKwAllSeller} className="ml-auto px-2.5 py-1 text-[12px] font-semibold bg-[#1e6fd9] text-white rounded hover:bg-[#1857ad]">📋 판매자코드 복사</button>
              <button onClick={copyKwAllProdNos} title="상품번호(숫자만) 중복제거 복사 — 11번가 상품관리 검색칸용" className="px-2.5 py-1 text-[12px] font-semibold bg-[#0d9488] text-white rounded hover:bg-[#0f766e]">📋 상품번호코드 복사</button>
              <button onClick={kwAllExcel} className="px-2.5 py-1 text-[12px] font-semibold bg-[#1d7a46] text-white rounded hover:bg-[#155c34]">⬇ 엑셀</button>
              <button onClick={() => setKwAllOpen(false)} className="px-2 py-1 text-[12px] text-[#888] hover:text-[#333]">✕</button>
            </div>
            <div className="flex items-center gap-1.5 px-5 py-2 border-b border-[#f0f0f0] flex-wrap">
              <span className="text-[12px] text-[#888] mr-1">기간:</span>
              {MODAL_PERIODS.map(p => (
                <button key={p.key} onClick={() => { setKwAllPeriod(p.key); if (p.key !== 'custom') fetchKwAll(p.key, kwAllFrom, kwAllTo); }}
                  className={`px-2 py-0.5 text-[12px] rounded ${kwAllPeriod === p.key ? 'bg-[#333] text-white' : 'bg-[#eee] text-[#555]'}`}>{p.label}</button>
              ))}
              {kwAllPeriod === 'custom' && (
                <span className="flex items-center gap-1 ml-1">
                  <input type="date" value={kwAllFrom} onChange={e => setKwAllFrom(e.target.value)} className="border rounded px-1 text-[12px]" />
                  <span className="text-[#999]">~</span>
                  <input type="date" value={kwAllTo} onChange={e => setKwAllTo(e.target.value)} className="border rounded px-1 text-[12px]" />
                  <button onClick={() => fetchKwAll('custom', kwAllFrom, kwAllTo)} className="px-2 py-0.5 text-[12px] bg-[#1e6fd9] text-white rounded">적용</button>
                </span>
              )}
              {kwAllData && <span className="text-[12px] text-[#888] ml-2">{kwAllData.date_from} ~ {kwAllData.date_to}</span>}
            </div>
            <div className="p-4">
              {kwAllLoading && <div className="text-center text-[#888] py-6">불러오는 중…</div>}
              {!kwAllLoading && kwAllData && (kwAllData.rows || []).length === 0 && <div className="text-center text-[#888] py-6">ROAS 200% 이상 키워드가 없습니다.</div>}
              {!kwAllLoading && kwAllData && (kwAllData.rows || []).length > 0 && (
                <table className="w-full text-[12px] [&_td]:whitespace-nowrap [&_th]:whitespace-nowrap [&_td]:px-3 [&_th]:px-3">
                  <thead><tr className="bg-[#f7f7f7] text-[#666] border-b border-[#e0e0e0]">
                    <th className="text-center px-2 py-1.5">번호</th>
                    <th className="text-left px-2 py-1.5">아이디</th>
                    <th className="text-left px-2 py-1.5">상품번호</th>
                    <th className="text-left px-2 py-1.5">판매자코드</th>
                    <th className="text-left px-2 py-1.5">키워드</th>
                    <th className="text-right px-2 py-1.5">광고비</th>
                    <th className="text-right px-2 py-1.5">전환매출</th>
                    <th className="text-right px-2 py-1.5">ROAS</th>
                    <th className="text-right px-2 py-1.5">클릭</th>
                  </tr></thead>
                  <tbody>
                    {(kwAllData.rows || []).map((r: any, i: number) => (
                      <tr key={i} className="border-b border-[#f0f0f0] hover:bg-[#fafafa]">
                        <td className="px-2 py-1.5 text-center text-[#999]">{i + 1}</td>
                        <td className="px-2 py-1.5 text-[#555]">{r.eleven_id}</td>
                        <td className="px-2 py-1.5 font-medium"><a href={`https://www.11st.co.kr/products/${r.product_no}`} target="_blank" rel="noreferrer" className="text-[#1e6fd9] hover:underline">{r.product_no}</a></td>
                        <td className="px-2 py-1.5 text-[#555]">{r.seller_code || '-'}</td>
                        <td className="px-2 py-1.5 text-[#333]">{r.keyword}</td>
                        <td className="px-2 py-1.5 text-right">{formatKRW(r.cost || 0)}</td>
                        <td className="px-2 py-1.5 text-right">{formatKRW(r.conv_amount || 0)}</td>
                        <td className="px-2 py-1.5 text-right font-semibold text-[#15803d]">{Number(r.roas_pct).toFixed(0)}%</td>
                        <td className="px-2 py-1.5 text-right">{(r.clicks || 0).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {kwAllData && (kwAllData.count || 0) > (kwAllData.rows || []).length && (
                <div className="text-center text-[11px] text-[#999] py-2">표는 상위 {(kwAllData.rows || []).length}개만 표시 — 전체는 ⬇ 엑셀로 받으세요</div>
              )}
            </div>
          </div>
        </div>
      )}

      {lossOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setLossOpen(false)}>
          <div className="bg-white rounded-lg shadow-xl max-w-[920px] w-[95%] max-h-[85vh] overflow-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-5 py-3 border-b border-[#eee] sticky top-0 bg-white flex-wrap">
              <h3 className="text-[12px] font-bold text-[#333]">{lossEid ? `적자상품 — ${lossName || lossEid}` : '전체 적자상품'}</h3>
              <span className="text-[11px] text-[#888]">ROAS≤100 · 광고비≥2천 · 클릭≥10</span>
              {lossData && <span className="text-[12px] text-[#c2410c] font-semibold">{lossData.count.toLocaleString()}개</span>}
              <button onClick={copyLossProductNos} className="ml-auto px-2.5 py-1 text-[12px] font-semibold bg-[#1e6fd9] text-white rounded hover:bg-[#1857ad]">📋 판매자코드 복사</button>
              <button onClick={copyLossProdNos} title="적자상품 전체의 상품번호(숫자만)를 복사 — 11번가 상품관리 검색칸 붙여넣기용" className="px-2.5 py-1 text-[12px] font-semibold bg-[#0d9488] text-white rounded hover:bg-[#0f766e]">📋 상품번호코드 복사</button>
              <button onClick={allDlLoss} className="px-2.5 py-1 text-[12px] font-semibold bg-[#1d7a46] text-white rounded hover:bg-[#155c34]">⬇ 엑셀</button>
              <button onClick={markDeleted} title="11번가에서 직접 삭제 완료한 상품을 '삭제완료'로 표시" className="px-2.5 py-1 text-[12px] font-bold bg-[#dc2626] text-white rounded hover:bg-[#b91c1c]">✓ 삭제완료 처리</button>
              <button onClick={validateLossDelete} title="셀러오피스 접속·셀렉터를 1상품으로 검증(실제 삭제 안 함)" className="px-2.5 py-1 text-[12px] font-semibold bg-[#0369a1] text-white rounded hover:bg-[#075985]">🔎 삭제 검증</button>
              <button onClick={deleteLossProducts} title="⚠️ 위험: 셀러오피스에서 실제 영구 삭제(검증 후 진행)" className="px-2.5 py-1 text-[12px] font-bold bg-[#7f1d1d] text-white rounded hover:bg-[#601515]">🗑 실제 삭제</button>
              <button onClick={() => setLossOpen(false)} className="text-[#999] hover:text-[#333] text-[12px]">✕</button>
            </div>
            <div className="px-5 py-2 border-b border-[#f0f0f0] flex items-center gap-1.5 flex-wrap">
              <span className="text-[12px] text-[#888] mr-1">기간:</span>
              {MODAL_PERIODS.map(p => (
                <button key={p.key} onClick={() => { setLossPeriod(p.key); if (p.key !== 'custom') fetchLoss(p.key, lossFrom, lossTo, lossEid); }}
                  className={`px-2 py-0.5 text-[12px] rounded ${lossPeriod === p.key ? 'bg-[#333] text-white' : 'bg-[#eee] text-[#555]'}`}>{p.label}</button>
              ))}
              {lossPeriod === 'custom' && (
                <span className="flex items-center gap-1 ml-1">
                  <input type="date" value={lossFrom} onChange={e => setLossFrom(e.target.value)} className="border rounded px-1 text-[12px]" />
                  <span className="text-[#999]">~</span>
                  <input type="date" value={lossTo} onChange={e => setLossTo(e.target.value)} className="border rounded px-1 text-[12px]" />
                  <button onClick={() => fetchLoss('custom', lossFrom, lossTo, lossEid)} className="px-2 py-0.5 text-[12px] bg-[#1e6fd9] text-white rounded">적용</button>
                </span>
              )}
              {lossData && <span className="text-[12px] text-[#888] ml-2">{lossData.date_from} ~ {lossData.date_to}</span>}
            </div>
            <div className="p-4">
              {lossLoading && <div className="text-center text-[#888] py-6">불러오는 중…</div>}
              {!lossLoading && lossData && (lossData.rows || []).length === 0 && <div className="text-center text-[#888] py-6">대상 적자상품이 없습니다.</div>}
              {!lossLoading && lossData && (lossData.rows || []).length > 0 && (
                <table className="w-full text-[12px] [&_td]:whitespace-nowrap [&_th]:whitespace-nowrap [&_td]:px-3 [&_th]:px-3">
                  <thead><tr className="bg-[#f7f7f7] text-[#666] border-b border-[#e0e0e0] select-none">
                    <th className="text-center px-2 py-1.5">번호</th>
                    <th onClick={() => lossSortClick('eleven_id')} className="text-left px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">아이디{lossArrow('eleven_id')}</th>
                    <th onClick={() => lossSortClick('product_no')} className="text-left px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">상품번호{lossArrow('product_no')}</th>
                    <th onClick={() => lossSortClick('seller_code')} className="text-left px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">판매자코드{lossArrow('seller_code')}</th>
                    <th onClick={() => lossSortClick('cost')} className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">광고비{lossArrow('cost')}</th>
                    <th onClick={() => lossSortClick('conv_amount')} title="광고센터(adoffice) 광고 전환매출 (직접+간접)" className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">광고전환매출{lossArrow('conv_amount')}</th>
                    <th onClick={() => lossSortClick('conv_roas_pct')} className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">광고전환ROAS{lossArrow('conv_roas_pct')}</th>
                    <th onClick={() => lossSortClick('sales')} title="실제 정산매출 (판매자코드 전역매칭, 광고 외 유입 포함)" className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">실매출{lossArrow('sales')}</th>
                    <th onClick={() => lossSortClick('roas_pct')} className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">실ROAS{lossArrow('roas_pct')}</th>
                    <th onClick={() => lossSortClick('clicks')} className="text-right px-2 py-1.5 cursor-pointer hover:text-[#1e6fd9]">클릭{lossArrow('clicks')}</th>
                    <th className="text-center px-2 py-1.5 align-top">
                      <span onClick={() => lossSortClick('status')} className="cursor-pointer hover:text-[#1e6fd9]">비고{lossArrow('status')}</span>
                      <select
                        value={lossStatusFilter}
                        onChange={e => setLossStatusFilter(e.target.value)}
                        className={`block mx-auto mt-1 border rounded px-1 py-0.5 text-[11px] font-normal ${lossStatusFilter ? 'border-[#1e6fd9] text-[#1e6fd9]' : 'border-[#ddd] text-[#666]'}`}
                      >
                        <option value="">전체 ({(lossData?.rows || []).length})</option>
                        {Object.keys(lossStatusCounts)
                          .sort((a, b) => (LOSS_STATUS_ORDER[a] ?? 99) - (LOSS_STATUS_ORDER[b] ?? 99))
                          .map(s => <option key={s} value={s}>{s} ({lossStatusCounts[s]})</option>)}
                      </select>
                    </th>
                  </tr></thead>
                  <tbody>
                    {lossSortedRows.map((r: any, i: number) => (
                      <tr key={i} className="border-b border-[#f0f0f0] hover:bg-[#fafafa]">
                        <td className="px-2 py-1.5 text-center text-[#999]">{i + 1}</td>
                        <td className="px-2 py-1.5 text-[#555]">{r.eleven_id}</td>
                        <td className="px-2 py-1.5 font-medium"><a href={`https://www.11st.co.kr/products/${r.product_no}`} target="_blank" rel="noreferrer" className="text-[#1e6fd9] hover:underline">{r.product_no}</a></td>
                        <td className="px-2 py-1.5 text-[#555]">{r.seller_code || '-'}</td>
                        <td className="px-2 py-1.5 text-right">{formatKRW(r.cost || 0)}</td>
                        <td className="px-2 py-1.5 text-right text-[#777]">{formatKRW(r.conv_amount || 0)}</td>
                        <td className="px-2 py-1.5 text-right">{r.conv_roas_pct ? `${Number(r.conv_roas_pct).toFixed(0)}%` : (r.cost ? '0%' : '-')}</td>
                        <td className="px-2 py-1.5 text-right font-medium">{formatKRW(r.sales || 0)}</td>
                        <td className="px-2 py-1.5 text-right font-semibold text-[#dc2626]">{r.roas_pct ? `${Number(r.roas_pct).toFixed(0)}%` : (r.cost ? '0%' : '-')}</td>
                        <td className="px-2 py-1.5 text-right">{(r.clicks || 0).toLocaleString()}</td>
                        <td className="px-2 py-1.5 text-center"><span className={r.status === '삭제완료' ? 'text-[#1e6fd9] font-bold' : (r.status === '삭제됨' || r.status === '판매금지') ? 'text-[#dc2626] font-semibold' : r.status === '중복등록' ? 'text-[#7c3aed] font-semibold' : r.status === '판매중' ? 'text-[#15803d]' : 'text-[#e08000]'} title={r.status === '중복등록' ? '같은 상품이 다른 코드로 판매중 — 삭제 제외' : r.status === '삭제완료' ? '삭제 처리 완료된 상품' : ''}>{r.status || '-'}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Card({ label, value, sub, valueClass }: { label: string; value: string; sub?: string; valueClass?: string }) {
  return (
    <div className="bg-white border border-[#e0e0e0] rounded px-3 py-2">
      <div className="text-[12px] text-[#888]">{label}{sub && <span className="ml-1 text-[#bbb]">{sub}</span>}</div>
      <div className={`text-[12px] md:text-[12px] font-bold ${valueClass || 'text-[#333]'}`}>{value}</div>
    </div>
  );
}
