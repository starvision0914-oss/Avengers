import { TrendingUp, TrendingDown, Eye, ArrowUp, ArrowDown, ArrowUpDown, Filter as FilterIcon } from 'lucide-react';
import type { KeywordProductItem, SortColumn, SortOrder, FilterableColumn } from '../../api/keyword';
import { themeStyles, fmt, SALE_STATUS_LABEL, SALE_STATUS_COLOR, MARKETS } from './constants';
import KeywordHoverImage from './KeywordHoverImage';
import CategoryPath from '../../components/CategoryPath';

interface Props {
  dark: boolean;
  items: KeywordProductItem[];
  onSelect: (id: number) => void;
  sort?: SortColumn;
  order: SortOrder;
  onSort: (col: SortColumn) => void;
  selectedIds: Set<number>;
  onToggleId: (id: number) => void;
  onToggleAll: () => void;
  filterCol?: FilterableColumn;
  filterVals: string[];
  onOpenFilter: (col: FilterableColumn, label: string, anchor: DOMRect) => void;
}

function changedFieldCount(p: KeywordProductItem): number {
  let n = 0;
  if (p.product_name !== p.orig_product_name) n++;
  if (p.market_product_name !== p.orig_market_product_name) n++;
  if (p.ownerclan_price !== p.orig_ownerclan_price) n++;
  if (p.market_price !== p.orig_market_price) n++;
  if (p.consumer_price !== p.orig_consumer_price) n++;
  if (p.shipping_fee !== p.orig_shipping_fee) n++;
  if (p.return_fee !== p.orig_return_fee) n++;
  if (p.image_large !== p.orig_image_large) n++;
  return n;
}

