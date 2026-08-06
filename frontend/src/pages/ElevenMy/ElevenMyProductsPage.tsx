import { useEffect, useState, useCallback } from 'react';
import { Sun, Moon, RefreshCw, Search, ChevronLeft, ChevronRight, Package, Star, AlertCircle, X, Zap, ChevronDown, ChevronUp, Download } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  fetchElevenMyProducts, fetchElevenMyAccounts, syncElevenMyProducts,
  exportElevenMyProducts, triggerIntegratedSync, triggerProductRecrawl,
  type ElevenAccountSummary,
} from '../../api/elevenMy';
import { fetchGmarketMyProducts, fetchGmarketMyAccounts, exportGmarketMyProducts } from '../../api/gmarketMy';
import { fetchAllMyProducts, type MyProductAllItem } from '../../api/myProductsAll';
import api from '../../api/client';
import { useTheme } from '../../hooks/useTheme';
import ElevenAccountSummaryCards from './ElevenAccountSummaryCards';

const PLATFORM_BADGE: Record<string, { label: string; color: string }> = {
  '11st': { label: '11번가', color: '#ff5a2e' },
  gmarket: { label: '지마켓', color: '#16a34a' },
  auction: { label: '옥션', color: '#db2777' },
  coupang: { label: '쿠팡', color: '#ef4444' },
  smartstore: { label: '스마트스토어', color: '#03c75a' },
  lotteon: { label: '롯데ON', color: '#da291c' },
};
function platformKey(p: MyProductAllItem): string {
  return p.platform === 'gmarket' && p.market === 'auction' ? 'auction' : p.platform;
}
// id는 11번가/지마켓 각각 별도 PK 시퀀스라 통합뷰에서는 충돌 가능 → 플랫폼+id 복합키 사용
function compositeKey(p: MyProductAllItem): string {
  return `${p.platform}:${p.id}`;
}

const PER_PAGE_OPTIONS = [50, 100, 200, 500, 1000];
const MAX_SELECT = 3000;   // 한 번에 선택 가능한 최대 상품 수

const STATUS_COLOR: Record<string, string> = {
  '판매중': '#16a34a', '품절': '#f59e0b', '판매종료': '#dc2626',
  '판매중지': '#6b7280', '판매금지': '#dc2626', '판매불가': '#dc2626', '재고부족': '#f59e0b',
};

function fmt(n: number | null | undefined): string {
  if (n == null) return '-';
  return n.toLocaleString();
}

