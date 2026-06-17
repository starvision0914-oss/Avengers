import { useEffect, useState, useCallback, useRef } from 'react';
import { Sun, Moon, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  fetchProducts, fetchStats,
  uploadExcel, uploadCsv, uploadSoldoutTxt, syncProducts,
  downloadProductExcel, fetchWCodes,
  deleteAllProducts, deleteProductsByIds, dedupeByName,
  type KeywordProductItem, type ProductStats, type UploadTaskStart,
  type SortColumn, type SortOrder, type FilterableColumn,
} from '../../api/keyword';
import { useTheme } from '../../hooks/useTheme';
import { useUploadTaskPolling } from '../../hooks/useUploadTaskPolling';
import { themeStyles, fmt } from './constants';
import KeywordActionBar from './KeywordActionBar';
import KeywordProductsTable from './KeywordProductsTable';
import KeywordProductsGrid from './KeywordProductsGrid';
import KeywordProductDetailModal from './KeywordProductDetailModal';
import KeywordUploadProgress from './KeywordUploadProgress';
import KeywordWCodesModal from './KeywordWCodesModal';
import KeywordEmptyState from './KeywordEmptyState';
import KeywordConfirmModal from './KeywordConfirmModal';
import KeywordColumnFilterPopover from './KeywordColumnFilterPopover';
import { TableSkeleton, GridSkeleton } from './KeywordSkeleton';
import CodeSearchModal from '../../components/CodeSearchModal';

interface FilterState {
  saleStatus?: number;
  isSynced?: number;
  search: string;
  changedField?: string;
}

const PER_PAGE_OPTIONS = [50, 100, 200];

