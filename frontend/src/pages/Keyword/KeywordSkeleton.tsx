import { themeStyles } from './constants';

export function TableSkeleton({ dark, rows = 8 }: { dark: boolean; rows?: number }) {
  const s = themeStyles(dark);
  const block = dark ? 'bg-[#2a2b35]' : 'bg-gray-200';
  return (
    <div className={`rounded-xl border ${s.card} overflow-hidden`}>
      <div className={`px-4 py-3 border-b ${s.border}`}>
        <div className={`h-4 w-32 rounded ${block} animate-pulse`} />
      </div>
      <div className={`divide-y ${s.divider}`}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 px-4 py-3">
            <div className={`h-10 w-10 rounded ${block} animate-pulse`} />
            <div className="flex-1 space-y-2">
              <div className={`h-3 w-3/4 rounded ${block} animate-pulse`} />
              <div className={`h-3 w-1/2 rounded ${block} animate-pulse`} />
            </div>
            <div className={`h-3 w-16 rounded ${block} animate-pulse`} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function GridSkeleton({ dark, count = 12 }: { dark: boolean; count?: number }) {
  const s = themeStyles(dark);
  const block = dark ? 'bg-[#2a2b35]' : 'bg-gray-200';
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={`rounded-xl border ${s.card} p-3 space-y-2`}>
          <div className={`aspect-square w-full rounded ${block} animate-pulse`} />
          <div className={`h-3 w-1/3 rounded ${block} animate-pulse`} />
          <div className={`h-4 w-full rounded ${block} animate-pulse`} />
          <div className={`h-3 w-1/2 rounded ${block} animate-pulse`} />
        </div>
      ))}
    </div>
  );
}

export function StatCardSkeleton({ dark }: { dark: boolean }) {
  const s = themeStyles(dark);
  const block = dark ? 'bg-[#2a2b35]' : 'bg-gray-200';
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className={`rounded-xl border ${s.card} p-4 space-y-2`}>
          <div className={`h-3 w-1/2 rounded ${block} animate-pulse`} />
          <div className={`h-6 w-3/4 rounded ${block} animate-pulse`} />
        </div>
      ))}
    </div>
  );
}