export default function KeywordProductsTable({ dark, items, onSelect, sort, order, onSort, selectedIds, onToggleId, onToggleAll, filterCol, filterVals, onOpenFilter }: Props) {
  const s = themeStyles(dark);
  const allChecked = items.length > 0 && items.every(p => selectedIds.has(p.id));
  const someChecked = !allChecked && items.some(p => selectedIds.has(p.id));

  const FilterButton = ({ col, label }: { col: FilterableColumn; label: string }) => {
    const active = filterCol === col && filterVals.length > 0;
    return (
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onOpenFilter(col, label, (e.currentTarget as HTMLElement).getBoundingClientRect()); }}
        className={`p-0.5 rounded hover:bg-blue-500/20 ${active ? 'text-blue-500' : s.text3}`}
        title={active ? `${label} 필터 적용중 (${filterVals.length}개)` : `${label} 필터`}
      >
        <FilterIcon size={11} fill={active ? 'currentColor' : 'none'} />
      </button>
    );
  };

  const SortIcon = ({ col }: { col: SortColumn }) => {
    if (sort !== col) return <ArrowUpDown size={11} className="opacity-40" />;
    return order === 'asc'
      ? <ArrowUp size={11} className="text-blue-500" />
      : <ArrowDown size={11} className="text-blue-500" />;
  };

  const SortableHeader = ({ col, label, align = 'left' }: { col: SortColumn; label: string; align?: 'left' | 'right' | 'center' }) => (
    <button
      type="button"
      onClick={() => onSort(col)}
      className={`flex items-center gap-1 font-medium select-none cursor-pointer ${
        align === 'right' ? 'ml-auto' : align === 'center' ? 'mx-auto' : ''
      } ${sort === col ? 'text-blue-500' : ''} hover:text-blue-500 transition-colors`}
    >
      {label}
      <SortIcon col={col} />
    </button>
  );

  return (
    <div className={`rounded-xl border ${s.card} overflow-hidden`}>
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead className={`${dark ? 'bg-[#0f1117]' : 'bg-gray-50'} sticky top-0`}>
            <tr className={s.text2}>
              <th className="px-3 py-2 text-center font-medium w-9">
                <input
                  type="checkbox"
                  checked={allChecked}
                  ref={el => { if (el) el.indeterminate = someChecked; }}
                  onChange={onToggleAll}
                  onClick={e => e.stopPropagation()}
                  className="cursor-pointer accent-blue-600"
                />
              </th>
              <th className="px-3 py-2 text-left font-medium w-12">이미지</th>
              <th className="px-3 py-2 text-left font-medium w-28"><SortableHeader col="product_code" label="W코드" /></th>
              <th className="px-3 py-2 text-left font-medium w-56">
                <div className="flex items-center gap-1">
                  <SortableHeader col="category_code" label="카테고리" />
                  <FilterButton col="category_name" label="카테고리" />
                </div>
              </th>
              <th className="px-3 py-2 text-left font-medium">상품명</th>
              <th className="px-3 py-2 text-right font-medium w-24"><SortableHeader col="ownerclan_price" label="판매가" align="right" /></th>
              <th className="px-3 py-2 text-right font-medium w-24"><SortableHeader col="market_price" label="마켓가" align="right" /></th>
              <th className="px-3 py-2 text-right font-medium w-20"><SortableHeader col="shipping_fee" label="배송비" align="right" /></th>
              <th className="px-3 py-2 text-center font-medium w-20">상태</th>
              <th className="px-3 py-2 text-center font-medium w-32">마켓</th>
              <th className="px-3 py-2 text-center font-medium w-16">변경</th>
              <th className="px-3 py-2 text-center font-medium w-12"></th>
            </tr>
          </thead>
          <tbody className={`divide-y ${s.divider}`}>
            {items.map((p) => {
              const cnt = changedFieldCount(p);
              const isChanged = cnt > 0 || p.is_synced === 0;
              const checked = selectedIds.has(p.id);
              return (
                <tr
                  key={p.id}
                  className={`${s.rowHover} cursor-pointer transition-colors ${isChanged ? 'border-l-4 border-l-orange-500' : 'border-l-4 border-l-transparent'} ${checked ? (dark ? 'bg-blue-900/20' : 'bg-blue-50') : ''}`}
                  onClick={() => onSelect(p.id)}
                >
                  <td className="px-3 py-2 text-center" onClick={e => { e.stopPropagation(); onToggleId(p.id); }}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onToggleId(p.id)}
                      onClick={e => e.stopPropagation()}
                      className="cursor-pointer accent-blue-600"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <KeywordHoverImage src={p.image_small || p.image_large} previewSrc={p.image_large || p.image_small} thumbnailSize={36} />
                  </td>
                  <td className={`px-3 py-2 font-mono text-[11px] ${s.text2}`}>{p.product_code}</td>
                  <td className="px-3 py-2 max-w-[220px]">
                    <CategoryPath path={p.category_name} dark={dark} compact code={p.category_code} />
                  </td>
                  <td className={`px-3 py-2 ${s.text1} max-w-md`}>
                    <DiffText current={p.market_product_name || p.product_name} orig={p.orig_market_product_name || p.orig_product_name} dark={dark} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <PriceCell current={p.ownerclan_price} orig={p.orig_ownerclan_price} dark={dark} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <PriceCell current={p.market_price} orig={p.orig_market_price} dark={dark} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <PriceCell current={p.shipping_fee} orig={p.orig_shipping_fee} dark={dark} />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <SaleBadge status={p.sale_status} />
                  </td>
                  <td className="px-3 py-2">
                    <MarketDots p={p} />
                  </td>
                  <td className="px-3 py-2 text-center">
                    {cnt > 0 ? (
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-orange-500/15 text-orange-500 text-[10px] font-bold">
                        {cnt}
                      </span>
                    ) : (
                      <span className={`text-[10px] ${s.text3}`}>—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <Eye size={14} className={s.text3} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PriceCell({ current, orig, dark }: { current: number; orig: number; dark: boolean }) {
  const s = themeStyles(dark);
  const changed = current !== orig;
  if (!changed) return <span className={s.text2}>{fmt(current)}</span>;
  const up = current > orig;
  return (
    <div className="leading-tight">
      <div className={`flex items-center justify-end gap-1 font-bold ${up ? 'text-orange-500' : 'text-blue-400'}`}>
        {up ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
        {fmt(current)}
      </div>
      <div className={`text-[10px] line-through ${s.text3}`}>{fmt(orig)}</div>
    </div>
  );
}

function DiffText({ current, orig, dark }: { current: string; orig: string; dark: boolean }) {
  const s = themeStyles(dark);
  const changed = current !== orig;
  return (
    <div className="leading-tight truncate">
      <div className={`truncate ${changed ? 'text-orange-500 font-semibold' : s.text1}`}>{current || '-'}</div>
      {changed && orig && <div className={`text-[10px] line-through truncate ${s.text3}`}>{orig}</div>}
    </div>
  );
}

function SaleBadge({ status }: { status: number }) {
  const label = SALE_STATUS_LABEL[status] || '—';
  const color = SALE_STATUS_COLOR[status] || '#94a3b8';
  return (
    <span
      className="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold"
      style={{ backgroundColor: `${color}25`, color }}
    >
      {label}
    </span>
  );
}

function MarketDots({ p }: { p: KeywordProductItem }) {
  return (
    <div className="flex items-center justify-center gap-1">
      {MARKETS.map(m => {
        const v = (p as any)[m.key];
        const on = v && v !== '' && v !== '0' && v !== 'N';
        return (
          <span
            key={m.key}
            title={`${m.label}: ${on ? '노출' : '미노출'}`}
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: on ? m.color : 'rgba(120,120,120,0.25)' }}
          />
        );
      })}
    </div>
  );
}
