import { TrendingUp, TrendingDown, Package } from 'lucide-react';
import type { OwnerclanProductItem } from '../../api/ownerclan';
import { themeStyles, fmt, SALE_STATUS_LABEL, SALE_STATUS_COLOR, MARKETS } from './constants';

interface Props {
  dark: boolean;
  items: OwnerclanProductItem[];
  onSelect: (id: number) => void;
}

export default function OwnerclanProductsGrid({ dark, items, onSelect }: Props) {
  const s = themeStyles(dark);

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
      {items.map(p => {
        const isChanged = p.is_synced === 0;
        const priceChanged = p.market_price !== p.orig_market_price;
        const up = priceChanged && p.market_price > p.orig_market_price;
        return (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className={`text-left rounded-xl border ${s.card} overflow-hidden hover:scale-[1.02] transition-all relative ${isChanged ? 'ring-1 ring-orange-500/50' : ''}`}
          >
            <div className={`relative aspect-square ${dark ? 'bg-[#0f1117]' : 'bg-gray-100'}`}>
              {p.image_large ? (
                <img
                  src={p.image_large}
                  alt={p.product_name}
                  loading="lazy"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Package size={36} className={s.text3} />
                </div>
              )}
              <div className="absolute top-2 left-2">
                <SaleBadge status={p.sale_status} />
              </div>
              {isChanged && (
                <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-orange-500 text-white text-[10px] font-bold">
                  변경됨
                </div>
              )}
            </div>
            <div className="p-3 space-y-1.5">
              <div className={`font-mono text-[10px] ${s.text3}`}>{p.product_code}</div>
              <div className={`text-[12px] font-medium line-clamp-2 leading-snug ${s.text1}`}>
                {p.market_product_name || p.product_name || '-'}
              </div>
              <div className="flex items-baseline justify-between pt-1">
                <div className={`text-[12px] font-bold ${priceChanged ? (up ? 'text-orange-500' : 'text-blue-400') : s.text1} flex items-center gap-1`}>
                  {priceChanged && (up ? <TrendingUp size={12} /> : <TrendingDown size={12} />)}
                  {fmt(p.market_price)}원
                </div>
                {priceChanged && (
                  <div className={`text-[10px] line-through ${s.text3}`}>{fmt(p.orig_market_price)}</div>
                )}
              </div>
              <MarketBadges p={p} dark={dark} />
            </div>
          </button>
        );
      })}
    </div>
  );
}

function SaleBadge({ status }: { status: number }) {
  const label = SALE_STATUS_LABEL[status] || '—';
  const color = SALE_STATUS_COLOR[status] || '#94a3b8';
  return (
    <span
      className="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold backdrop-blur-sm"
      style={{ backgroundColor: `${color}cc`, color: '#fff' }}
    >
      {label}
    </span>
  );
}

function MarketBadges({ p, dark }: { p: OwnerclanProductItem; dark: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-1 pt-1">
      {MARKETS.map(m => {
        const v = (p as any)[m.key];
        const on = v && v !== '' && v !== '0' && v !== 'N';
        return (
          <span
            key={m.key}
            title={m.label}
            className={`px-1.5 py-0.5 rounded text-[9px] font-bold transition-opacity ${on ? '' : 'opacity-30'}`}
            style={{
              backgroundColor: on ? `${m.color}25` : (dark ? '#2a2b35' : '#f3f4f6'),
              color: on ? m.color : (dark ? '#6b7280' : '#9ca3af'),
            }}
          >
            {m.label}
          </span>
        );
      })}
    </div>
  );
}
