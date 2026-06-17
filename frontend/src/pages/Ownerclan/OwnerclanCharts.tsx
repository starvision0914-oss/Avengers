import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import type { ProductStats } from '../../api/ownerclan';
import { themeStyles, fmt } from './constants';

interface Props {
  dark: boolean;
  stats: ProductStats | null;
}

export default function OwnerclanCharts({ dark, stats }: Props) {
  const s = themeStyles(dark);

  const pie = stats
    ? [
        { name: '판매중', value: stats.selling, color: '#16a34a' },
        { name: '품절', value: stats.soldout, color: '#f59e0b' },
        { name: '단종', value: stats.discontinued, color: '#dc2626' },
      ].filter(d => d.value > 0)
    : [];
  const total = pie.reduce((a, b) => a + b.value, 0);

  return (
    <div className={`rounded-xl border ${s.card} p-4`}>
      <div className={`text-[12px] font-bold ${s.text1} mb-3`}>판매상태 비중</div>
      <div className="flex items-center gap-6">
        <div className="w-[160px] h-[160px] relative shrink-0">
          {pie.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pie} dataKey="value" innerRadius={48} outerRadius={70} paddingAngle={2} strokeWidth={0}>
                  {pie.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Pie>
                <Tooltip
                  formatter={(v: any) => `${fmt(Number(v))}개`}
                  contentStyle={{ fontSize: 11, background: dark ? '#1a1b23' : '#fff', border: '1px solid #333', borderRadius: 8 }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className={`w-full h-full flex items-center justify-center ${s.text3} text-xs`}>데이터 없음</div>
          )}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className={`text-[10px] ${s.text3}`}>전체</span>
            <span className={`text-[12px] font-bold ${s.text1}`}>{fmt(total)}</span>
          </div>
        </div>
        <div className="space-y-2 flex-1">
          {pie.length === 0 && <div className={`text-[12px] ${s.text3}`}>업로드 후 표시됩니다</div>}
          {pie.map(d => {
            const pct = total > 0 ? ((d.value / total) * 100).toFixed(1) : '0';
            return (
              <div key={d.name} className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: d.color }} />
                <div className="flex-1">
                  <div className="flex items-baseline justify-between">
                    <span className={`text-[11px] ${s.text2}`}>{d.name}</span>
                    <span className={`text-[10px] ${s.text3}`}>{pct}%</span>
                  </div>
                  <div className={`text-[12px] font-bold ${s.text1}`}>{fmt(d.value)}개</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