export default function ElevenMyProductsPage() {
  const { dark, toggle } = useTheme();

  const bg = dark ? 'bg-[#0f1117]' : 'bg-[#f5f6fa]';
  const card = dark ? 'bg-[#1a1b23] border-[#2a2b35]' : 'bg-white border-[#e5e7eb]';
  const text1 = dark ? 'text-white' : 'text-gray-900';
  const text2 = dark ? 'text-gray-400' : 'text-gray-500';
  const text3 = dark ? 'text-gray-500' : 'text-gray-400';
  const inputBg = dark ? 'bg-[#0f1117] border-[#2a2b35] text-white' : 'bg-white border-gray-300 text-gray-900';
  const cardHover = dark ? 'hover:bg-[#2a2b35]' : 'hover:bg-gray-100';

  const [accounts, setAccounts] = useState<ElevenAccountSummary[]>([]);
  const [items, setItems] = useState<MyProductAllItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(50);
  const [pageInput, setPageInput] = useState('');
  const [platform, setPlatform] = useState<'all' | '11st' | 'gmarket'>('all');   // 쇼핑몰 선택
  const [accountId, setAccountId] = useState<number | undefined>(undefined);
  const [status, setStatus] = useState<string>('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [detailKey, setDetailKey] = useState<string | null>(null);
  const [detail, setDetail] = useState<MyProductAllItem | null>(null);
  const [cardsOpen, setCardsOpen] = useState(true);
  const [integratedRunning, setIntegratedRunning] = useState(false);
  const [integratedModalOpen, setIntegratedModalOpen] = useState(false);
  const [integratedTasks, setIntegratedTasks] = useState<Set<string>>(new Set(['products', 'office', 'grade', 'cost']));
  // 선택 계정 재크롤(대량엑셀)
  const [recrawlOpen, setRecrawlOpen] = useState(false);
  const [recrawlSel, setRecrawlSel] = useState<Set<string>>(new Set());
  const [recrawling, setRecrawling] = useState(false);
  // 상품 선택(엑셀 다운로드용) — 페이지 넘어가도 유지 (platform:id → 상품)
  const [selProd, setSelProd] = useState<Map<string, MyProductAllItem>>(new Map());
  // 정렬
  const [sortKey, setSortKey] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [needsCheck, setNeedsCheck] = useState(false);          // 확인필요(역마진)만 보기
  const [needsCheckTotal, setNeedsCheckTotal] = useState(0);    // 확인필요 건수(배지)
  const [allAccounts, setAllAccounts] = useState(false);        // 전체 계정 보기(집중관리 외 비집중 포함)
  const [dedup, setDedup] = useState(false);                    // 지마켓 중복(같은 판매자코드) 제외

  const loadAccounts = useCallback(async () => {
    if (platform === 'all') { setAccounts([]); return; }
    try {
      if (platform === 'gmarket') {
        const accs = await fetchGmarketMyAccounts();
        setAccounts(accs.map(a => ({
          account_id: a.account_id, login_id: a.login_id, seller_name: a.seller_name,
          product_count: a.product_count, has_api_key: true,
        })) as any);
      } else {
        const r = await fetchElevenMyAccounts(allAccounts);
        setAccounts(r.accounts);
      }
    } catch (e: any) {
      toast.error(`계정 로드 실패: ${e.message || e}`);
    }
  }, [platform, allAccounts]);

  const loadProducts = useCallback(async () => {
    setLoading(true);
    try {
      if (platform === 'all') {
        const r = await fetchAllMyProducts(page, perPage, status || undefined, search || undefined, sortKey || undefined, sortOrder, needsCheck, dedup);
        setItems(r.items);
        setTotal(r.total);
        setTotalPages(r.total_pages);
      } else if (platform === 'gmarket') {
        const r = await fetchGmarketMyProducts(page, perPage, accountId, undefined, status || undefined, search || undefined, sortKey || undefined, sortOrder, dedup);
        setItems(r.items.map(p => ({
          ...p, platform: 'gmarket', category: p.category_code, is_focused: null,
          status_label: p.status_type, purchase_cost: null, cost_diff: null,
        })) as any);
        setTotal(r.total);
        setTotalPages(r.total_pages);
      } else {
        const r = await fetchElevenMyProducts(page, perPage, accountId, status || undefined, search || undefined, !allAccounts, sortKey || undefined, sortOrder, needsCheck);
        setItems(r.items.map(p => ({
          ...p, platform: '11st', category: p.category_id, market: null, status_label: p.status_type,
        })) as any);
        setTotal(r.total);
        setTotalPages(r.total_pages);
        setNeedsCheckTotal(r.needs_check_total ?? 0);
      }
    } catch (e: any) {
      toast.error(`상품 로드 실패: ${e.message || e}`);
    } finally {
      setLoading(false);
    }
  }, [platform, page, perPage, accountId, status, search, sortKey, sortOrder, needsCheck, allAccounts, dedup]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortOrder(o => (o === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key); setSortOrder('asc');
    }
    setPage(1);
  };
  const sortArrow = (key: string) => (sortKey === key ? (sortOrder === 'asc' ? ' ▲' : ' ▼') : '');

  useEffect(() => { loadAccounts(); }, [loadAccounts]);
  useEffect(() => { loadProducts(); }, [loadProducts]);

  // 상세 모달 — 이미 로드된 행 데이터로 바로 표시(추가 fetch 불필요, 두 플랫폼 공통 필드로 충분)
  const openDetail = (p: MyProductAllItem) => { setDetailKey(compositeKey(p)); setDetail(p); };
  const closeDetail = () => { setDetailKey(null); setDetail(null); };

  const handleSync = async (singleAccountId?: number) => {
    setSyncing(true);
    const tid = toast.loading(singleAccountId ? '단일 계정 동기화 중...' : '집중관리 계정 일괄 동기화 중...');
    try {
      const r: any = await syncElevenMyProducts(singleAccountId);
      if (r.error) {
        toast.error(`동기화 실패: ${r.error}`, { id: tid });
      } else if (r.accounts) {
        const totalSynced = r.accounts.reduce((s: number, a: any) => s + (a.synced || 0), 0);
        const errs = r.accounts.filter((a: any) => a.error).length;
        toast.success(`동기화 완료: ${r.accounts.length}계정, ${fmt(totalSynced)}개 상품${errs > 0 ? ` (오류 ${errs})` : ''}`, { id: tid });
        if (r.skipped_no_api_key?.length) {
          toast(`API키 미설정 ${r.skipped_no_api_key.length}계정 스킵`, { icon: '⚠️' });
        }
      } else {
        toast.success(`${r.login_id || '동기화'}: ${fmt(r.synced || 0)}개`, { id: tid });
      }
      await loadAccounts();
      await loadProducts();
    } catch (e: any) {
      toast.error(`동기화 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    } finally {
      setSyncing(false);
    }
  };

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const openIntegratedSync = () => setIntegratedModalOpen(true);

  const toggleTask = (t: string) => {
    setIntegratedTasks(prev => {
      const n = new Set(prev);
      if (n.has(t)) n.delete(t); else n.add(t);
      return n;
    });
  };

  const runIntegratedSync = async () => {
    const tasks = Array.from(integratedTasks);
    if (tasks.length === 0) { toast.error('작업을 선택하세요'); return; }
    setIntegratedModalOpen(false);
    setIntegratedRunning(true);
    const tid = toast.loading('통합 동기화 시작 중...');
    try {
      const r = await triggerIntegratedSync(tasks);
      const started = (r.started || []).join(', ');
      toast.success(`통합 동기화 시작 — ${started || '없음'}`, { id: tid, duration: 4000 });
      toast('셀레늄 작업(등급/광고비/셀러오피스)은 백그라운드 진행 — 몇 분 후 새로고침하면 결과 반영', { duration: 5000 });
      await loadAccounts();
      await loadProducts();
    } catch (e: any) {
      toast.error(`통합 동기화 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    } finally {
      setIntegratedRunning(false);
    }
  };

  const toggleRecrawl = (loginId: string) => {
    setRecrawlSel(prev => {
      const n = new Set(prev);
      if (n.has(loginId)) n.delete(loginId); else n.add(loginId);
      return n;
    });
  };
  const allRecrawlSelected = accounts.length > 0 && recrawlSel.size === accounts.length;
  const toggleAllRecrawl = () => {
    setRecrawlSel(allRecrawlSelected ? new Set() : new Set(accounts.map(a => a.login_id)));
  };
  const startRecrawl = async () => {
    const ids = Array.from(recrawlSel);
    if (ids.length === 0) { toast.error('재크롤할 계정을 선택하세요'); return; }
    setRecrawling(true);
    const tid = toast.loading(`${ids.length}개 계정 등록상품 재크롤 시작 중...`);
    try {
      const r = await triggerProductRecrawl(ids);
      if (r.status === 'busy') {
        toast.error(r.error || '이미 다른 크롤러 실행 중', { id: tid });
      } else {
        toast.success(`재크롤 시작됨 — ${ids.length}개 계정 (백그라운드 진행, 몇 분 후 새로고침)`, { id: tid, duration: 5000 });
        setRecrawlOpen(false);
      }
    } catch (e: any) {
      toast.error(`재크롤 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    } finally {
      setRecrawling(false);
    }
  };

  const toggleProd = (p: MyProductAllItem) => {
    setSelProd(prev => {
      const n = new Map(prev);
      const k = compositeKey(p);
      if (n.has(k)) n.delete(k); else n.set(k, p);
      return n;
    });
  };
  // 선택 상품 삭제 — 검증(dry-run)/실삭제. 플랫폼별(11번가/지마켓) 셀러오피스에서 판매중지→재조회→삭제.
  // 통합뷰에서는 선택 항목이 두 플랫폼에 걸쳐있을 수 있어 플랫폼별로 그룹핑해 각각의 삭제 API를 호출한다.
  const deleteSelectedProducts = (real: boolean) => {
    const sel = Array.from(selProd.values());
    if (!sel.length) { toast.error('삭제할 상품을 선택하세요'); return; }
    const byPlatform: Record<string, Record<string, string[]>> = { '11st': {}, gmarket: {} };
    sel.forEach(p => {
      const lid = p.login_id;
      if (!lid) return;
      const grp = byPlatform[p.platform];
      (grp[lid] = grp[lid] || []).push(String(p.product_no));
    });
    const groups = (['11st', 'gmarket'] as const)
      .map(pf => ({ pf, byAcc: byPlatform[pf], accs: Object.keys(byPlatform[pf]) }))
      .filter(g => g.accs.length > 0);
    if (!groups.length) { toast.error('계정 정보 없음'); return; }
    const totalAccs = groups.reduce((s, g) => s + g.accs.length, 0);
    const mallNames = groups.map(g => (g.pf === 'gmarket' ? '지마켓' : '11번가')).join('+');
    if (real) {
      if (!window.confirm(`⚠️ 위험: 선택 ${sel.length}개를 ${mallNames}에서 실제·영구 삭제합니다(되돌릴 수 없음).\n\n먼저 [🔎 선택 검증]으로 확인하셨나요?\n검증을 안 하셨다면 [취소]하고 검증부터 하세요.\n\n검증을 마쳤고, 실제 삭제를 진행하시겠습니까?`)) return;
      if (!window.confirm(`최종 확인 ⚠️\n${sel.length}개(${totalAccs}계정) 상품을 ${mallNames}에서 영구 삭제합니다.\n정말 진행하시겠습니까?`)) return;
    } else {
      if (!window.confirm(`🔎 선택 ${sel.length}개(${totalAccs}계정) 삭제 검증(dry-run)\n셀러오피스 접속·상품번호 입력·조회·셀렉터를 확인합니다.\n실제 삭제는 하지 않습니다(안전). 진행할까요?`)) return;
    }
    const calls = groups.flatMap(g => {
      const url = g.pf === 'gmarket' ? '/cpc/gmarket/loss-products/delete/' : '/cpc/eleven-loss-products/delete/';
      return g.accs.map(eid => api.post(url, { eid, product_nos: g.byAcc[eid], ...(real ? { real: 1 } : {}) }));
    });
    Promise.all(calls)
      .then(() => toast.success(`${real ? '실삭제' : '검증(dry-run)'} 시작 — ${totalAccs}계정. 진행상황은 텔레그램/로그로 확인하세요.`))
      .catch((e: any) => toast.error(e?.response?.data?.message || e?.response?.data?.error || '시작 실패'));
  };
  // 선택 상품 판매중지(삭제 없음) — 품절 등 상태 무관하게 선택된 11번가 상품만 대상.
  // 지마켓 판매중지 API는 아직 검증 전이라 11번가만 지원(선택 중 지마켓 항목은 제외).
  const stopSelectedProducts = () => {
    const sel = Array.from(selProd.values()).filter(p => p.platform === '11st' && p.login_id);
    const skipped = selProd.size - sel.length;
    if (!sel.length) { toast.error('판매중지할 11번가 상품을 선택하세요(지마켓은 미지원)'); return; }
    const byAcc: Record<string, string[]> = {};
    sel.forEach(p => { (byAcc[p.login_id!] = byAcc[p.login_id!] || []).push(String(p.product_no)); });
    const accs = Object.keys(byAcc);
    if (!window.confirm(
      `선택 ${sel.length}개(${accs.length}계정)를 11번가에서 판매중지합니다.`
      + (skipped ? `\n(지마켓 ${skipped}개는 제외됨)` : '')
      + '\n삭제는 하지 않으며, 나중에 다시 판매중으로 되돌릴 수 있습니다.\n진행하시겠습니까?'
    )) return;
    Promise.all(accs.map(eid =>
      api.post('/cpc/eleven-loss-products/delete/', { eid, product_nos: byAcc[eid], stop_only: 1, real: 1 })
    ))
      .then(() => toast.success(`판매중지 시작 — ${accs.length}계정. 진행상황은 텔레그램/로그로 확인하세요.`))
      .catch((e: any) => toast.error(e?.response?.data?.message || e?.response?.data?.error || '시작 실패'));
  };
  // 선택 상품 실삭제(판매금지 전용) — 11번가에서 판매금지 상태인 상품을 영구 삭제.
  // 기존 "선택 삭제"와 동일한 API(real:1)를 쓰지만, 판매금지만 다루는 버튼임을 명확히 하고
  // 확인 문구도 그에 맞게 표시(다른 상태 상품이 섞여 선택돼도 그대로 삭제되니 사용 전 상태필터 확인 필요).
  const deleteBannedProducts = () => {
    const sel = Array.from(selProd.values()).filter(p => p.platform === '11st' && p.login_id);
    const skipped = selProd.size - sel.length;
    if (!sel.length) { toast.error('삭제할 11번가 상품을 선택하세요(지마켓은 미지원)'); return; }
    const byAcc: Record<string, string[]> = {};
    sel.forEach(p => { (byAcc[p.login_id!] = byAcc[p.login_id!] || []).push(String(p.product_no)); });
    const accs = Object.keys(byAcc);
    if (!window.confirm(
      `⚠️ 위험(판매금지 삭제): 선택 ${sel.length}개(${accs.length}계정)를 11번가에서 실제·영구 삭제합니다(되돌릴 수 없음).`
      + (skipped ? `\n(지마켓 ${skipped}개는 제외됨)` : '')
      + '\n\n상태필터가 "판매금지"로 맞춰져 있는지 다시 확인하세요. 진행하시겠습니까?'
    )) return;
    if (!window.confirm(`최종 확인 ⚠️\n${sel.length}개(${accs.length}계정) 상품을 영구 삭제합니다.\n정말 진행하시겠습니까?`)) return;
    Promise.all(accs.map(eid =>
      api.post('/cpc/eleven-loss-products/delete/', { eid, product_nos: byAcc[eid], real: 1 })
    ))
      .then(() => toast.success(`실삭제 시작 — ${accs.length}계정. 진행상황은 텔레그램/로그로 확인하세요.`))
      .catch((e: any) => toast.error(e?.response?.data?.message || e?.response?.data?.error || '시작 실패'));
  };
  const pageAllSelected = items.length > 0 && items.every(p => selProd.has(compositeKey(p)));
  const togglePageAll = () => {
    setSelProd(prev => {
      const n = new Map(prev);
      if (items.every(p => n.has(compositeKey(p)))) items.forEach(p => n.delete(compositeKey(p)));
      else items.forEach(p => n.set(compositeKey(p), p));
      return n;
    });
  };
  const [downloading, setDownloading] = useState(false);
  const [selecting, setSelecting] = useState(false);
  // 현재 필터(계정/상태/검색)에 맞는 검색결과 상위 MAX_SELECT개를 한 번에 선택 (페이지 넘김 불필요)
  const selectUpToMax = async () => {
    if (selecting) return;
    setSelecting(true);
    const tid = toast.loading(`검색결과 상위 ${fmt(MAX_SELECT)}개 불러오는 중...`);
    try {
      let fetched: MyProductAllItem[];
      let respTotal: number;
      if (platform === 'all') {
        const resp = await fetchAllMyProducts(1, MAX_SELECT, status || undefined, search || undefined, sortKey || undefined, sortOrder, needsCheck, dedup);
        fetched = resp.items; respTotal = resp.total;
      } else if (platform === 'gmarket') {
        const resp = await fetchGmarketMyProducts(1, MAX_SELECT, accountId, undefined, status || undefined, search || undefined, sortKey || undefined, sortOrder, dedup);
        fetched = resp.items.map(p => ({ ...p, platform: 'gmarket' as const, category: p.category_code, is_focused: null, status_label: p.status_type, purchase_cost: null, cost_diff: null })) as any;
        respTotal = resp.total;
      } else {
        const resp = await fetchElevenMyProducts(1, MAX_SELECT, accountId, status || undefined, search || undefined, !allAccounts, sortKey || undefined, sortOrder, needsCheck);
        fetched = resp.items.map(p => ({ ...p, platform: '11st' as const, category: p.category_id, market: null, status_label: p.status_type })) as any;
        respTotal = resp.total;
      }
      setSelProd(() => {
        const n = new Map<string, MyProductAllItem>();
        for (const p of fetched) {
          if (n.size >= MAX_SELECT) break;
          n.set(compositeKey(p), p);
        }
        return n;
      });
      const cnt = Math.min(fetched.length, MAX_SELECT);
      toast.success(
        `${fmt(cnt)}개 선택됨${respTotal > MAX_SELECT ? ` (전체 ${fmt(respTotal)}건 중 상위 ${fmt(MAX_SELECT)}개)` : ''}`,
        { id: tid },
      );
    } catch {
      toast.error('선택 실패', { id: tid });
    } finally {
      setSelecting(false);
    }
  };
  // 선택한 상품만 CSV로 다운로드 (이미 로드된 객체로 클라이언트에서 생성 — 선택 그대로 반영)
  const downloadSelectedExcel = () => {
    const sel = Array.from(selProd.values());
    if (!sel.length) { toast.error('선택된 상품이 없습니다'); return; }
    const header = ['플랫폼', '셀러', '로그인ID', '상품번호', '판매자상품코드', '상품명', '판매가', '재고', '판매상태', '카테고리', '마켓가', '차이'];
    const esc = (v: any) => {
      const s = v == null ? '' : String(v);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines = [header.join(',')];
    for (const p of sel) {
      lines.push([
        PLATFORM_BADGE[platformKey(p)]?.label ?? p.platform, p.seller_name ?? '', p.login_id ?? '', p.product_no ?? '',
        p.seller_product_code ?? '', p.product_name ?? '', p.sale_price ?? '',
        p.stock_quantity ?? '', p.status_label ?? p.status_type ?? '',
        p.category ?? '', p.purchase_cost ?? '', p.cost_diff ?? '',
      ].map(esc).join(','));
    }
    const blob = new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `나의상품_선택_${sel.length}건_${new Date().toLocaleDateString('sv')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`선택 ${fmt(sel.length)}건 엑셀(CSV) 다운로드`);
  };
  // 현재 필터(계정/상태/검색)에 맞는 '전체' 상품을 CSV로 다운로드 — 선택 불필요 (플랫폼 단일 선택 시에만 가능)
  const downloadAllExcel = async () => {
    if (downloading || platform === 'all') return;
    setDownloading(true);
    const tid = toast.loading(`전체 상품 다운로드 중... (${fmt(total)}건)`);
    try {
      const blob = platform === 'gmarket'
        ? await exportGmarketMyProducts(accountId, undefined, status || undefined, search || undefined, dedup)
        : await exportElevenMyProducts(accountId, status || undefined, search || undefined, sortKey || undefined, sortOrder);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `나의상품_전체_${new Date().toLocaleDateString('sv')}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`전체 ${fmt(total)}건 엑셀(CSV) 다운로드`, { id: tid });
    } catch (e) {
      toast.error('다운로드 실패', { id: tid });
    } finally {
      setDownloading(false);
    }
  };

  const totals = {
    balance: accounts.reduce((s, a) => s + (a.balance || 0), 0),
    cost30: accounts.reduce((s, a) => s + (a.cost_30days || 0), 0),
    products: accounts.reduce((s, a) => s + (a.product_count || 0), 0),
  };

  const lastSyncOverall = accounts.reduce((m: string | null, a) => {
    if (!a.last_synced) return m;
    if (!m) return a.last_synced;
    return a.last_synced > m ? a.last_synced : m;
  }, null);

  const focusedAccountsWithKey = accounts.filter(a => a.has_api_key);
  const noFocused = platform !== 'all' && accounts.length === 0;

  return (
    <div className={`min-h-screen ${bg}`}>
      <div className="max-w-[1600px] mx-auto px-4 md:px-6 py-4 space-y-3">
        <header className="flex items-center justify-between">
          <div>
            <h1 className={`text-2xl font-bold ${text1}`}>나의 상품</h1>
            <p className={`text-xs ${text3} mt-0.5`}>
              총 {fmt(total)}개
              {platform !== 'all' && lastSyncOverall && ` · 마지막 동기화 ${new Date(lastSyncOverall).toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}`}
              {platform !== 'all' && (<>{' · 집중관리 셀러 '}{accounts.length}개 (API키 등록 {focusedAccountsWithKey.length})</>)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => { loadAccounts(); loadProducts(); }} className={`p-2 rounded-lg ${cardHover}`}>
              <RefreshCw size={16} className={loading ? 'animate-spin text-blue-500' : text2} />
            </button>
            <button onClick={toggle} className={`p-2 rounded-lg ${cardHover} ${dark ? 'text-yellow-400' : 'text-gray-600'}`}>
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        {/* 계정 통합 요약 카드 (요청에 따라 숨김) */}
        <div hidden className={`rounded-xl border ${card} p-2.5`}>
          <button
            onClick={() => setCardsOpen(o => !o)}
            className={`w-full flex items-center justify-between text-left mb-${cardsOpen ? '2' : '0'}`}
          >
            <div className="flex items-center gap-3">
              <span className={`text-[12px] font-bold ${text1}`}>집중관리 계정 요약 ({accounts.length})</span>
              {!noFocused && (
                <span className={`text-[10px] ${text3}`}>
                  · 잔액합 {fmt(totals.balance)} · 30일 광고비 {fmt(totals.cost30)} · 상품 {fmt(totals.products)}개
                </span>
              )}
            </div>
            {cardsOpen ? <ChevronUp size={14} className={text2} /> : <ChevronDown size={14} className={text2} />}
          </button>
          {cardsOpen && (
            <ElevenAccountSummaryCards
              accounts={accounts}
              dark={dark}
              onSelectAccount={(id) => { setAccountId(id === accountId ? undefined : id); setPage(1); }}
              selectedAccountId={accountId}
            />
          )}
        </div>

        <div className={`flex flex-wrap items-center gap-2 rounded-xl border ${card} p-2.5`}>
          {platform !== 'all' && (
            <button
              onClick={openIntegratedSync}
              disabled={integratedRunning || accounts.length === 0}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-bold bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white disabled:opacity-40 shadow-md"
              title="등급+광고비+상품 통합 동기화"
            >
              <Zap size={13} className={integratedRunning ? 'animate-pulse' : ''} /> 통합 동기화 ({accounts.length})
            </button>
          )}

          {platform === '11st' && (
            <button
              onClick={() => handleSync(undefined)}
              disabled={syncing || focusedAccountsWithKey.length === 0}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-40"
              title={focusedAccountsWithKey.length === 0 ? 'API키 등록된 집중관리 계정 없음' : '상품만 동기화 (OpenAPI)'}
            >
              <RefreshCw size={13} className={syncing ? 'animate-spin' : ''} /> 상품만 ({focusedAccountsWithKey.length})
            </button>
          )}

          <select
            value={platform}
            onChange={e => { setPlatform(e.target.value as 'all' | '11st' | 'gmarket'); setAccountId(undefined); setPage(1); }}
            className={`px-2 py-2 rounded-lg border text-[12px] font-semibold ${inputBg}`}
            title="쇼핑몰 선택"
          >
            <option value="all">🗂 전체</option>
            <option value="11st">🛒 11번가</option>
            <option value="gmarket">🛍 지마켓/옥션</option>
          </select>

          {platform !== 'all' && (
            <select
              value={accountId ?? ''}
              onChange={e => { setAccountId(e.target.value ? Number(e.target.value) : undefined); setPage(1); }}
              className={`px-2 py-2 rounded-lg border text-[12px] ${inputBg}`}
            >
              <option value="">전체 계정</option>
              {accounts.map(a => (
                <option key={a.account_id} value={a.account_id}>
                  {a.login_id} ({a.seller_name || '-'}) · {a.product_count}개{a.has_api_key ? '' : ' [API키 미설정]'}
                </option>
              ))}
            </select>
          )}

          {platform === '11st' && accountId && (
            <button
              onClick={() => handleSync(accountId)}
              disabled={syncing}
              className="inline-flex items-center gap-1 px-3 py-2 rounded-lg text-[12px] font-semibold bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-40"
            >
              <RefreshCw size={12} /> 이 계정만
            </button>
          )}

          <select
            value={status}
            onChange={e => { setStatus(e.target.value); setPage(1); }}
            className={`px-2 py-2 rounded-lg border text-[12px] ${inputBg}`}
          >
            <option value="">전체 상태</option>
            <option value="판매중">판매중</option>
            <option value="판매중지">판매중지</option>
            <option value="품절">품절</option>
            {platform === '11st' && <option value="판매금지">판매금지</option>}
            {platform !== '11st' && <option value="판매불가">판매불가</option>}
            {platform !== '11st' && <option value="판매종료">판매종료</option>}
          </select>

          {platform === '11st' && (
            <label
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border text-[12px] font-semibold cursor-pointer ${allAccounts ? 'bg-blue-600 border-blue-600 text-white' : inputBg}`}
              title="집중관리(★) 외 비집중 계정까지 전부 표시"
            >
              <input
                type="checkbox"
                checked={allAccounts}
                onChange={e => { setAllAccounts(e.target.checked); setAccountId(undefined); setPage(1); }}
              />
              전체 계정
            </label>
          )}

          {(platform === '11st' || platform === 'all') && (
            <button
              onClick={() => { setNeedsCheck(v => !v); setPage(1); }}
              title="구매원가가 판매가보다 높은(역마진) 상품 — 11번가만 해당. 단위 불일치/원가 오류 등 확인 필요."
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border text-[12px] font-semibold ${
                needsCheck
                  ? 'bg-red-600 text-white border-red-600'
                  : `${inputBg} ${needsCheckTotal > 0 ? 'text-red-500 border-red-400' : ''}`
              }`}
            >
              ⚠ 확인필요{platform === '11st' && needsCheckTotal > 0 ? ` (${fmt(needsCheckTotal)})` : ''}
            </button>
          )}

          {(platform === 'gmarket' || platform === 'all') && (
            <label
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border text-[12px] font-semibold cursor-pointer ${dedup ? 'bg-blue-600 border-blue-600 text-white' : inputBg}`}
              title="같은 판매자코드(=같은 상품)가 여러 상품번호/마켓으로 등록된 지마켓/옥션 중복을 1개만 표시"
            >
              <input type="checkbox" checked={dedup} onChange={e => { setDedup(e.target.checked); setPage(1); }} />
              중복제외(지마켓)
            </label>
          )}

          {platform !== 'all' && (
            <button
              onClick={() => setRecrawlOpen(o => !o)}
              disabled={accounts.length === 0}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-40"
              title="계정 선택 후 등록상품(대량엑셀) 새로 크롤링"
            >
              <Package size={13} /> 등록상품 재크롤{recrawlSel.size > 0 ? ` (${recrawlSel.size})` : ''}
            </button>
          )}

          <button
            onClick={selectUpToMax}
            disabled={selecting}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-40"
            title={`현재 필터(계정/상태/검색)에 맞는 검색결과 상위 ${fmt(MAX_SELECT)}개를 한 번에 선택`}
          >
            {selecting ? '선택 중…' : `최대 ${fmt(MAX_SELECT)}개 선택`}
          </button>

          {selProd.size > 0 && (
            <>
              <button
                onClick={downloadSelectedExcel}
                title="선택한 상품만 CSV(엑셀)로 다운로드"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold bg-sky-600 hover:bg-sky-700 text-white"
              >
                <Download size={13} /> 선택 엑셀 다운로드 ({selProd.size})
              </button>
              <button
                onClick={() => deleteSelectedProducts(false)}
                title="선택 상품을 셀러오피스 셀렉터로 검증(실제 삭제 안 함)"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold bg-[#0369a1] hover:bg-[#075985] text-white"
              >
                🔎 선택 검증 ({selProd.size})
              </button>
              {Array.from(selProd.values()).some(p => p.platform === '11st') && (
                <button
                  onClick={stopSelectedProducts}
                  title="선택한 11번가 상품을 셀러오피스에서 판매중지(삭제 아님, 되돌릴 수 있음). 품절 상품 필터 후 전체선택하면 품절→판매중지로 사용 가능."
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold bg-amber-600 hover:bg-amber-700 text-white"
                >
                  🛑 선택 판매중지 ({Array.from(selProd.values()).filter(p => p.platform === '11st').length})
                </button>
              )}
              {Array.from(selProd.values()).some(p => p.platform === '11st') && (
                <button
                  onClick={deleteBannedProducts}
                  title="⚠️ 위험: 선택한 11번가 상품을 셀러오피스에서 실제 영구 삭제(판매금지 상품 전용). 상태필터=판매금지로 선택 후 사용하세요."
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-bold bg-rose-800 hover:bg-rose-900 text-white"
                >
                  🗑 판매금지 실삭제 ({Array.from(selProd.values()).filter(p => p.platform === '11st').length})
                </button>
              )}
              <button
                onClick={() => deleteSelectedProducts(true)}
                title="⚠️ 위험: 선택 상품을 셀러오피스에서 실제 영구 삭제(검증 후 진행)"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-bold bg-[#7f1d1d] hover:bg-[#601515] text-white"
              >
                🗑 선택 삭제 ({selProd.size})
              </button>
            </>
          )}

          <button
            onClick={downloadAllExcel}
            disabled={downloading || platform === 'all'}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold bg-teal-600 hover:bg-teal-700 text-white disabled:opacity-40"
            title={platform === 'all' ? '전체 다운로드는 플랫폼(11번가/지마켓)을 선택한 뒤 가능합니다' : '현재 필터(계정/상태/검색)에 맞는 전체 상품을 CSV로 다운로드 (선택 불필요)'}
          >
            <Download size={13} /> {downloading ? '다운로드 중…' : `전체 엑셀 다운로드 (${fmt(total)})`}
          </button>
          {selProd.size > 0 && (
            <button onClick={() => setSelProd(new Map())} className={`text-[11px] underline ${text3}`}>선택해제</button>
          )}

          <form onSubmit={submitSearch} className="relative ml-auto">
            <Search size={14} className={`absolute left-2.5 top-2.5 ${text3}`} />
            <input
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              placeholder="상품명/셀러상품코드..."
              className={`pl-8 pr-3 py-1.5 rounded-lg border text-[12px] w-64 ${inputBg}`}
            />
          </form>
        </div>

        {/* 등록상품 재크롤 — 계정 선택 패널 */}
        {platform !== 'all' && recrawlOpen && (
          <div className={`rounded-xl border ${card} p-3 space-y-2.5`}>
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-3">
                <span className={`text-[12px] font-bold ${text1}`}>등록상품 재크롤할 계정 선택</span>
                <label className={`flex items-center gap-1 text-[11px] ${text2} cursor-pointer`}>
                  <input type="checkbox" checked={allRecrawlSelected} onChange={toggleAllRecrawl} />
                  전체선택 ({recrawlSel.size}/{accounts.length})
                </label>
              </div>
              <button
                onClick={startRecrawl}
                disabled={recrawling || recrawlSel.size === 0}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-bold bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-40"
              >
                <RefreshCw size={12} className={recrawling ? 'animate-spin' : ''} /> 선택 {recrawlSel.size}개 재크롤 시작
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-1.5">
              {accounts.map(a => {
                const on = recrawlSel.has(a.login_id);
                return (
                  <label
                    key={a.account_id}
                    className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg border cursor-pointer text-[11px] ${on ? 'border-emerald-500 bg-emerald-500/10' : `${inputBg}`}`}
                  >
                    <input type="checkbox" checked={on} onChange={() => toggleRecrawl(a.login_id)} />
                    <span className={`truncate ${text1}`} title={`${a.seller_name} (${a.login_id})`}>
                      {a.seller_name || a.login_id}
                    </span>
                    <span className={`ml-auto ${text3}`}>{a.product_count}</span>
                  </label>
                );
              })}
            </div>
            <p className={`text-[10px] ${text3}`}>
              ※ 선택 계정의 등록상품을 대량엑셀로 새로 받아 나의상품에 저장합니다 (백그라운드, 계정당 ~1~2분). 다른 크롤러 실행 중이면 거부됩니다.
            </p>
          </div>
        )}

        <div className={`rounded-xl border ${card} overflow-hidden`}>
          {noFocused ? (
            <div className="p-12 text-center space-y-3">
              <AlertCircle size={32} className={`mx-auto ${text3}`} />
              <p className={`text-[12px] ${text2}`}>집중관리 ON 11번가 계정이 없습니다.</p>
              <p className={`text-[11px] ${text3}`}>ID 관리 페이지에서 11번가 계정에 별표(★)를 지정하고 API 키를 등록하세요.</p>
            </div>
          ) : loading ? (
            <div className="p-12 text-center">
              <RefreshCw size={20} className="animate-spin mx-auto text-blue-500" />
            </div>
          ) : items.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <Package size={32} className={`mx-auto ${text3}`} />
              <p className={`text-[12px] ${text2}`}>표시할 상품이 없습니다.</p>
              {platform === '11st' && <p className={`text-[11px] ${text3}`}>"일괄 동기화" 버튼을 눌러 11번가 API에서 상품을 가져오세요.</p>}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead className={`${dark ? 'bg-[#0f1117]' : 'bg-gray-50'} sticky top-0`}>
                  <tr className={text2}>
                    <th className="px-2 py-2 text-center font-medium w-8">
                      <input type="checkbox" checked={pageAllSelected} onChange={togglePageAll} title="이 페이지 전체선택" />
                    </th>
                    {platform === 'all' && <th className="px-3 py-2 text-left font-medium w-16">플랫폼</th>}
                    <th onClick={() => handleSort('seller_name')} className="px-3 py-2 text-left font-medium w-32 cursor-pointer select-none">셀러{sortArrow('seller_name')}</th>
                    <th className="px-3 py-2 text-left font-medium w-12">★</th>
                    <th className="px-3 py-2 text-left font-medium w-16">이미지</th>
                    <th onClick={() => handleSort('product_no')} className="px-3 py-2 text-left font-medium w-28 cursor-pointer select-none">상품번호{sortArrow('product_no')}</th>
                    <th onClick={() => handleSort('product_name')} className="px-3 py-2 text-left font-medium cursor-pointer select-none">상품명{sortArrow('product_name')}</th>
                    <th onClick={() => handleSort('sale_price')} className="px-3 py-2 text-right font-medium w-24 cursor-pointer select-none">판매가{sortArrow('sale_price')}</th>
                    <th onClick={() => handleSort('stock_quantity')} className="px-3 py-2 text-right font-medium w-16 cursor-pointer select-none">재고{sortArrow('stock_quantity')}</th>
                    <th onClick={() => handleSort('status_type')} className="px-3 py-2 text-center font-medium w-20 cursor-pointer select-none">상태{sortArrow('status_type')}</th>
                    <th onClick={() => handleSort('seller_product_code')} className="px-3 py-2 text-left font-medium w-28 cursor-pointer select-none">셀러코드{sortArrow('seller_product_code')}</th>
                    <th className="px-3 py-2 text-left font-medium w-24">카테고리</th>
                    <th onClick={() => handleSort('synced_at')} className="px-3 py-2 text-right font-medium w-28 cursor-pointer select-none">동기화{sortArrow('synced_at')}</th>
                    {platform !== 'all' && <th className="px-3 py-2 text-right font-medium w-24" title="예비상품(오너클랜) 마켓가(마켓실제판매가) — 판매자코드 매칭">마켓가</th>}
                    {platform !== 'all' && <th className="px-3 py-2 text-right font-medium w-24" title="판매가 - 마켓가">차이</th>}
                  </tr>
                </thead>
                <tbody className={`divide-y ${dark ? 'divide-[#2a2b35]' : 'divide-gray-100'}`}>
                  {items.map(p => {
                    const ck = compositeKey(p);
                    const badge = PLATFORM_BADGE[platformKey(p)];
                    return (
                    <tr key={ck} onClick={() => openDetail(p)} className={`${dark ? 'hover:bg-[#1f2029]' : 'hover:bg-gray-50'} cursor-pointer ${
                      selProd.has(ck) ? (dark ? 'bg-teal-900/20' : 'bg-teal-50')
                      : (p.cost_diff != null && p.cost_diff < 0) ? (dark ? 'bg-red-900/15' : 'bg-red-50') : ''
                    }`}>
                      <td className="px-2 py-1.5 text-center" onClick={e => e.stopPropagation()}>
                        <input type="checkbox" checked={selProd.has(ck)} onChange={() => toggleProd(p)} />
                      </td>
                      {platform === 'all' && (
                        <td className="px-3 py-1.5">
                          <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold"
                            style={{ backgroundColor: `${badge.color}20`, color: badge.color }}>
                            {badge.label}
                          </span>
                        </td>
                      )}
                      <td className={`px-3 py-1.5 ${text2} text-[11px]`}>
                        <div className="font-mono">{p.login_id}</div>
                        <div className={text3}>{p.seller_name || '-'}</div>
                      </td>
                      <td className="px-3 py-1.5">
                        {p.is_focused && <Star size={12} className="text-yellow-400" fill="currentColor" />}
                      </td>
                      <td className="px-3 py-1.5">
                        {p.product_image_url ? (
                          <img src={p.product_image_url} alt="" loading="lazy" className="w-9 h-9 rounded object-cover" />
                        ) : (
                          <div className={`w-9 h-9 rounded ${dark ? 'bg-[#0f1117]' : 'bg-gray-100'}`} />
                        )}
                      </td>
                      <td className={`px-3 py-1.5 font-mono text-[11px] ${text2}`}>{p.product_no}</td>
                      <td className={`px-3 py-1.5 ${text1} max-w-md truncate`} title={p.product_name}>{p.product_name || '-'}</td>
                      <td className={`px-3 py-1.5 text-right ${text1} font-semibold`}>{fmt(p.sale_price)}</td>
                      <td className={`px-3 py-1.5 text-right ${p.stock_quantity == null ? text3 : p.stock_quantity > 0 ? text2 : 'text-red-500 font-semibold'}`}>{fmt(p.stock_quantity)}</td>
                      <td className="px-3 py-1.5 text-center">
                        <span
                          className="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold"
                          style={{ backgroundColor: `${STATUS_COLOR[p.status_label] || '#94a3b8'}25`, color: STATUS_COLOR[p.status_label] || '#94a3b8' }}
                        >
                          {p.status_label || p.status_type || '-'}
                        </span>
                      </td>
                      <td className={`px-3 py-1.5 font-mono text-[10px] ${text3}`}>{p.seller_product_code || '-'}</td>
                      <td className={`px-3 py-1.5 font-mono text-[10px] ${text3}`}>{p.category || '-'}</td>
                      <td className={`px-3 py-1.5 text-right text-[10px] ${text3}`}>
                        {p.synced_at ? new Date(p.synced_at).toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}
                      </td>
                      {platform !== 'all' && (
                        <td className={`px-3 py-1.5 text-right ${text2}`}>{p.purchase_cost != null ? fmt(p.purchase_cost) : '-'}</td>
                      )}
                      {platform !== 'all' && (
                        <td className="px-3 py-1.5 text-right font-semibold">
                          {p.cost_diff != null ? (
                            <span className={p.cost_diff >= 0 ? 'text-emerald-500' : 'text-red-500'}>
                              {p.cost_diff > 0 ? '+' : ''}{fmt(p.cost_diff)}
                            </span>
                          ) : <span className={text3}>-</span>}
                        </td>
                      )}
                    </tr>
                  );})}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {totalPages > 1 && (
          <div className={`flex flex-wrap items-center justify-between gap-2 rounded-xl border ${card} px-3 py-2`}>
            <div className="flex items-center gap-1">
              <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className={`p-1.5 rounded ${cardHover} ${text2} disabled:opacity-30`}>
                <ChevronLeft size={14} />
              </button>
              <span className={`px-2 text-[11px] ${text2}`}>{page} / {totalPages}</span>
              <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page === totalPages} className={`p-1.5 rounded ${cardHover} ${text2} disabled:opacity-30`}>
                <ChevronRight size={14} />
              </button>
            </div>
            <div className="flex items-center gap-3">
              <form onSubmit={(e) => {
                e.preventDefault();
                const n = parseInt(pageInput, 10);
                if (!isNaN(n) && n >= 1 && n <= totalPages) { setPage(n); setPageInput(''); }
              }} className="flex items-center gap-1">
                <span className={`text-[11px] ${text3}`}>이동</span>
                <input
                  type="number" min={1} max={totalPages}
                  value={pageInput} onChange={e => setPageInput(e.target.value)}
                  placeholder={String(page)}
                  className={`w-14 px-2 py-1 text-[11px] rounded border text-center ${inputBg}`}
                />
              </form>
              <select value={perPage} onChange={e => { setPerPage(Number(e.target.value)); setPage(1); }} className={`px-2 py-1 text-[11px] rounded border ${inputBg}`}>
                {PER_PAGE_OPTIONS.map(n => <option key={n} value={n}>{n}개씩</option>)}
              </select>
            </div>
          </div>
        )}
      </div>

      {detailKey && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={closeDetail}>
          <div className={`relative w-full max-w-3xl rounded-2xl border ${card} shadow-2xl`} onClick={e => e.stopPropagation()}>
            <header className={`flex items-center justify-between px-5 py-3 border-b ${dark ? 'border-[#2a2b35]' : 'border-gray-200'}`}>
              <div className="flex items-center gap-3">
                <span className={`font-mono text-[12px] ${text2}`}>{detail ? detail.product_no : '불러오는 중…'}</span>
                <span className={`text-[11px] ${text3}`}>{detail?.login_id || ''}</span>
              </div>
              <button onClick={closeDetail} className={`p-1 rounded ${cardHover} ${text2}`}><X size={16} /></button>
            </header>
            {!detail ? (
              <div className="p-12 text-center"><RefreshCw size={20} className="animate-spin mx-auto text-blue-500" /></div>
            ) : (
            <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-1">
                {detail.product_image_url ? (
                  <img src={detail.product_image_url} alt="" className="w-full aspect-square rounded-lg object-contain bg-white" />
                ) : (
                  <div className={`aspect-square rounded-lg flex items-center justify-center ${dark ? 'bg-[#0f1117]' : 'bg-gray-100'}`}>
                    <Package size={40} className={text3} />
                  </div>
                )}
              </div>
              <div className="md:col-span-2 space-y-2 text-[12px]">
                <h3 className={`text-[12px] font-bold ${text1}`}>{detail.product_name}</h3>
                <Row k="플랫폼" v={PLATFORM_BADGE[platformKey(detail)]?.label ?? detail.platform} dark={dark} />
                <Row k="셀러" v={`${detail.login_id} (${detail.seller_name || '-'})`} dark={dark} />
                <Row k="판매가" v={`${fmt(detail.sale_price)}원`} dark={dark} />
                <Row k="재고" v={`${fmt(detail.stock_quantity)}개`} dark={dark} />
                <Row k="상태" v={`${detail.status_label || detail.status_type}`} dark={dark} />
                <Row k="셀러상품코드" v={detail.seller_product_code || '-'} dark={dark} />
                {detail.platform === '11st' && (
                  <>
                    <Row k="마켓가" v={detail.purchase_cost != null ? `${fmt(detail.purchase_cost)}원` : '-'} dark={dark} />
                    <Row k="차이(판매가-마켓가)" v={detail.cost_diff != null ? `${detail.cost_diff > 0 ? '+' : ''}${fmt(detail.cost_diff)}원` : '-'} dark={dark} />
                  </>
                )}
                <Row k="카테고리" v={detail.category || '-'} dark={dark} />
                <Row k="동기화" v={detail.synced_at ? new Date(detail.synced_at).toLocaleString('ko-KR') : '-'} dark={dark} />
              </div>
            </div>
            )}
          </div>
        </div>
      )}

      {integratedModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setIntegratedModalOpen(false)}>
          <div className={`relative w-full max-w-md rounded-2xl border shadow-2xl ${dark ? 'bg-[#1a1b23] border-[#2a2b35]' : 'bg-white border-gray-200'}`} onClick={e => e.stopPropagation()}>
            <div className={`px-5 py-3 border-b ${dark ? 'border-[#2a2b35]' : 'border-gray-200'}`}>
              <h3 className={`text-[12px] font-bold ${dark ? 'text-white' : 'text-gray-900'}`}>통합 동기화</h3>
              <p className={`text-[11px] mt-0.5 ${dark ? 'text-gray-400' : 'text-gray-500'}`}>{accounts.length}개 집중관리 계정 대상. 작업을 선택하세요.</p>
            </div>
            <div className="p-5 space-y-2">
              {[
                { v: 'products', l: '상품 (OpenAPI)', d: '집중관리 계정의 판매중 상품 동기화. 즉시 처리.' },
                { v: 'office', l: '셀러오피스 (잔액/상품/경고 등 14항목)', d: '셀레늄 로그인 → 메인 페이지 크롤. 분 단위 소요. 백그라운드.' },
                { v: 'grade', l: '등급 (셀레늄)', d: '셀러 등급 + 다음 등급까지 매출. 백그라운드.' },
                { v: 'cost', l: '광고비 거래내역 (셀레늄)', d: '셀러캐시/포인트 거래 + 잔액. 백그라운드.' },
              ].map(t => (
                <label key={t.v} className={`flex items-start gap-2 p-2 rounded-lg cursor-pointer ${dark ? 'hover:bg-[#0f1117]' : 'hover:bg-gray-50'}`}>
                  <input
                    type="checkbox"
                    checked={integratedTasks.has(t.v)}
                    onChange={() => toggleTask(t.v)}
                    className="mt-0.5 cursor-pointer accent-blue-600"
                  />
                  <div className="flex-1 min-w-0">
                    <div className={`text-[12px] font-semibold ${dark ? 'text-white' : 'text-gray-900'}`}>{t.l}</div>
                    <div className={`text-[10px] ${dark ? 'text-gray-400' : 'text-gray-500'}`}>{t.d}</div>
                  </div>
                </label>
              ))}
            </div>
            <div className={`flex items-center justify-end gap-2 px-5 py-3 border-t ${dark ? 'border-[#2a2b35]' : 'border-gray-200'}`}>
              <button
                onClick={() => setIntegratedModalOpen(false)}
                className={`px-3 py-1.5 rounded text-[12px] font-semibold ${dark ? 'bg-[#2a2b35] text-gray-300 hover:bg-[#353749]' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
              >
                취소
              </button>
              <button
                onClick={runIntegratedSync}
                className="px-4 py-1.5 rounded text-[12px] font-semibold bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white"
              >
                선택한 작업 시작 ({integratedTasks.size})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ k, v, dark }: { k: string; v: string; dark: boolean }) {
  const text2 = dark ? 'text-gray-400' : 'text-gray-500';
  const text1 = dark ? 'text-white' : 'text-gray-900';
  return (
    <div className="flex gap-3">
      <div className={`w-24 shrink-0 ${text2}`}>{k}</div>
      <div className={`${text1} break-all`}>{v}</div>
    </div>
  );
}
