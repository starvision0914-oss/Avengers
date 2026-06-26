import { useState, useCallback } from 'react';
import { RefreshCw, Download, Search, AlertTriangle } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';
import {
  getProducts, syncProducts, downloadProductExcel,
  previewSuspend, suspendProducts,
  type SmartStoreAccount, type SmartStoreProduct,
} from '../../api/smartstore';

const STATUS_LABEL: Record<string, string> = {
  SALE: '판매중', SUSPENSION: '판매중지', OUTOFSTOCK: '품절',
  WAIT: '대기', PROHIBITION: '금지', CLOSE: '종료',
};
const STATUS_COLOR: Record<string, string> = {
  SALE: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  SUSPENSION: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  OUTOFSTOCK: 'bg-orange-100 text-orange-800',
  PROHIBITION: 'bg-red-100 text-red-800',
  CLOSE: 'bg-gray-100 text-gray-500',
};

interface Props {
  accounts: SmartStoreAccount[];
}

export default function SmartStoreProductsTab({ accounts }: Props) {
  const { dark } = useTheme();
  const [accountId, setAccountId] = useState<number | string>(0);
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [ownerclanFilter, setOwnerclanFilter] = useState('');
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<SmartStoreProduct[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState<number | null>(null);
  const [syncMsg, setSyncMsg] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [selectAll, setSelectAll] = useState(false);
  const [suspendModal, setSuspendModal] = useState<null | { total_count: number; by_store: { store_name: string; count: number }[]; w_codes: string[] }>(null);
  const [suspending, setSuspending] = useState(false);

  const card = dark ? 'bg-[#1a1d27] border-[#2d3144]' : 'bg-white border-gray-200';
  const inp = dark ? 'bg-[#2d3144] border-[#3d4464] text-gray-100' : 'bg-gray-50 border-gray-200 text-gray-800';
  const text2 = dark ? 'text-gray-400' : 'text-gray-500';
  const hdr = dark ? 'bg-[#13151f] text-gray-400' : 'bg-gray-50 text-gray-500';

  const load = useCallback(async (p = page) => {
    setLoading(true);
    try {
      const res = await getProducts({
        account_id: accountId || 0,
        page: p, per_page: 50,
        status: status || undefined,
        search: search || undefined,
        ownerclan_soldout: ownerclanFilter || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
      setSelectedIds(new Set());
      setSelectAll(false);
    } finally {
      setLoading(false);
    }
  }, [accountId, status, search, ownerclanFilter, page]);

  const applySearch = () => {
    setSearch(searchInput);
    setPage(1);
    load(1);
  };

  const handleSync = async (aid: number) => {
    setSyncing(aid);
    setSyncMsg('');
    try {
      const res = await syncProducts(aid);
      setSyncMsg(`동기화 완료: ${res.synced}개 (${res.store_name})`);
      load(1);
    } catch (e: any) {
      setSyncMsg(`오류: ${e?.response?.data?.error || e.message}`);
    } finally {
      setSyncing(null);
    }
  };

  const handleExcel = () => downloadProductExcel({
    account_ids: accountId ? [Number(accountId)] : undefined,
    statuses: status ? [status] : undefined,
  });

  const toggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handlePreviewSuspend = async () => {
    const result = await previewSuspend(
      [...selectedIds], selectAll,
      { account_id: Number(accountId) || 0, status, search, ownerclan_soldout: ownerclanFilter === '1' || undefined },
    );
    setSuspendModal(result);
  };

  const handleSuspend = async () => {
    setSuspending(true);
    try {
      const result = await suspendProducts(
        [...selectedIds], selectAll,
        { account_id: Number(accountId) || 0, status, search, ownerclan_soldout: ownerclanFilter === '1' || undefined },
      );
      alert(`품절처리 완료: 성공 ${result.success_count}개, 실패 ${result.fail_count}개`);
      setSuspendModal(null);
      load(1);
    } finally {
      setSuspending(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 도구 모음 */}
      <div className={`${card} border rounded-xl p-4`}>
        <div className="flex flex-wrap gap-3 items-center">
          {/* 계정 선택 */}
          <select
            className={`px-3 py-2 rounded-lg border text-sm ${inp}`}
            value={accountId}
            onChange={e => { setAccountId(e.target.value ? Number(e.target.value) : 0); setPage(1); }}
          >
            <option value={0}>전체 스토어</option>
            {accounts.map(a => (
              <option key={a.id} value={a.id}>{a.display_name || a.store_name}</option>
            ))}
          </select>

          {/* 상태 필터 */}
          <select className={`px-3 py-2 rounded-lg border text-sm ${inp}`} value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}>
            <option value="">전체 상태</option>
            {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>

          {/* 오너클랜 필터 */}
          <select className={`px-3 py-2 rounded-lg border text-sm ${inp}`} value={ownerclanFilter} onChange={e => { setOwnerclanFilter(e.target.value); setPage(1); }}>
            <option value="">전체</option>
            <option value="1">오너클랜 품절</option>
            <option value="0">정상</option>
          </select>

          {/* 검색 */}
          <div className="flex gap-1 flex-1">
            <input
              className={`flex-1 px-3 py-2 rounded-lg border text-sm ${inp}`}
              placeholder="상품명 / 판매자코드 검색"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && applySearch()}
            />
            <button onClick={applySearch} className="px-3 py-2 rounded-lg bg-[#03C75A] text-white">
              <Search size={15} />
            </button>
          </div>

          <button onClick={() => load(1)} disabled={loading} className={`px-3 py-2 rounded-lg border text-sm ${inp} flex items-center gap-1`}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> 조회
          </button>
          <button onClick={handleExcel} className={`px-3 py-2 rounded-lg border text-sm ${inp} flex items-center gap-1`}>
            <Download size={14} /> 엑셀
          </button>
        </div>

        {/* API 동기화 버튼들 */}
        {accountId !== 0 && accountId !== '' && (
          <div className="mt-3 flex items-center gap-3">
            <button
              onClick={() => handleSync(Number(accountId))}
              disabled={syncing !== null}
              className="px-4 py-1.5 rounded-lg bg-blue-500 text-white text-sm flex items-center gap-1.5"
            >
              <RefreshCw size={13} className={syncing === accountId ? 'animate-spin' : ''} />
              네이버 API 동기화
            </button>
            {syncMsg && <span className={`text-sm ${syncMsg.startsWith('오류') ? 'text-red-400' : 'text-[#03C75A]'}`}>{syncMsg}</span>}
          </div>
        )}
      </div>

      {/* 품절처리 도구 */}
      {(selectedIds.size > 0 || selectAll) && (
        <div className={`${card} border border-orange-500/30 rounded-xl p-3 flex items-center gap-3`}>
          <AlertTriangle size={16} className="text-orange-400" />
          <span className="text-sm">{selectAll ? '전체' : selectedIds.size}개 선택됨</span>
          <button
            onClick={handlePreviewSuspend}
            className="px-3 py-1.5 rounded-lg bg-orange-500 text-white text-sm"
          >
            W코드 품절처리 미리보기
          </button>
        </div>
      )}

      {/* 총 건수 */}
      <div className={`text-sm ${text2}`}>총 {total.toLocaleString()}개 상품</div>

      {/* 상품 테이블 */}
      <div className={`${card} border rounded-xl overflow-hidden`}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className={`${hdr} border-b ${dark ? 'border-[#2d3144]' : 'border-gray-200'}`}>
                <th className="px-3 py-2.5 text-left w-8">
                  <input type="checkbox" checked={selectAll} onChange={e => { setSelectAll(e.target.checked); if (!e.target.checked) setSelectedIds(new Set()); }} />
                </th>
                <th className="px-3 py-2.5 text-left">스토어</th>
                <th className="px-3 py-2.5 text-left">상품번호</th>
                <th className="px-3 py-2.5 text-left min-w-[200px]">상품명</th>
                <th className="px-3 py-2.5 text-right">판매가</th>
                <th className="px-3 py-2.5 text-right">재고</th>
                <th className="px-3 py-2.5 text-center">상태</th>
                <th className="px-3 py-2.5 text-left">판매자코드</th>
                <th className="px-3 py-2.5 text-center">오너클랜</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={9} className="text-center py-10 text-gray-400">불러오는 중...</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={9} className="text-center py-10 text-gray-400">조회 버튼을 눌러 상품을 불러오세요</td></tr>
              ) : items.map(p => (
                <tr key={p.id} className={`border-b ${dark ? 'border-[#2d3144] hover:bg-[#2d3144]/40' : 'border-gray-100 hover:bg-gray-50'}`}>
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selectAll || selectedIds.has(p.id)}
                      onChange={() => { setSelectAll(false); toggleSelect(p.id); }}
                    />
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-400">{p.store_name}</td>
                  <td className="px-3 py-2 text-xs font-mono">{p.product_no}</td>
                  <td className="px-3 py-2 max-w-[250px]">
                    <div className="truncate text-xs">{p.name}</div>
                  </td>
                  <td className="px-3 py-2 text-right text-xs">{p.sale_price.toLocaleString()}원</td>
                  <td className="px-3 py-2 text-right text-xs">{p.stock_quantity}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLOR[p.status_type] || 'bg-gray-100 text-gray-500'}`}>
                      {STATUS_LABEL[p.status_type] || p.status_type}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs font-mono text-gray-400">{p.seller_management_code}</td>
                  <td className="px-3 py-2 text-center">
                    {p.ownerclan_soldout && <span className="text-xs text-orange-400">품절</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 페이지네이션 */}
        {totalPages > 1 && (
          <div className="flex justify-center gap-1 p-3">
            <button onClick={() => { setPage(p => Math.max(1, p - 1)); load(Math.max(1, page - 1)); }}
              disabled={page <= 1} className={`px-3 py-1 rounded text-sm ${page <= 1 ? 'opacity-40' : ''} ${inp} border`}>
              이전
            </button>
            <span className={`px-3 py-1 text-sm ${text2}`}>{page} / {totalPages}</span>
            <button onClick={() => { setPage(p => Math.min(totalPages, p + 1)); load(Math.min(totalPages, page + 1)); }}
              disabled={page >= totalPages} className={`px-3 py-1 rounded text-sm ${page >= totalPages ? 'opacity-40' : ''} ${inp} border`}>
              다음
            </button>
          </div>
        )}
      </div>

      {/* 품절처리 확인 모달 */}
      {suspendModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className={`${dark ? 'bg-[#1a1d27]' : 'bg-white'} rounded-2xl p-6 max-w-md w-full mx-4`}>
            <h3 className="font-bold text-lg mb-3 text-orange-400">품절처리 확인</h3>
            <p className="text-sm mb-2">아래 상점의 상품이 판매중지(SUSPENSION) 처리됩니다:</p>
            <div className="space-y-1 mb-4">
              {suspendModal.by_store.map(s => (
                <div key={s.store_name} className={`flex justify-between text-sm px-3 py-1.5 rounded ${dark ? 'bg-[#2d3144]' : 'bg-gray-50'}`}>
                  <span>{s.store_name}</span>
                  <span className="font-bold">{s.count}개</span>
                </div>
              ))}
              {suspendModal.total_count === 0 && (
                <p className="text-sm text-gray-400">처리 대상 없음 (W코드 + 오너클랜품절 + 판매중 조건 미충족)</p>
              )}
            </div>
            <p className="text-sm font-bold mb-4">총 {suspendModal.total_count}개 처리 예정</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setSuspendModal(null)} className={`px-4 py-2 rounded-lg text-sm ${dark ? 'bg-[#2d3144]' : 'bg-gray-100'}`}>취소</button>
              {suspendModal.total_count > 0 && (
                <button onClick={handleSuspend} disabled={suspending} className="px-4 py-2 rounded-lg bg-orange-500 text-white text-sm">
                  {suspending ? '처리 중...' : '품절처리 실행'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