export default function KeywordProductsPage() {
  const { dark, toggle } = useTheme();
  const s = themeStyles(dark);

  const [view, setView] = useState<'table' | 'grid'>('table');
  const [filter, setFilter] = useState<FilterState>({ search: '' });
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(50);
  const [pageInput, setPageInput] = useState('');
  const [sort, setSort] = useState<SortColumn | undefined>(undefined);
  const [order, setOrder] = useState<SortOrder>('asc');

  const [products, setProducts] = useState<KeywordProductItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [stats, setStats] = useState<ProductStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);

  const [detailId, setDetailId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [confirmKind, setConfirmKind] = useState<null | 'all' | 'selected' | 'dedupe'>(null);
  const [deleting, setDeleting] = useState(false);
  const [filterCol, setFilterCol] = useState<FilterableColumn | undefined>(undefined);
  const [filterVals, setFilterVals] = useState<string[]>([]);
  const [filterPopover, setFilterPopover] = useState<{ col: FilterableColumn; label: string; anchor: DOMRect } | null>(null);
  const [uploadTaskId, setUploadTaskId] = useState<number | null>(null);
  const [uploadPct, setUploadPct] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [wcodes, setWcodes] = useState<string[] | null>(null);
  const [codeFilter, setCodeFilter] = useState<string[]>([]);
  const [codeModalOpen, setCodeModalOpen] = useState(false);
  const filterDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const uploadTask = useUploadTaskPolling(uploadTaskId);

  const reloadProducts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchProducts(
        page, perPage,
        filter.saleStatus, filter.isSynced, filter.search || undefined, filter.changedField,
        sort, order,
        filterCol, filterVals,
        codeFilter.length > 0 ? codeFilter : undefined,
      );
      setProducts(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (e: any) {
      toast.error(`상품 로드 실패: ${e.message || e}`);
    } finally {
      setLoading(false);
    }
  }, [page, perPage, filter, sort, order, filterCol, filterVals, codeFilter]);

  const toggleId = useCallback((id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const toggleAllOnPage = useCallback(() => {
    setSelectedIds(prev => {
      const allOnPage = products.every(p => prev.has(p.id));
      const next = new Set(prev);
      if (allOnPage) products.forEach(p => next.delete(p.id));
      else products.forEach(p => next.add(p.id));
      return next;
    });
  }, [products]);

  const performDelete = async () => {
    if (!confirmKind) return;
    setDeleting(true);
    const tid = toast.loading('처리 중...');
    try {
      let msg = '';
      if (confirmKind === 'all') {
        const r = await deleteAllProducts();
        msg = `전체 ${fmt(r.deleted)}건 삭제`;
      } else if (confirmKind === 'selected') {
        const ids = Array.from(selectedIds);
        const r = await deleteProductsByIds(ids);
        msg = `선택 ${fmt(r.deleted)}건 삭제`;
        setSelectedIds(new Set());
      } else if (confirmKind === 'dedupe') {
        const r = await dedupeByName();
        msg = `중복 ${fmt(r.deleted)}건 삭제 (높은가 ${fmt(r.higher_price_removed)} / 동가중복 ${fmt(r.same_price_removed)})`;
      }
      toast.success(msg, { id: tid });
      setConfirmKind(null);
      await Promise.all([reloadProducts(), reloadStats()]);
    } catch (e: any) {
      toast.error(`처리 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    } finally {
      setDeleting(false);
    }
  };

  const handleSort = useCallback((col: SortColumn) => {
    if (sort === col) {
      setOrder(o => (o === 'asc' ? 'desc' : 'asc'));
    } else {
      setSort(col);
      setOrder('asc');
    }
    setPage(1);
  }, [sort]);

  const reloadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const st = await fetchStats().catch(() => null);
      setStats(st);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => { reloadProducts(); }, [reloadProducts]);
  useEffect(() => { reloadStats(); }, [reloadStats]);

  // 필터 변경 시 page 1로
  useEffect(() => {
    if (filterDebounceRef.current) clearTimeout(filterDebounceRef.current);
    filterDebounceRef.current = setTimeout(() => setPage(1), 0);
  }, [filter]);

  // 업로드 task가 done 되면 자동 새로고침
  useEffect(() => {
    if (uploadTask?.status === 'done') {
      const r = uploadTask.result_data || {};
      toast.success(`업로드 완료 — 추가 ${fmt(r.inserted || 0)} / 업데이트 ${fmt(r.updated || 0)} / 스킵 ${fmt(r.skipped || 0)}`);
      reloadProducts();
      reloadStats();
    } else if (uploadTask?.status === 'error') {
      toast.error(`업로드 실패: ${uploadTask.result_data?.error || '알 수 없는 오류'}`);
    }
  }, [uploadTask?.status, reloadProducts, reloadStats]);

  const handleExcelUpload = async (file: File) => {
    setBusy(true);
    setUploadPct(0);
    const tid = toast.loading(`${file.name} 업로드 중...`);
    try {
      const res: UploadTaskStart = await uploadExcel(file, (pct) => setUploadPct(pct));
      setUploadTaskId(res.task_id);
      toast.success('업로드 시작 — 진행률을 표시합니다', { id: tid });
    } catch (e: any) {
      toast.error(`업로드 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    } finally {
      setBusy(false);
      setTimeout(() => setUploadPct(null), 500);
    }
  };

  const handleCsvUpload = async (file: File) => {
    setBusy(true);
    const tid = toast.loading('CSV 처리 중...');
    try {
      const res = await uploadCsv(file);
      toast.success(`CSV 업로드 완료 — ${fmt(res.updated)}개 업데이트`, { id: tid });
      await Promise.all([reloadProducts(), reloadStats()]);
    } catch (e: any) {
      toast.error(`CSV 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    } finally {
      setBusy(false);
    }
  };

  const handleSoldoutUpload = async (file: File) => {
    setBusy(true);
    const tid = toast.loading('품절 TXT 처리 중...');
    try {
      const res = await uploadSoldoutTxt(file);
      toast.success(`품절 처리 완료 — ${fmt(res.ownerclan_updated)}건 업데이트`, { id: tid });
      await Promise.all([reloadProducts(), reloadStats()]);
    } catch (e: any) {
      toast.error(`품절 TXT 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    } finally {
      setBusy(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    const tid = toast.loading('동기화 처리 중...');
    try {
      const res = await syncProducts();
      toast.success(`동기화 완료 — ${fmt(res.synced)}건`, { id: tid });
      await Promise.all([reloadProducts(), reloadStats()]);
    } catch (e: any) {
      toast.error(`동기화 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    } finally {
      setSyncing(false);
    }
  };

  const handleExcelDownload = async () => {
    const tid = toast.loading('엑셀 다운로드 준비 중...');
    try {
      await downloadProductExcel({
        saleStatus: filter.saleStatus,
        isSynced: filter.isSynced,
        search: filter.search || undefined,
        changedField: filter.changedField,
      });
      toast.success('다운로드 완료', { id: tid });
    } catch (e: any) {
      toast.error(`다운로드 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    }
  };

  const handleWCodes = async () => {
    const tid = toast.loading('W코드 추출 중...');
    try {
      const codes = await fetchWCodes({
        saleStatus: filter.saleStatus,
        isSynced: filter.isSynced,
        search: filter.search || undefined,
        changedField: filter.changedField,
      });
      setWcodes(codes);
      toast.success(`${fmt(codes.length)}개 추출`, { id: tid });
    } catch (e: any) {
      toast.error(`추출 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    }
  };

  const isEmpty = !loading && total === 0 && !filter.saleStatus && !filter.isSynced && !filter.search && !filter.changedField;

  return (
    <div className={`min-h-screen ${s.bg} transition-colors duration-300`}>
      <div className="max-w-[1600px] mx-auto px-4 md:px-6 py-4 space-y-4">

        <header className="flex items-center justify-between">
          <div>
            <h1 className={`text-2xl font-bold ${s.text1}`}>키워드추출기</h1>
            <p className={`text-xs ${s.text3} mt-0.5`}>
              총 {fmt(total)}개
              {stats?.changed ? ` · 변경 ${fmt(stats.changed)}개` : ''}
              {stats?.unsynced ? ` · 미동기화 ${fmt(stats.unsynced)}개` : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => { reloadProducts(); reloadStats(); }}
              className={`p-2 rounded-lg ${dark ? 'hover:bg-[#2a2b35]' : 'hover:bg-gray-100'}`}
            >
              <RefreshCw size={16} className={loading ? 'animate-spin text-blue-500' : s.text2} />
            </button>
            <button
              onClick={toggle}
              className={`p-2 rounded-lg ${dark ? 'hover:bg-[#2a2b35] text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        {(uploadTaskId || uploadPct != null) && (
          <KeywordUploadProgress
            dark={dark}
            task={uploadTask}
            uploadPct={uploadPct}
            onClose={() => { setUploadTaskId(null); setUploadPct(null); }}
          />
        )}
        <KeywordActionBar
          dark={dark}
          view={view}
          onViewChange={setView}
          onExcelUpload={handleExcelUpload}
          onCsvUpload={handleCsvUpload}
          onSoldoutUpload={handleSoldoutUpload}
          onSync={handleSync}
          onExcelDownload={handleExcelDownload}
          onWCodes={handleWCodes}
          onDeleteAll={() => setConfirmKind('all')}
          onDeleteSelected={() => setConfirmKind('selected')}
          onDedupe={() => setConfirmKind('dedupe')}
          onCodeSearch={() => setCodeModalOpen(true)}
          codeSearchCount={codeFilter.length}
          selectedCount={selectedIds.size}
          busy={busy}
          syncing={syncing}
        />

        <div className="space-y-3">
          {isEmpty ? (
            <KeywordEmptyState dark={dark} onUploadClick={() => {
              const inp = document.querySelector<HTMLInputElement>('input[type="file"][accept=".xlsx,.zip"]');
              inp?.click();
            }} />
          ) : loading ? (
            view === 'table' ? <TableSkeleton dark={dark} /> : <GridSkeleton dark={dark} />
          ) : products.length === 0 ? (
            <div className={`rounded-xl border ${s.card} p-12 text-center`}>
              <div className={`text-[12px] ${s.text2} mb-2`}>조건에 맞는 상품이 없습니다.</div>
              <button
                onClick={() => setFilter({ search: '' })}
                className="text-[12px] text-blue-500 hover:underline"
              >
                초기화
              </button>
            </div>
          ) : view === 'table' ? (
            <KeywordProductsTable
              dark={dark}
              items={products}
              onSelect={setDetailId}
              sort={sort}
              order={order}
              onSort={handleSort}
              selectedIds={selectedIds}
              onToggleId={toggleId}
              onToggleAll={toggleAllOnPage}
              filterCol={filterCol}
              filterVals={filterVals}
              onOpenFilter={(col, label, anchor) => setFilterPopover({ col, label, anchor })}
            />
          ) : (
            <KeywordProductsGrid dark={dark} items={products} onSelect={setDetailId} />
          )}

          {totalPages > 1 && (
            <Pagination
              dark={dark}
              page={page}
              totalPages={totalPages}
              perPage={perPage}
              onPage={setPage}
              onPerPage={setPerPage}
              pageInput={pageInput}
              onPageInputChange={setPageInput}
            />
          )}
        </div>
      </div>

      <KeywordProductDetailModal
        dark={dark}
        productId={detailId}
        onClose={() => setDetailId(null)}
      />
      <KeywordWCodesModal dark={dark} codes={wcodes} onClose={() => setWcodes(null)} />

      <CodeSearchModal
        dark={dark}
        open={codeModalOpen}
        title="W코드 대량검색 (키워드추출기)"
        initialCodes={codeFilter}
        onClose={() => setCodeModalOpen(false)}
        onSubmit={(codes) => { setCodeFilter(codes); setPage(1); toast.success(`${codes.length}개 코드로 검색합니다`); }}
        onClear={() => { setCodeFilter([]); setPage(1); }}
      />

      <KeywordColumnFilterPopover
        dark={dark}
        open={filterPopover !== null}
        column={filterPopover?.col || 'category_name'}
        columnLabel={filterPopover?.label || ''}
        selectedValues={filterPopover && filterCol === filterPopover.col ? filterVals : []}
        anchorRect={filterPopover?.anchor || null}
        onApply={(vals) => {
          if (vals.length === 0) {
            setFilterCol(undefined);
            setFilterVals([]);
          } else if (filterPopover) {
            setFilterCol(filterPopover.col);
            setFilterVals(vals);
          }
          setPage(1);
        }}
        onClose={() => setFilterPopover(null)}
      />

      <KeywordConfirmModal
        dark={dark}
        open={confirmKind !== null}
        busy={deleting}
        title={
          confirmKind === 'all' ? '전체 키워드추출기 항목을 삭제할까요?'
          : confirmKind === 'selected' ? `선택한 ${selectedIds.size}개를 삭제할까요?`
          : confirmKind === 'dedupe' ? '상품명 중복을 삭제할까요?'
          : ''
        }
        message={
          confirmKind === 'all'
            ? `현재 DB의 모든 키워드추출기 항목(${fmt(total)}개)을 영구 삭제합니다.\n이 작업은 되돌릴 수 없습니다.`
          : confirmKind === 'selected'
            ? `선택된 ${selectedIds.size}개 항목을 영구 삭제합니다.\n이 작업은 되돌릴 수 없습니다.`
          : confirmKind === 'dedupe'
            ? '상품명이 같은 상품들 중에서 판매가가 더 높은 상품을 삭제합니다.\n(가장 낮은 가격의 상품 1개씩만 보존됩니다.)\n이 작업은 되돌릴 수 없습니다.'
          : ''
        }
        confirmLabel={confirmKind === 'dedupe' ? '중복 삭제' : '삭제'}
        variant={confirmKind === 'dedupe' ? 'warning' : 'danger'}
        onConfirm={performDelete}
        onCancel={() => setConfirmKind(null)}
      />
    </div>
  );
}

function Pagination({
  dark, page, totalPages, perPage, onPage, onPerPage, pageInput, onPageInputChange,
}: {
  dark: boolean; page: number; totalPages: number; perPage: number;
  onPage: (n: number) => void; onPerPage: (n: number) => void;
  pageInput: string; onPageInputChange: (v: string) => void;
}) {
  const s = themeStyles(dark);
  const start = Math.max(1, Math.min(page - 4, totalPages - 8));
  const end = Math.min(totalPages, start + 8);
  const pages: number[] = [];
  for (let i = start; i <= end; i++) pages.push(i);

  const submitJump = (e: React.FormEvent) => {
    e.preventDefault();
    const n = parseInt(pageInput, 10);
    if (!isNaN(n) && n >= 1 && n <= totalPages) {
      onPage(n);
      onPageInputChange('');
    }
  };

  return (
    <div className={`flex flex-wrap items-center justify-between gap-2 rounded-xl border ${s.card} px-3 py-2`}>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPage(Math.max(1, page - 1))}
          disabled={page === 1}
          className={`p-1.5 rounded ${s.cardHover} ${s.text2} disabled:opacity-30`}
        >
          <ChevronLeft size={14} />
        </button>
        {start > 1 && <span className={`px-2 text-[11px] ${s.text3}`}>...</span>}
        {pages.map(p => (
          <button
            key={p}
            onClick={() => onPage(p)}
            className={`min-w-[28px] px-2 py-1 rounded text-[11px] font-semibold ${
              p === page ? 'bg-blue-600 text-white' : `${s.text2} ${s.cardHover}`
            }`}
          >
            {p}
          </button>
        ))}
        {end < totalPages && <span className={`px-2 text-[11px] ${s.text3}`}>...</span>}
        <button
          onClick={() => onPage(Math.min(totalPages, page + 1))}
          disabled={page === totalPages}
          className={`p-1.5 rounded ${s.cardHover} ${s.text2} disabled:opacity-30`}
        >
          <ChevronRight size={14} />
        </button>
      </div>

      <div className="flex items-center gap-3">
        <form onSubmit={submitJump} className="flex items-center gap-1">
          <span className={`text-[11px] ${s.text3}`}>페이지</span>
          <input
            type="number"
            min={1}
            max={totalPages}
            value={pageInput}
            onChange={(e) => onPageInputChange(e.target.value)}
            placeholder={String(page)}
            className={`w-14 px-2 py-1 text-[11px] rounded border text-center ${s.inputBg}`}
          />
          <span className={`text-[11px] ${s.text3}`}>/ {totalPages}</span>
        </form>
        <select
          value={perPage}
          onChange={(e) => onPerPage(Number(e.target.value))}
          className={`px-2 py-1 text-[11px] rounded border ${s.inputBg}`}
        >
          {PER_PAGE_OPTIONS.map(n => (
            <option key={n} value={n}>{n}개씩</option>
          ))}
        </select>
      </div>
    </div>
  );
}
