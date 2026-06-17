import { useEffect, useState, useCallback } from 'react';
import { Download, ShoppingBag, Search } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  fetchGmarketMyProducts, fetchGmarketMyAccounts, exportGmarketMyProducts,
  type GmarketMyProduct, type GmarketAccount,
} from '../../api/gmarketMy';

const PER_PAGE_OPTIONS = [50, 100, 200, 500, 1000];
const MARKET_LABEL: Record<string, string> = { gmarket: '지마켓', auction: '옥션' };
const fmt = (n: number) => (n || 0).toLocaleString();

export default function GmarketMyProductsPage() {
  const [accounts, setAccounts] = useState<GmarketAccount[]>([]);
  const [items, setItems] = useState<GmarketMyProduct[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(50);
  const [accountId, setAccountId] = useState<number | undefined>(undefined);  // 아이디 선택
  const [market, setMarket] = useState('');     // 쇼핑몰 선택: '' 전체 | gmarket | auction
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [sort, setSort] = useState('product_no');
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');
  const [dedup, setDedup] = useState(false);   // 중복(같은 판매자코드) 제외

  useEffect(() => {
    fetchGmarketMyAccounts().then(setAccounts).catch(() => setAccounts([]));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetchGmarketMyProducts(page, perPage, accountId, market || undefined, status || undefined, search || undefined, sort, order, dedup);
      setItems(r.items); setTotal(r.total); setTotalPages(r.total_pages);
    } catch { toast.error('상품 조회 실패'); } finally { setLoading(false); }
  }, [page, perPage, accountId, market, status, search, sort, order, dedup]);

  useEffect(() => { load(); }, [load]);

  const sortBy = (k: string) => {
    if (sort === k) setOrder(o => (o === 'asc' ? 'desc' : 'asc'));
    else { setSort(k); setOrder('asc'); }
    setPage(1);
  };
  const arrow = (k: string) => (sort === k ? (order === 'asc' ? ' ▲' : ' ▼') : '');

  const acctLabel = accountId ? (accounts.find(a => a.account_id === accountId)?.login_id || '선택계정') : '전체';
  const downloadAll = async () => {
    if (downloading) return;
    setDownloading(true);
    const tid = toast.loading(`다운로드 중... (${acctLabel} ${fmt(total)}건)`);
    try {
      const blob = await exportGmarketMyProducts(accountId, market || undefined, status || undefined, search || undefined, dedup);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `지마켓_나의상품_${acctLabel}${dedup ? '_중복제외' : ''}_${new Date().toLocaleDateString('sv')}.csv`;
      a.click(); URL.revokeObjectURL(url);
      toast.success(`${acctLabel} ${fmt(total)}건 다운로드`, { id: tid });
    } catch { toast.error('다운로드 실패', { id: tid }); } finally { setDownloading(false); }
  };

  const selStyle = 'px-2 py-2 rounded-lg border border-gray-300 text-[12px] bg-white';

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center gap-2">
        <ShoppingBag size={18} className="text-emerald-600" />
        <h1 className="text-[12px] font-bold">지마켓/옥션 나의 상품</h1>
        <span className="text-[12px] text-gray-500">총 {fmt(total)}개</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {/* 쇼핑몰 선택 */}
        <select value={market} onChange={e => { setMarket(e.target.value); setPage(1); }} className={selStyle}>
          <option value="">쇼핑몰 전체</option>
          <option value="gmarket">지마켓</option>
          <option value="auction">옥션</option>
        </select>
        {/* 아이디 선택 */}
        <select value={accountId ?? ''} onChange={e => { setAccountId(e.target.value ? Number(e.target.value) : undefined); setPage(1); }} className={selStyle}>
          <option value="">아이디 전체</option>
          {accounts.map(a => (
            <option key={a.account_id} value={a.account_id}>{a.login_id}{a.seller_name && a.seller_name !== a.login_id ? ` (${a.seller_name})` : ''} · {a.product_count}</option>
          ))}
        </select>
        {/* 상태 */}
        <select value={status} onChange={e => { setStatus(e.target.value); setPage(1); }} className={selStyle}>
          <option value="">상태 전체</option>
          <option value="판매중">판매중</option>
          <option value="판매중지">판매중지</option>
          <option value="품절">품절</option>
          <option value="판매불가">판매불가</option>
          <option value="판매종료">판매종료</option>
        </select>
        {/* 검색 */}
        <div className="flex items-center gap-1">
          <input value={searchInput} onChange={e => setSearchInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { setSearch(searchInput); setPage(1); } }}
            placeholder="상품명/상품번호/코드/아이디" className={`${selStyle} w-52`} />
          <button onClick={() => { setSearch(searchInput); setPage(1); }} className="px-2.5 py-2 rounded-lg bg-blue-600 text-white text-[12px]"><Search size={13} /></button>
        </div>
        {/* 중복(같은 판매자코드) 제외 */}
        <label className="inline-flex items-center gap-1.5 px-2 py-2 rounded-lg border border-gray-300 text-[12px] bg-white cursor-pointer select-none" title="같은 판매자코드(=같은 상품)가 여러 상품번호/마켓으로 등록된 중복을 1개만 표시">
          <input type="checkbox" checked={dedup} onChange={e => { setDedup(e.target.checked); setPage(1); }} />
          중복제외
        </label>
        <button onClick={downloadAll} disabled={downloading}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold bg-teal-600 hover:bg-teal-700 text-white disabled:opacity-40">
          <Download size={13} /> {downloading ? '다운로드 중…' : `${acctLabel} 다운로드 (${fmt(total)})`}
        </button>
      </div>

      <div className="rounded-lg border border-gray-200 overflow-auto">
        <table className="w-full text-[12px]">
          <thead className="bg-gray-50 text-gray-600 select-none">
            <tr>
              <th onClick={() => sortBy('market')} className="px-3 py-2 text-left cursor-pointer hover:text-blue-600">쇼핑몰{arrow('market')}</th>
              <th onClick={() => sortBy('login_id')} className="px-3 py-2 text-left cursor-pointer hover:text-blue-600">아이디{arrow('login_id')}</th>
              <th onClick={() => sortBy('product_no')} className="px-3 py-2 text-left cursor-pointer hover:text-blue-600">상품번호{arrow('product_no')}</th>
              <th onClick={() => sortBy('product_name')} className="px-3 py-2 text-left cursor-pointer hover:text-blue-600">상품명{arrow('product_name')}</th>
              <th onClick={() => sortBy('sale_price')} className="px-3 py-2 text-right cursor-pointer hover:text-blue-600">판매가{arrow('sale_price')}</th>
              <th onClick={() => sortBy('stock_quantity')} className="px-3 py-2 text-right cursor-pointer hover:text-blue-600">재고{arrow('stock_quantity')}</th>
              <th onClick={() => sortBy('status_type')} className="px-3 py-2 text-left cursor-pointer hover:text-blue-600">상태{arrow('status_type')}</th>
              <th onClick={() => sortBy('seller_product_code')} className="px-3 py-2 text-left cursor-pointer hover:text-blue-600">판매자코드{arrow('seller_product_code')}</th>
              <th className="px-3 py-2 text-left">카테고리</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={9} className="px-3 py-8 text-center text-gray-400">불러오는 중…</td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={9} className="px-3 py-8 text-center text-gray-400">상품이 없습니다</td></tr>
            ) : items.map(p => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-3 py-1.5">{MARKET_LABEL[p.market] || p.market}</td>
                <td className="px-3 py-1.5 font-mono text-[11px]">{p.login_id}</td>
                <td className="px-3 py-1.5 font-mono">{p.product_no}</td>
                <td className="px-3 py-1.5">{p.product_name}</td>
                <td className="px-3 py-1.5 text-right">{fmt(p.sale_price)}</td>
                <td className="px-3 py-1.5 text-right">{fmt(p.stock_quantity)}</td>
                <td className="px-3 py-1.5">{p.status_type}</td>
                <td className="px-3 py-1.5 text-[11px]">{p.seller_product_code}</td>
                <td className="px-3 py-1.5 text-[11px] text-gray-500">{p.category_code}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-[12px]">
        <select value={perPage} onChange={e => { setPerPage(Number(e.target.value)); setPage(1); }} className={selStyle}>
          {PER_PAGE_OPTIONS.map(n => <option key={n} value={n}>{n}개씩</option>)}
        </select>
        <div className="flex items-center gap-2">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="px-2 py-1 border rounded disabled:opacity-30">이전</button>
          <span>{page} / {totalPages || 1}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="px-2 py-1 border rounded disabled:opacity-30">다음</button>
        </div>
      </div>
    </div>
  );
}
