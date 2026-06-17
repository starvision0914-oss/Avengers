import { useState, useEffect, useCallback, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { getOverview, type OverviewResponse } from '../../api/overview';
import { formatKRW } from '../../utils/format';

function todayKST(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' });
}

function SummaryCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color: string }) {
  return (
    <div style={{ flex: 1, minWidth: 160, background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: '14px 16px' }}>
      <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 800, color }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

export default function OverviewDashboard() {
  const [date, setDate] = useState(todayKST());
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const fetchData = useCallback(async (d: string) => {
    setLoading(true);
    setErr(null);
    try {
      setData(await getOverview(d));
    } catch (e: any) {
      setErr(e?.message || '불러오기 실패');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(date); }, [date, fetchData]);
  // 5분 자동 새로고침
  useEffect(() => {
    const t = setInterval(() => fetchData(date), 5 * 60 * 1000);
    return () => clearInterval(t);
  }, [date, fetchData]);

  const pie = useMemo(() => {
    if (!data) return [];
    return data.markets.filter(m => m.ad_cost > 0).map(m => ({ name: m.label, value: m.ad_cost, color: m.color }));
  }, [data]);

  const t = data?.totals;

  return (
    <div style={{ padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>📊 통합 현황</h1>
        <input type="date" value={date} onChange={e => setDate(e.target.value)}
          style={{ padding: '4px 8px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 }} />
        <button onClick={() => fetchData(date)} disabled={loading}
          style={{ padding: '4px 12px', border: '1px solid #d1d5db', borderRadius: 6, background: '#fff', cursor: 'pointer', fontSize: 14 }}>
          {loading ? '불러오는 중…' : '↻ 새로고침'}
        </button>
        {data?.last_collected && (
          <span style={{ fontSize: 12, color: '#9ca3af', marginLeft: 'auto' }}>
            최근 수집: {new Date(data.last_collected).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>

      {err && <div style={{ color: '#dc2626', padding: 12, background: '#fef2f2', borderRadius: 8, marginBottom: 16 }}>{err}</div>}

      {t && (
        <>
          {/* 합계 카드 */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
            <SummaryCard label="총 광고비 (당일)" value={`${formatKRW(t.ad_cost)}원`} color="#f59e0b" />
            <SummaryCard label="총 잔액 (예치금+셀러포인트)" value={`${formatKRW(t.balance)}원`} sub="11번가 캐시 제외" color="#0369a1" />
            <SummaryCard label="계정 현황" value={`${t.accounts}개`} sub={`정상 ${t.normal} / 실패 ${t.failed}`} color={t.failed > 0 ? '#dc2626' : '#16a34a'} />
          </div>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {/* 도넛: 마켓별 광고비 비중 */}
            <div style={{ flex: '0 0 300px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>마켓별 광고비 비중</div>
              {pie.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={pie} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={2}>
                      {pie.map((p, i) => <Cell key={i} fill={p.color} />)}
                    </Pie>
                    <Tooltip formatter={(v: any) => `${formatKRW(Number(v))}원`} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: 13 }}>
                  당일 광고비 없음 (수집 전이거나 0원)
                </div>
              )}
            </div>

            {/* 마켓별 카드 */}
            <div style={{ flex: 1, minWidth: 320, display: 'flex', flexDirection: 'column', gap: 12 }}>
              {data.markets.map(m => (
                <div key={m.key} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, borderLeft: `5px solid ${m.color}` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                    <span style={{ fontSize: 16, fontWeight: 800, color: m.color }}>{m.label}</span>
                    <span style={{ fontSize: 12, color: '#9ca3af' }}>계정 {m.accounts}개 (정상 {m.normal} / 실패 {m.failed})</span>
                  </div>
                  <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                    <div><span style={{ fontSize: 12, color: '#6b7280' }}>광고비 </span><b style={{ color: '#f59e0b' }}>{formatKRW(m.ad_cost)}원</b>
                      {m.ai > 0 && <span style={{ fontSize: 11, color: '#9ca3af' }}> (CPC {formatKRW(m.cpc)}/AI {formatKRW(m.ai)})</span>}</div>
                    <div><span style={{ fontSize: 12, color: '#6b7280' }}>잔액 </span><b style={{ color: '#0369a1' }}>{formatKRW(m.balance)}원</b>
                      {m.key === '11st' && m.cash != null && <span style={{ fontSize: 11, color: '#9ca3af' }}> (셀러캐시 {formatKRW(m.cash)})</span>}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 경보 패널 */}
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 16 }}>
            <AlertBox title="⛔ 실패/차단 계정" color="#dc2626" count={data.alerts.failed_accounts.length}
              items={data.alerts.failed_accounts.map(a => `[${a.platform}] ${a.seller_name || a.login_id} (${a.status})`)} />
            <AlertBox title="⚠️ 잔액 부족 (5만↓)" color="#e67700" count={data.alerts.low_balance.length}
              items={data.alerts.low_balance.map(a => `${a.seller}: ${formatKRW(a.balance)}원`)} />
            <AlertBox title="💤 당일 광고비 0" color="#6b7280" count={data.alerts.zero_ad.length}
              items={data.alerts.zero_ad.map(a => a.seller)} />
          </div>
        </>
      )}
    </div>
  );
}

function AlertBox({ title, color, count, items }: { title: string; color: string; count: number; items: string[] }) {
  return (
    <div style={{ flex: 1, minWidth: 240, background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12 }}>
      <div style={{ fontSize: 14, fontWeight: 700, color, marginBottom: 8 }}>{title} <span style={{ color: '#111' }}>{count}</span></div>
      {count === 0 ? (
        <div style={{ fontSize: 13, color: '#9ca3af' }}>없음 ✅</div>
      ) : (
        <div style={{ maxHeight: 160, overflowY: 'auto', fontSize: 13, color: '#374151', lineHeight: 1.7 }}>
          {items.map((it, i) => <div key={i}>· {it}</div>)}
        </div>
      )}
    </div>
  );
}
