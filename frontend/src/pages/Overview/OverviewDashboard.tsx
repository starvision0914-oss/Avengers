import { useState, useEffect, useCallback, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { getOverview, getMallProfit, type OverviewResponse, type MallProfitResponse } from '../../api/overview';
import { formatKRW } from '../../utils/format';

function todayKST(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' });
}
function curMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

// 쇼핑몰 브랜드 색/아이콘
const MALL: Record<string, { color: string; emoji: string; grad: string }> = {
  gmarket:     { color: '#16a34a', emoji: '🟢', grad: 'linear-gradient(135deg,#6cc24a,#4d9e2f)' },
  auction:     { color: '#db2777', emoji: '🅰️', grad: 'linear-gradient(135deg,#ec4899,#be185d)' },
  '11st':      { color: '#ff5a2e', emoji: '1️⃣', grad: 'linear-gradient(135deg,#ff7a52,#e23e16)' },
  smartstore:  { color: '#03c75a', emoji: '🟩', grad: 'linear-gradient(135deg,#22c55e,#03a14a)' },
  coupang:     { color: '#ef4444', emoji: '🚀', grad: 'linear-gradient(135deg,#f87171,#dc2626)' },
  lotteon:     { color: '#da291c', emoji: '🛍️', grad: 'linear-gradient(135deg,#f0594c,#b91c1c)' },
};
const mallOf = (p: string) => MALL[p] || { color: '#64748b', emoji: '🏬', grad: 'linear-gradient(135deg,#94a3b8,#64748b)' };

const CARD: React.CSSProperties = {
  background: '#fff', border: '1px solid #eef0f3', borderRadius: 16,
  boxShadow: '0 1px 3px rgba(16,24,40,.06), 0 1px 2px rgba(16,24,40,.04)',
};

export default function OverviewDashboard() {
  const [date, setDate] = useState(todayKST());
  const [month, setMonth] = useState(curMonth());
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [profit, setProfit] = useState<MallProfitResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const fetchData = useCallback(async (d: string, m: string) => {
    setLoading(true); setErr(null);
    try {
      const [ov, pf] = await Promise.all([getOverview(d), getMallProfit(m)]);
      setData(ov); setProfit(pf);
    } catch (e: any) {
      setErr(e?.message || '불러오기 실패');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(date, month); }, [date, month, fetchData]);
  useEffect(() => {
    const t = setInterval(() => fetchData(date, month), 5 * 60 * 1000);
    return () => clearInterval(t);
  }, [date, month, fetchData]);

  const pie = useMemo(() => {
    if (!data) return [];
    return data.markets.filter(m => m.ad_cost > 0).map(m => ({ name: m.label, value: m.ad_cost, color: m.color }));
  }, [data]);

  const t = data?.totals;
  const pt = profit?.totals;
  const profitRows = useMemo(
    () => (profit?.rows || []).filter(r => r.revenue > 0 || r.ad_cost > 0).sort((a, b) => b.revenue - a.revenue),
    [profit]
  );
  const maxNet = useMemo(() => Math.max(1, ...profitRows.map(r => Math.abs(r.net_profit))), [profitRows]);

  const winColor = (n: number) => (n >= 0 ? '#16a34a' : '#dc2626');

  return (
    <div style={{ padding: '20px 20px 48px', maxWidth: 1240, margin: '0 auto', background: '#f6f7f9', minHeight: '100%' }}>
      <style>{`
        .ovh-card{transition:transform .15s ease, box-shadow .15s ease;}
        .ovh-card:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(16,24,40,.10);}
        .ovh-btn:hover{background:#f3f4f6;}
        .ovh-spin{animation:ovspin 1s linear infinite;display:inline-block;}
        @keyframes ovspin{to{transform:rotate(360deg)}}
      `}</style>

      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18, flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, letterSpacing: -0.5 }}>📊 통합 현황</h1>
        <button className="ovh-btn" onClick={() => fetchData(date, month)} disabled={loading}
          style={{ padding: '6px 14px', border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
          {loading ? <span className="ovh-spin">↻</span> : '↻'} {loading ? ' 불러오는 중' : ' 새로고침'}
        </button>
        {data?.last_collected && (
          <span style={{ fontSize: 12, color: '#9ca3af', marginLeft: 'auto' }}>
            최근 수집 {new Date(data.last_collected).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>

      {err && <div style={{ color: '#dc2626', padding: 12, background: '#fef2f2', borderRadius: 12, marginBottom: 16, border: '1px solid #fecaca' }}>{err}</div>}

      {/* ===== 종합 순수익 히어로 ===== */}
      {pt && (
        <div style={{
          ...CARD, padding: '20px 24px', marginBottom: 16, color: '#fff', border: 'none',
          background: pt.net_profit >= 0
            ? 'linear-gradient(120deg,#0ea5e9 0%,#22c55e 100%)'
            : 'linear-gradient(120deg,#f97316 0%,#ef4444 100%)',
          boxShadow: '0 10px 30px rgba(2,132,199,.18)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 14, fontWeight: 700, opacity: .92 }}>이번 달 종합 순수익</span>
            <input type="month" value={month} onChange={e => setMonth(e.target.value)}
              style={{ padding: '4px 8px', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, color: '#111' }} />
            <span style={{ marginLeft: 'auto', fontSize: 13, fontWeight: 800, padding: '5px 14px', borderRadius: 999, background: 'rgba(255,255,255,.22)' }}>
              {pt.net_profit >= 0 ? '🟢 흑자' : '🔴 적자'}
            </span>
          </div>
          <div style={{ fontSize: 40, fontWeight: 900, marginTop: 6, letterSpacing: -1 }}>
            {pt.net_profit >= 0 ? '+' : ''}{formatKRW(pt.net_profit)}<span style={{ fontSize: 22, fontWeight: 700 }}> 원</span>
            <span style={{ fontSize: 16, fontWeight: 700, marginLeft: 10, opacity: .9 }}>순수익률 {pt.net_margin}%</span>
          </div>
          <div style={{ display: 'flex', gap: 28, marginTop: 14, flexWrap: 'wrap', fontSize: 13.5 }}>
            <HeroStat label="매출" value={`${formatKRW(pt.revenue)}원`} />
            <HeroStat label="매출이익" value={`${formatKRW(pt.gross_profit)}원`} />
            <HeroStat label="광고비" value={`${formatKRW(pt.ad_cost)}원`} />
            <HeroStat label="주문수" value={`${formatKRW(pt.orders)}건`} />
          </div>
        </div>
      )}

      {/* ===== 쇼핑몰별 손익 카드 ===== */}
      {pt && (
        <>
          <div style={{ fontSize: 16, fontWeight: 800, margin: '4px 2px 12px' }}>💰 쇼핑몰별 손익</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(238px, 1fr))', gap: 14, marginBottom: 26 }}>
            {profitRows.map(r => {
              const win = r.net_profit >= 0;
              const mk = mallOf(r.platform);
              const barW = Math.round(Math.abs(r.net_profit) / maxNet * 100);
              return (
                <div key={r.platform} className="ovh-card" style={{ ...CARD, overflow: 'hidden' }}>
                  <div style={{ height: 6, background: mk.grad }} />
                  <div style={{ padding: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                      <span style={{ fontSize: 15.5, fontWeight: 800, color: '#111' }}>{mk.emoji} {r.label}</span>
                      <span style={{ fontSize: 11.5, fontWeight: 800, padding: '3px 9px', borderRadius: 999, color: '#fff', background: win ? '#16a34a' : '#dc2626' }}>
                        {win ? '흑자' : '적자'}
                      </span>
                    </div>
                    <div style={{ fontSize: 25, fontWeight: 900, color: winColor(r.net_profit), letterSpacing: -0.5 }}>
                      {win ? '+' : ''}{formatKRW(r.net_profit)}<span style={{ fontSize: 14, fontWeight: 700 }}> 원</span>
                    </div>
                    <div style={{ fontSize: 11.5, color: '#9ca3af', marginBottom: 10 }}>순수익률 {r.net_margin}%</div>
                    {/* 비교 바 */}
                    <div style={{ height: 6, background: '#f1f5f9', borderRadius: 999, overflow: 'hidden', marginBottom: 12 }}>
                      <div style={{ width: `${barW}%`, height: '100%', background: win ? '#22c55e' : '#ef4444' }} />
                    </div>
                    <div style={{ fontSize: 12.5, color: '#475569', lineHeight: 1.9 }}>
                      <Row k="매출" v={`${formatKRW(r.revenue)}원`} />
                      <Row k="매출이익" v={`${formatKRW(r.gross_profit)}원`} vColor="#0891b2" />
                      <Row k="광고비" v={r.has_ad_data ? `${formatKRW(r.ad_cost)}원${r.revenue > 0 ? ` · ${r.ad_ratio}%` : ''}` : '—'} vColor="#d97706" />
                      <Row k="주문" v={`${formatKRW(r.orders)}건`} vColor="#94a3b8" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* ===== 당일 광고·계정 현황 ===== */}
      {t && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '0 2px 12px' }}>
            <span style={{ fontSize: 16, fontWeight: 800 }}>📅 당일 광고·계정</span>
            <input type="date" value={date} onChange={e => setDate(e.target.value)}
              style={{ padding: '4px 8px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 13 }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12, marginBottom: 16 }}>
            <MiniStat icon="💸" label="총 광고비 (당일)" value={`${formatKRW(t.ad_cost)}원`} color="#f59e0b" />
            <MiniStat icon="🏦" label="총 잔액" sub="예치금+셀러포인트" value={`${formatKRW(t.balance)}원`} color="#0369a1" />
            <MiniStat icon="👥" label="계정 현황" sub={`정상 ${t.normal} / 실패 ${t.failed}`} value={`${t.accounts}개`} color={t.failed > 0 ? '#dc2626' : '#16a34a'} />
          </div>

          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginBottom: 16 }}>
            <div className="ovh-card" style={{ ...CARD, flex: '0 0 290px', padding: 18 }}>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>마켓별 광고비 비중 (당일)</div>
              {pie.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={pie} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={52} outerRadius={82} paddingAngle={2}>
                      {pie.map((p, i) => <Cell key={i} fill={p.color} />)}
                    </Pie>
                    <Tooltip formatter={(v: any) => `${formatKRW(Number(v))}원`} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: 13 }}>
                  당일 광고비 없음
                </div>
              )}
            </div>

            <div style={{ flex: 1, minWidth: 320, display: 'flex', flexDirection: 'column', gap: 12 }}>
              {data!.markets.map(m => (
                <div key={m.key} className="ovh-card" style={{ ...CARD, padding: 16, borderLeft: `5px solid ${m.color}` }}>
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

          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <AlertBox title="⛔ 실패/차단 계정" color="#dc2626" count={data!.alerts.failed_accounts.length}
              items={data!.alerts.failed_accounts.map(a => `[${a.platform}] ${a.seller_name || a.login_id} (${a.status})`)} />
            <AlertBox title="⚠️ 잔액 부족 (5만↓)" color="#e67700" count={data!.alerts.low_balance.length}
              items={data!.alerts.low_balance.map(a => `${a.seller}: ${formatKRW(a.balance)}원`)} />
            <AlertBox title="💤 당일 광고비 0" color="#6b7280" count={data!.alerts.zero_ad.length}
              items={data!.alerts.zero_ad.map(a => a.seller)} />
          </div>

          <p style={{ fontSize: 11.5, color: '#9ca3af', marginTop: 16, lineHeight: 1.6 }}>
            순수익 = 매출이익(매출−원가) − 광고비. 광고비 출처: 지마켓·옥션=거래내역, 11번가=상품ROAS(adoffice). 스마트스토어·쿠팡 등은 광고비 데이터 없음(—).
          </p>
        </>
      )}
    </div>
  );
}

function HeroStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 12, opacity: .85 }}>{label}</div>
      <div style={{ fontSize: 17, fontWeight: 800, marginTop: 2 }}>{value}</div>
    </div>
  );
}

function Row({ k, v, vColor }: { k: string; v: string; vColor?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
      <span style={{ color: '#94a3b8' }}>{k}</span>
      <span style={{ fontWeight: 700, color: vColor || '#334155' }}>{v}</span>
    </div>
  );
}

function MiniStat({ icon, label, value, sub, color }: { icon: string; label: string; value: string; sub?: string; color: string }) {
  return (
    <div className="ovh-card" style={{ ...CARD, padding: '14px 16px' }}>
      <div style={{ fontSize: 12.5, color: '#6b7280', marginBottom: 6 }}>{icon} {label}</div>
      <div style={{ fontSize: 23, fontWeight: 800, color }}>{value}</div>
      {sub && <div style={{ fontSize: 11.5, color: '#9ca3af', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function AlertBox({ title, color, count, items }: { title: string; color: string; count: number; items: string[] }) {
  return (
    <div className="ovh-card" style={{ ...CARD, flex: 1, minWidth: 240, padding: 14 }}>
      <div style={{ fontSize: 14, fontWeight: 700, color, marginBottom: 8 }}>
        {title} <span style={{ color: '#111', background: '#f3f4f6', padding: '1px 8px', borderRadius: 999, fontSize: 12 }}>{count}</span>
      </div>
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
