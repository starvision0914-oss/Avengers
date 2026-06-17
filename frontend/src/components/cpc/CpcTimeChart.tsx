import { useMemo } from 'react';
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';
import type { TimeseriesRow, SalesTimeseriesRow } from '../../types/cpc';
import { formatKRW } from '../../utils/format';

interface Props {
  data: TimeseriesRow[];
  salesData: SalesTimeseriesRow[];
  sellerAlias: string;
}

interface ChartPoint {
  time: string;
  cpc: number;
  ai: number;
  prime: number;
  salesCum: number | null;
  orderAmt: number | null;
}

function CustomDot(props: any) {
  const { cx, cy, payload } = props;
  if (!payload.orderAmt || payload.orderAmt === 0) return null;
  return (
    <g>
      <circle cx={cx} cy={cy} r={4} fill="#00a651" stroke="#fff" strokeWidth={1.5} />
      <text x={cx} y={cy - 10} textAnchor="middle" fontSize={9} fill="#00a651" fontWeight="bold">
        {formatKRW(payload.orderAmt)}
      </text>
    </g>
  );
}

export default function CpcTimeChart({ data, salesData, sellerAlias }: Props) {
  const { chartData, totalSales, orderCount } = useMemo(() => {
    const allTimes = new Set<string>();
    const adSorted = [...data].sort((a, b) => a.ts.localeCompare(b.ts));
    for (const r of adSorted) allTimes.add(r.ts);
    const salesSorted = [...salesData].sort((a, b) => a.ts.localeCompare(b.ts));
    for (const r of salesSorted) allTimes.add(r.ts);

    const adMap = new Map<string, { cpc: number; ai: number; prime: number }>();
    for (const r of adSorted) {
      const prev = adMap.get(r.ts);
      if (prev) { prev.cpc += r.cpc; prev.ai += r.ai; prev.prime += r.prime; }
      else adMap.set(r.ts, { cpc: r.cpc, ai: r.ai, prime: r.prime });
    }

    const salesMap = new Map<string, number>();
    let totalSales = 0, orderCount = 0;
    for (const r of salesSorted) {
      salesMap.set(r.ts, (salesMap.get(r.ts) || 0) + r.sales);
      totalSales += r.sales;
      orderCount++;
    }

    const times = Array.from(allTimes).sort();
    let cpcAcc = 0, aiAcc = 0, primeAcc = 0, salesAcc = 0;
    const points: ChartPoint[] = [];

    for (const t of times) {
      const ad = adMap.get(t);
      if (ad) { cpcAcc += ad.cpc; aiAcc += ad.ai; primeAcc += ad.prime; }
      const orderVal = salesMap.get(t) || 0;
      salesAcc += orderVal;
      points.push({
        time: t, cpc: cpcAcc, ai: aiAcc, prime: primeAcc,
        salesCum: salesData.length > 0 ? salesAcc : null,
        orderAmt: orderVal > 0 ? orderVal : null,
      });
    }
    return { chartData: points, totalSales, orderCount };
  }, [data, salesData]);

  if (!chartData.length) return null;
  const hasSales = salesData.length > 0;

  return (
    <div className="bg-white border border-[#e0e0e0] rounded p-5">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-[12px] font-bold text-[#333]">
          {sellerAlias}
          <span className="ml-2 text-[11px] font-normal text-[#999]">누적 광고비 추이</span>
        </h3>
        {hasSales && (
          <span className="text-[12px]">
            <span className="text-[#00a651] font-bold">{formatKRW(totalSales)}원</span>
            <span className="text-[#999] ml-1">({orderCount}건)</span>
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#999' }} interval="preserveStartEnd" />
          <YAxis yAxisId="ad" tick={{ fontSize: 10, fill: '#999' }} tickFormatter={(v: number) => formatKRW(v)} width={60} />
          {hasSales && (
            <YAxis yAxisId="sales" orientation="right" tick={{ fontSize: 10, fill: '#00a651' }}
              tickFormatter={(v: number) => formatKRW(v)} width={70} />
          )}
          <Tooltip
            formatter={(v, name) => v === null || v === undefined ? ['-', name ?? ''] : [formatKRW(v as number) + '원', name ?? '']}
            contentStyle={{ fontSize: 12, borderRadius: 4, border: '1px solid #e0e0e0' }}
          />
          <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
          <Line yAxisId="ad" type="monotone" dataKey="cpc" stroke="#1a73e8" name="CPC" dot={false} strokeWidth={2} />
          <Line yAxisId="ad" type="monotone" dataKey="ai" stroke="#e08000" name="AI" dot={false} strokeWidth={2} />
          <Line yAxisId="ad" type="monotone" dataKey="prime" stroke="#9c27b0" name="프라임" dot={false} strokeWidth={2} />
          {hasSales && (
            <Line yAxisId="sales" type="stepAfter" dataKey="salesCum" stroke="#00a651" name="누적매출"
              dot={<CustomDot />} strokeWidth={2} strokeDasharray="6 3" connectNulls={false} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
