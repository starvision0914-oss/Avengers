import { useState, useEffect, useCallback, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import {
  getOverview, getMallProfit, getMallProfitProducts,
  type OverviewResponse, type MallProfitResponse, type OverviewParams, type MallProductRow,
} from '../../api/overview';
import { formatKRW } from '../../utils/format';

function todayKST(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' });
}
function ydayKST(): string {
  const d = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  d.setDate(d.getDate() - 1);
  return d.toLocaleDateString('en-CA');
}
function daysAgoKST(n: number): string {
  const d = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  d.setDate(d.getDate() - n);
  return d.toLocaleDateString('en-CA');
}

// Overview/G마켓/스마트스토어/11번가 4개 대시보드 공통 프리셋과 동일한 순서·의미로 통일.
// year=올해(1/1~오늘, calendar YTD) / month=최근30일(rolling) / mtd=당월(이번달 1일~오늘)
type PeriodKey = 'today' | 'yesterday' | 'mtd' | 'month' | 'year' | 'custom';
const PERIODS: { key: PeriodKey; label: string }[] = [
  { key: 'today', label: '오늘' },
  { key: 'yesterday', label: '어제' },
  { key: 'mtd', label: '당월' },
  { key: 'month', label: '한달' },
  { key: 'year', label: '1년' },
  { key: 'custom', label: '기간별' },
];

function firstDayOfMonthKST(): string {
  const d = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  d.setDate(1);
  return d.toLocaleDateString('en-CA');
}
function firstDayOfYearKST(): string {
  const d = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  return `${d.getFullYear()}-01-01`;
}

function periodToOverviewParam(period: PeriodKey, cFrom: string, cTo: string): OverviewParams {
  if (period === 'custom') return { date_from: cFrom, date_to: cTo };
  if (period === 'year') return { period: 'year' };
  if (period === 'month') return { period: 'month' };
  if (period === 'mtd') return { period: 'mtd' };
  if (period === 'today') return { period: 'today' };
  return { period: 'yesterday' };
}

function periodToMallProfitParam(period: PeriodKey, cFrom: string, cTo: string) {
  const today = todayKST();
  if (period === 'custom') return { date_from: cFrom, date_to: cTo };
  if (period === 'year') return { date_from: firstDayOfYearKST(), date_to: today };
  if (period === 'month') return { date_from: daysAgoKST(29), date_to: today };
  if (period === 'mtd') return { date_from: firstDayOfMonthKST(), date_to: today };
  if (period === 'today') return { date_from: today, date_to: today };
  return { date_from: ydayKST(), date_to: ydayKST() };
}

function periodLabel(period: PeriodKey, dateFrom: string, dateTo: string): string {
  if (period === 'year') return '올해';
  if (period === 'month') return '최근 30일';
  if (period === 'mtd') return '이번 달';
  if (period === 'today') return '오늘';
  if (period === 'yesterday') return '어제';
  return dateFrom === dateTo ? dateFrom : `${dateFrom} ~ ${dateTo}`;
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
  // G마켓/스마트스토어/11번가와 동일한 기본 진입 화면(당월)로 통일
  const initialPeriod: PeriodKey = 'mtd';
  const [period, setPeriod] = useState<PeriodKey>(initialPeriod);
  const [cFrom, setCFrom] = useState(firstDayOfMonthKST());
  const [cTo, setCTo] = useState(todayKST());
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [profit, setProfit] = useState<MallProfitResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [modalMall, setModalMall] = useState<{ platform: string; label: string } | null>(null);

  const ovParams = useMemo<OverviewParams>(
    () => periodToOverviewParam(period, cFrom, cTo),
    [period, cFrom, cTo]
  );
  const profitParams = useMemo(
    () => periodToMallProfitParam(period, cFrom, cTo),
    [period, cFrom, cTo]
  );

  const fetchData = useCallback(async (p: OverviewParams, pp: ReturnType<typeof periodToMallProfitParam>) => {
    setLoading(true); setErr(null);
    try {
      const [ov, pf] = await Promise.all([getOverview(p), getMallProfit(pp)]);
      setData(ov); setProfit(pf);
    } catch (e: any) {
      setErr(e?.message || '불러오기 실패');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(ovParams, profitParams); }, [ovParams, profitParams, fetchData]);
  useEffect(() => {
    const t = setInterval(() => fetchData(ovParams, profitParams), 5 * 60 * 1000);
    return () => clearInterval(t);
  }, [ovParams, profitParams, fetchData]);

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
  const pLabel = data ? periodLabel(period, data.date_from, data.date_to) : '';

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

        {/* 기간 선택 */}
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {PERIODS.map(p => (
            <button key={p.key} onClick={() => setPeriod(p.key)}
              style={{
                padding: '5px 14px', borderRadius: 999, cursor: 'pointer', fontSize: 13, fontWeight: 700,
                border: period === p.key ? '1px solid #0ea5e9' : '1px solid #d1d5db',
                background: period === p.key ? '#0ea5e9' : '#fff',
                color: period === p.key ? '#fff' : '#374151',
              }}>{p.label}</button>
          ))}
        </div>

        {period === 'custom' && (
          <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
            <input type="date" value={cFrom} max={cTo} onChange={e => setCFrom(e.target.value)}
              style={{ padding: '4px 8px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 13 }} />
            <span style={{ color: '#9ca3af' }}>~</span>
            <input type="date" value={cTo} min={cFrom} onChange={e => setCTo(e.target.value)}
              style={{ padding: '4px 8px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 13 }} />
          </span>
        )}

        <button className="ovh-btn" onClick={() => fetchData(ovParams, profitParams)} disabled={loading}
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
            <span style={{ fontSize: 14, fontWeight: 700, opacity: .92 }}>종합 순수익 — {pLabel}</span>
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
                <div key={r.platform} className="ovh-card"
                  onClick={() => setModalMall({ platform: r.platform, label: r.label })}
                  style={{ ...CARD, overflow: 'hidden', cursor: 'pointer' }}
                  title="클릭하면 상품별 목록을 볼 수 있습니다">
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
                    <div style={{ height: 6, background: '#f1f5f9', borderRadius: 999, overflow: 'hidden', marginBottom: 12 }}>
                      <div style={{ width: `${barW}%`, height: '100%', background: win ? '#22c55e' : '#ef4444' }} />
                    </div>
                    <div style={{ fontSize: 12.5, color: '#475569', lineHeight: 1.9 }}>
                      <Row k="매출" v={`${formatKRW(r.revenue)}원`} />
                      <Row k="구매가" v={`${formatKRW(r.cost)}원`} vColor="#b45309" />
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

      {/* ===== 기간별 실적 (광고·매출·순익·계정) ===== */}
      {t && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '0 2px 12px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 16, fontWeight: 800 }}>📅 기간별 실적</span>
            {data?.date_from && (
              <span style={{ fontSize: 12, color: '#6b7280' }}>
                {data.date_from === data.date_to ? data.date_from : `${data.date_from} ~ ${data.date_to}`}
              </span>
            )}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 12, marginBottom: 16 }}>
            <MiniStat icon="🛒" label="매출 (기간)" value={`${formatKRW(t.sales)}원`} color="#0891b2" />
            <MiniStat icon="💸" label="광고비 (기간)" value={`${formatKRW(t.ad_cost)}원`} color="#f59e0b" />
            <MiniStat icon="📦" label="상품순익 (광고 전)" value={`${formatKRW(t.profit)}원`} color="#7c3aed" />
            <MiniStat icon={t.net_after_ad >= 0 ? '🟢' : '🔴'} label="순수익 (광고 차감 후)"
              value={`${t.net_after_ad >= 0 ? '+' : ''}${formatKRW(t.net_after_ad)}원`} color={t.net_after_ad >= 0 ? '#16a34a' : '#dc2626'} />
            <MiniStat icon="🏦" label="총 잔액" sub="예치금+셀러포인트" value={`${formatKRW(t.balance)}원`} color="#0369a1" />
            <MiniStat icon="👥" label="계정 현황" sub={`정상 ${t.normal} / 실패 ${t.failed}`} value={`${t.accounts}개`} color={t.failed > 0 ? '#dc2626' : '#16a34a'} />
          </div>

          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginBottom: 16 }}>
            <div className="ovh-card" style={{ ...CARD, flex: '0 0 290px', padding: 18 }}>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>마켓별 광고비 비중 (기간)</div>
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
                  광고비 없음
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
                    <div><span style={{ fontSize: 12, color: '#6b7280' }}>매출 </span><b style={{ color: '#0891b2' }}>{formatKRW(m.sales || 0)}원</b></div>
                    <div><span style={{ fontSize: 12, color: '#6b7280' }}>광고비 </span><b style={{ color: '#f59e0b' }}>{formatKRW(m.ad_cost)}원</b>
                      {(m.ai || 0) > 0 && <span style={{ fontSize: 11, color: '#9ca3af' }}> (CPC {formatKRW(m.cpc)}/AI {formatKRW(m.ai || 0)})</span>}</div>
                    <div><span style={{ fontSize: 12, color: '#6b7280' }}>순수익 </span>
                      <b style={{ color: (m.net_after_ad || 0) >= 0 ? '#16a34a' : '#dc2626' }}>{(m.net_after_ad || 0) >= 0 ? '+' : ''}{formatKRW(m.net_after_ad || 0)}원</b></div>
                    {m.balance > 0 && <div><span style={{ fontSize: 12, color: '#6b7280' }}>잔액 </span><b style={{ color: '#0369a1' }}>{formatKRW(m.balance)}원</b>
                      {m.key === '11st' && m.cash != null && <span style={{ fontSize: 11, color: '#9ca3af' }}> (셀러캐시 {formatKRW(m.cash)})</span>}</div>}
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

      {modalMall && profit && (
        <MallProductModal
          platform={modalMall.platform}
          label={modalMall.label}
          dateFrom={profit.date_from}
          dateTo={profit.date_to}
          onClose={() => setModalMall(null)}
        />
      )}
    </div>
  );
}

// ── 쇼핑몰 카드 클릭 → 상품별 목록 모달 (전체/적자/우수 + 엑셀다운) ──
function MallProductModal({ platform, label, dateFrom, dateTo, onClose }:
  { platform: string; label: string; dateFrom: string; dateTo: string; onClose: () => void }) {
  const [mode, setMode] = useState<'all' | 'loss' | 'high'>('all');
  const [rows, setRows] = useState<MallProductRow[]>([]);
  const [totals, setTotals] = useState<{ revenue: number; cost: number; net_profit: number; quantity: number; products: number } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getMallProfitProducts({ platform, date_from: dateFrom, date_to: dateTo, mode })
      .then(r => { setRows(r.rows); setTotals(r.totals); })
      .finally(() => setLoading(false));
  }, [platform, dateFrom, dateTo, mode]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const doExport = () => {
    const header = ['상품코드', '상품명', '수량', '매출', '구매가', '순익', '마진율(%)', '주문수'].join(',');
    const lines = [header, ...rows.map(r =>
      [r.product_code, r.product_name, r.quantity, r.revenue, r.cost, r.net_profit, r.margin, r.orders]
        .map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')
    )];
    const csv = '﻿' + lines.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${label}_상품손익_${dateFrom}_${dateTo}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const MODES: { key: 'all' | 'loss' | 'high'; label: string; on: string; off: string }[] = [
    { key: 'all', label: '전체', on: '#334155', off: '#f3f4f6' },
    { key: 'loss', label: '적자', on: '#dc2626', off: '#fee2e2' },
    { key: 'high', label: '우수', on: '#16a34a', off: '#dcfce7' },
  ];

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(15,23,42,.55)', zIndex: 100,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#fff', borderRadius: 16, width: '100%', maxWidth: 920, maxHeight: '85vh',
        display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: '0 20px 60px rgba(0,0,0,.3)',
      }}>
        {/* 헤더 */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #eef0f3', display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 17, fontWeight: 800 }}>{label} 상품별 손익</span>
          <span style={{ fontSize: 12, color: '#9ca3af' }}>{dateFrom === dateTo ? dateFrom : `${dateFrom} ~ ${dateTo}`}</span>
          <div style={{ display: 'flex', gap: 6, marginLeft: 8 }}>
            {MODES.map(m => (
              <button key={m.key} onClick={() => setMode(m.key)}
                style={{
                  padding: '5px 14px', borderRadius: 999, cursor: 'pointer', fontSize: 12.5, fontWeight: 700,
                  border: 'none', color: mode === m.key ? '#fff' : m.on, background: mode === m.key ? m.on : m.off,
                }}>{m.label}</button>
            ))}
          </div>
          <button onClick={doExport}
            style={{ padding: '5px 14px', borderRadius: 8, cursor: 'pointer', fontSize: 12.5, fontWeight: 700, border: '1px solid #d1d5db', background: '#fff', color: '#374151' }}>
            ⬇ 엑셀다운
          </button>
          <button onClick={onClose}
            style={{ marginLeft: 'auto', width: 28, height: 28, borderRadius: 8, border: 'none', background: '#f3f4f6', cursor: 'pointer', fontSize: 15, color: '#6b7280' }}>
            ✕
          </button>
        </div>

        {/* 요약 */}
        {totals && (
          <div style={{ padding: '10px 20px', display: 'flex', gap: 20, flexWrap: 'wrap', fontSize: 12.5, background: '#f8fafc', borderBottom: '1px solid #eef0f3' }}>
            <span style={{ color: '#6b7280' }}>상품 <b style={{ color: '#111' }}>{totals.products.toLocaleString()}</b>개</span>
            <span style={{ color: '#6b7280' }}>매출 <b style={{ color: '#0891b2' }}>{formatKRW(totals.revenue)}원</b></span>
            <span style={{ color: '#6b7280' }}>구매가 <b style={{ color: '#b45309' }}>{formatKRW(totals.cost)}원</b></span>
            <span style={{ color: '#6b7280' }}>순익 <b style={{ color: totals.net_profit >= 0 ? '#16a34a' : '#dc2626' }}>{totals.net_profit >= 0 ? '+' : ''}{formatKRW(totals.net_profit)}원</b></span>
          </div>
        )}

        {/* 테이블 */}
        <div style={{ overflow: 'auto', flex: 1 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead style={{ position: 'sticky', top: 0, background: '#f8fafc', zIndex: 1 }}>
              <tr>
                {['상품명', '수량', '매출', '구매가', '순익', '마진율'].map((h, i) => (
                  <th key={h} style={{ padding: '9px 12px', textAlign: i === 0 ? 'left' : 'right', fontWeight: 700, color: '#6b7280', fontSize: 12, borderBottom: '1px solid #eef0f3', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 48, color: '#9ca3af' }}>{loading ? '불러오는 중...' : '데이터가 없습니다'}</td></tr>
              )}
              {rows.map((r, i) => (
                <tr key={`${r.product_code}-${i}`} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '8px 12px', maxWidth: 320 }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={r.product_name}>{r.product_name}</div>
                    {r.product_code && <div style={{ fontSize: 11, color: '#9ca3af' }}>{r.product_code}</div>}
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', color: '#64748b' }}>{r.quantity.toLocaleString()}</td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', color: '#0891b2', fontWeight: 600 }}>{r.revenue.toLocaleString()}</td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', color: '#b45309' }}>{r.cost.toLocaleString()}</td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700, color: r.net_profit >= 0 ? '#16a34a' : '#dc2626' }}>
                    {r.net_profit >= 0 ? '+' : ''}{r.net_profit.toLocaleString()}
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', color: r.margin >= 0 ? '#16a34a' : '#dc2626' }}>{r.margin}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
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
