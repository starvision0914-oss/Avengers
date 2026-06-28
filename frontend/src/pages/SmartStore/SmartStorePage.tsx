import { useEffect, useState, useCallback, useRef } from 'react';
import {
  RefreshCw, Settings, Package,
  ShoppingBag, Lock, BarChart3, Clock,
} from 'lucide-react';
import {
  getAccounts, getDashboard, getProductStats,
  type SmartStoreAccount, type DashboardResponse, type AccountRow, type ProductStats,
} from '../../api/smartstore';
import AccountSettingsModal from './AccountSettingsModal';
import SmartStoreProductsTab from './SmartStoreProductsTab';
import api from '../../api/client';
import DateNavigator from '../../components/cpc/DateNavigator';
import DateRangePicker from '../../components/cpc/DateRangePicker';
import PeriodSelector from '../../components/cpc/PeriodSelector';
import type { PeriodMode } from '../../types/cpc';

const SS = '#03C75A';
const fmt = (n: number) => (n || 0).toLocaleString();
const fmtW = (n: number) => {
  if (Math.abs(n) >= 100_000_000) return (n / 100_000_000).toFixed(1) + '억';
  if (Math.abs(n) >= 10_000) return (n / 10_000).toFixed(0) + '만';
  return fmt(n);
};
const ymd = (d: Date) => {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};
const todayYmd = () => ymd(new Date());
const monthStart = (d: Date) => ymd(new Date(d.getFullYear(), d.getMonth(), 1));
const monthEnd = (d: Date) => ymd(new Date(d.getFullYear(), d.getMonth() + 1, 0));
const yearStart = (d: Date) => `${d.getFullYear()}-01-01`;

export default function SmartStorePage() {
  const [tab, setTab] = useState<'dashboard' | 'products'>('dashboard');
  const [accounts, setAccounts] = useState<SmartStoreAccount[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [dash, setDash] = useState<DashboardResponse | null>(null);
  const [prodStats, setProdStats] = useState<ProductStats | null>(null);
  const [crawlLogs, setCrawlLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [periodMode, setPeriodMode] = useState<PeriodMode>('monthly');
  const [date, setDate] = useState(todayYmd());
  const [rangeStart, setRangeStart] = useState('');
  const [rangeEnd, setRangeEnd] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const getRange = useCallback((mode: PeriodMode, d: string): [string, string] => {
    if (mode === 'range') return [rangeStart || monthStart(new Date()), rangeEnd || todayYmd()];
    if (mode === 'yearly') return [yearStart(new Date(d)), `${new Date(d).getFullYear()}-12-31`];
    if (mode === 'monthly') {
      const dt = new Date(d);
      return [monthStart(dt), monthEnd(dt)];
    }
    return [d, d];
  }, [rangeStart, rangeEnd]);

  const prevDate = () => {
    const dt = new Date(date);
    if (periodMode === 'yearly') dt.setFullYear(dt.getFullYear() - 1);
    else if (periodMode === 'monthly') dt.setMonth(dt.getMonth() - 1);
    else dt.setDate(dt.getDate() - 1);
    setDate(ymd(dt));
  };
  const nextDate = () => {
    const dt = new Date(date);
    if (periodMode === 'yearly') dt.setFullYear(dt.getFullYear() + 1);
    else if (periodMode === 'monthly') dt.setMonth(dt.getMonth() + 1);
    else dt.setDate(dt.getDate() + 1);
    if (ymd(dt) <= todayYmd()) setDate(ymd(dt));
  };
  const goToday = () => setDate(todayYmd());

  const loadAccounts = useCallback(async () => {
    const data = await getAccounts().catch(() => []);
    setAccounts(data);
  }, []);

  const loadCrawlLogs = useCallback(async () => {
    const r = await api.get('/smartstore/crawl-status/').catch(() => ({ data: [] }));
    setCrawlLogs(r.data || []);
  }, []);

  const loadDash = useCallback(async () => {
    setLoading(true);
    const [start, end] = getRange(periodMode, date);
    try {
      const [data, ps] = await Promise.all([
        getDashboard({ start, end, account_id: selectedIds.length > 0 ? selectedIds : undefined }),
        getProductStats(),
      ]);
      setDash(data);
      setProdStats(ps);
    } finally {
      setLoading(false);
    }
  }, [periodMode, date, selectedIds, getRange]);

  useEffect(() => { loadAccounts(); loadCrawlLogs(); }, []);

  useEffect(() => {
    if (tab === 'dashboard') {
      loadDash();
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = setInterval(() => { loadDash(); loadCrawlLogs(); }, 60000);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [tab, loadDash]);

  const s = dash?.summary;
  const byAcc: AccountRow[] = dash?.by_account || [];
  const accountLoginMap = new Map(accounts.map(a => [a.id, a.login_id.split('@')[0]]));
  const [start, end] = getRange(periodMode, date);

  const net = (s?.total_excel_revenue || 0) - (s?.total_ad_cost || 0) - (s?.total_cogs || 0);

  const lastCrawl = (() => {
    const done = crawlLogs.filter(l => l.status === 'done');
    if (!done.length) return null;
    return new Date(done[0].started_at).toLocaleString('ko-KR', {
      timeZone: 'Asia/Seoul', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false,
    });
  })();

  const periodLabel = periodMode === 'range' ? `${start} ~ ${end}` : start !== end ? `${start} ~ ${end}` : start;

  return (
    <div className="min-h-screen bg-[#f5f6fa]">

      {/* ── 상단 날짜 네비게이션 바 ── */}
      <div className="bg-white border-b border-[#e0e0e0] px-4 md:px-6 py-2 sticky top-0 z-30">
        <div className="max-w-[1800px] mx-auto flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm" style={{ background: SS }} />
            <h1 className="text-[13px] font-bold text-[#222]">스마트스토어 대시보드</h1>
            {loading && <span className="text-[11px] text-[#999] animate-pulse">로딩중...</span>}
          </div>
          {periodMode === 'range' ? (
            <DateRangePicker startDate={rangeStart} endDate={rangeEnd}
              onStartChange={setRangeStart} onEndChange={setRangeEnd} onSearch={loadDash} />
          ) : (
            <DateNavigator date={date} onPrev={prevDate} onNext={nextDate} onToday={goToday} onDateChange={setDate} periodMode={periodMode} />
          )}
        </div>
      </div>

      <div className="max-w-[1800px] mx-auto px-4 md:px-6 py-3 space-y-3">

        {/* ── 컨트롤 바 ── */}
        <div className="bg-white border border-[#e0e0e0] rounded px-4 py-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px]">
          <span className="font-bold text-[#333]">스마트스토어</span>
          <span className="text-[#888]">계정 <b className="text-[#333]">{accounts.length}개</b></span>
          {lastCrawl && (
            <span className="flex items-center gap-1 text-[#888]">
              <Clock size={11} />
              수집 <b className="text-[#1e6fd9]">{lastCrawl}</b>
            </span>
          )}
          <span className="text-[#888] hidden md:inline">⏱ 매일 <b style={{ color: SS }}>01:00</b> 자동수집</span>
          <span className="ml-auto flex items-center gap-2">
            <span className="text-[11px] text-[#999]">{periodLabel}</span>
            <button onClick={() => setShowSettings(true)}
              className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold border border-[#d0d0d0] text-[#555] rounded hover:text-[#03C75A] hover:border-[#03C75A] transition-colors">
              <Settings size={12} /> 계정설정
            </button>
            <button onClick={loadDash} disabled={loading}
              className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-white rounded transition-colors"
              style={{ background: loading ? '#aaa' : SS }}>
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> 새로고침
            </button>
            <PeriodSelector value={periodMode} onChange={setPeriodMode} />
          </span>
        </div>

        {/* ── KPI 요약 바 ── */}
        <div className="bg-white border border-[#e0e0e0] rounded">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1 px-4 md:px-5 py-2.5 text-[12px]">
            <SumItem label="매출" value={s?.total_excel_revenue || 0} color={SS} />
            <Sep />
            <span>
              <span className="text-[#888] mr-1">광고비:</span>
              <span className="font-bold text-[#f97316]">{fmtW(s?.total_ad_cost || 0)}원</span>
              {(s?.total_ad_cpc || 0) > 0 && (
                <span className="text-[10px] text-[#aaa] ml-1">(CPC {fmtW(s.total_ad_cpc)})</span>
              )}
              {(s?.total_ad_ai || 0) > 0 && (
                <span className="text-[10px] text-[#6366f1] ml-1">AI {fmtW(s.total_ad_ai)}</span>
              )}
            </span>
            <Sep />
            <SumItem label="결제금액" value={s?.total_sales || 0} color="#888" />
            <Sep />
            {(s?.total_cogs || 0) > 0 && (
              <>
                <SumItem label="구매가" value={s?.total_cogs || 0} color="#0284c7" />
                <Sep />
              </>
            )}
            <span>
              <span className="text-[#888] mr-1">순수익:</span>
              <span className="font-bold" style={{ color: net >= 0 ? '#15803d' : '#dc2626' }}>{fmtW(net)}원</span>
            </span>
            <Sep />
            <span>
              <span className="text-[#888] mr-1">ROAS:</span>
              <span className="font-bold" style={{ color: s?.roas != null && s.roas >= 200 ? '#15803d' : s?.roas != null ? '#dc2626' : '#888' }}>
                {s?.roas != null ? s.roas + '%' : '-'}
              </span>
            </span>
            <Sep />
            <span>
              <span className="text-[#888] mr-1">주문:</span>
              <span className="font-bold text-[#2563eb]">{fmt(s?.total_orders || 0)}건</span>
            </span>
            <Sep />
            <span>
              <span className="text-[#888] mr-1">취소:</span>
              <span className="font-bold text-[#dc2626]">{fmtW(s?.total_cancel || 0)}원</span>
            </span>
            {accounts.filter(a => !a.has_pw).length > 0 && (
              <>
                <Sep />
                <span className="text-[#dc2626] font-semibold text-[11px]">⚠ 비번미등록 {accounts.filter(a => !a.has_pw).length}개</span>
              </>
            )}
            <span className="ml-auto">
              <button onClick={() => setTab('products')}
                className="px-3 py-1 text-[11px] font-semibold text-white rounded"
                style={{ background: SS }}>
                상품관리 →
              </button>
            </span>
          </div>
        </div>

        {/* ── 계정별 테이블 ── */}
        <div className="grid grid-cols-1 gap-3">

          <div className="bg-white border border-[#e0e0e0] rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-[#f0f0f0] flex items-center gap-2">
              <BarChart3 size={15} style={{ color: SS }} />
              <span className="text-[12px] font-bold text-[#222]">계정별 현황</span>
              <span className="text-[11px] text-[#999]">{periodLabel}</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead className="bg-[#fafafa]">
                  <tr className="text-[#666]">
                    <th className="px-4 py-2.5 text-left font-semibold">계정</th>
                    <th className="px-4 py-2.5 text-right font-semibold" style={{ color: SS }}>매출</th>
                    <th className="px-4 py-2.5 text-right font-semibold text-[#f97316]">CPC</th>
                    <th className="px-4 py-2.5 text-right font-semibold text-[#6366f1]">AI</th>
                    <th className="px-4 py-2.5 text-right font-semibold text-[#0284c7]">구매가</th>
                    <th className="px-4 py-2.5 text-right font-semibold">순수익</th>
                    <th className="px-4 py-2.5 text-right font-semibold">ROAS</th>
                    <th className="px-4 py-2.5 text-right font-semibold">주문</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f5f5f5]">
                  {byAcc.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-10 text-center text-[#aaa] text-[12px]">
                        데이터 없음 — 크롤링 후 표시됩니다
                      </td>
                    </tr>
                  ) : (
                    byAcc.map(row => {
                      const cpc = row.ad_cpc || 0;
                      const ai  = row.ad_ai  || 0;
                      const cogs = row.cogs || 0;
                      const excelRev = row.excel_revenue || 0;
                      const rowNet = excelRev - cpc - ai - cogs;
                      return (
                        <tr key={row.account_id} className="hover:bg-[#fafff8] transition-colors">
                          <td className="px-4 py-2.5">
                            <span className="font-semibold text-[#333]">{row.account_name}</span>
                            <span className="text-[10px] text-[#aaa] ml-1.5">{accountLoginMap.get(row.account_id) || ''}</span>
                          </td>
                          <td className="px-4 py-2.5 text-right font-semibold" style={{ color: SS }}>{excelRev > 0 ? fmt(excelRev) : <span className="text-[#ccc]">-</span>}</td>
                          <td className="px-4 py-2.5 text-right text-[#f97316]">{cpc > 0 ? fmt(cpc) : '-'}</td>
                          <td className="px-4 py-2.5 text-right text-[#6366f1]">{ai > 0 ? fmt(ai) : '-'}</td>
                          <td className="px-4 py-2.5 text-right text-[#0284c7]">
                            {cogs > 0 ? fmt(cogs) : <span className="text-[#ccc]">-</span>}
                          </td>
                          <td className={`px-4 py-2.5 text-right font-semibold ${rowNet >= 0 ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>{fmt(rowNet)}</td>
                          <td className={`px-4 py-2.5 text-right font-bold ${row.roas != null && row.roas >= 200 ? 'text-[#16a34a]' : row.roas != null ? 'text-[#dc2626]' : 'text-[#aaa]'}`}>
                            {row.roas != null ? row.roas + '%' : '-'}
                          </td>
                          <td className="px-4 py-2.5 text-right text-[#555]">{fmt(row.orders)}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
                {byAcc.length > 0 && (
                  <tfoot className="bg-[#f5f5f5]">
                    <tr className="font-bold text-[#333]">
                      <td className="px-4 py-2.5">합계 ({byAcc.length}개)</td>
                      <td className="px-4 py-2.5 text-right" style={{ color: SS }}>{fmt(s?.total_excel_revenue || 0)}</td>
                      <td className="px-4 py-2.5 text-right text-[#f97316]">{fmt(s?.total_ad_cpc || 0)}</td>
                      <td className="px-4 py-2.5 text-right text-[#6366f1]">{fmt(s?.total_ad_ai || 0)}</td>
                      <td className="px-4 py-2.5 text-right text-[#0284c7]">{fmt(s?.total_cogs || 0)}</td>
                      <td className={`px-4 py-2.5 text-right ${net >= 0 ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>{fmt(net)}</td>
                      <td className={`px-4 py-2.5 text-right ${s?.roas != null && s.roas >= 200 ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>
                        {s?.roas != null ? s.roas + '%' : '-'}
                      </td>
                      <td className="px-4 py-2.5 text-right">{fmt(s?.total_orders || 0)}</td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </div>

        </div>

        {/* ── 상품 현황 ── */}
        {prodStats && prodStats.total > 0 && (
          <div className="bg-white border border-[#e0e0e0] rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Package size={15} style={{ color: SS }} />
              <span className="text-[12px] font-bold text-[#222]">상품 현황</span>
              <span className="text-[11px] text-[#999]">총 {fmt(prodStats.total)}개</span>
              <button onClick={() => setTab('products')} className="ml-auto text-[11px] font-semibold underline" style={{ color: SS }}>
                상품관리 →
              </button>
            </div>
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
              {Object.entries(prodStats.by_status).map(([st, cnt]) => {
                const labels: Record<string, string> = { SALE: '판매중', SUSPENSION: '판매중지', OUTOFSTOCK: '품절', WAIT: '대기', PROHIBITION: '금지' };
                const colors: Record<string, string> = { SALE: SS, SUSPENSION: '#dc2626', OUTOFSTOCK: '#f97316', WAIT: '#6b7280', PROHIBITION: '#7c3aed' };
                return (
                  <div key={st} className="bg-[#f8fafb] rounded-lg p-3 text-center border border-[#eee]">
                    <div className="text-[10px] text-[#888] mb-1">{labels[st] || st}</div>
                    <div className="text-[18px] font-bold" style={{ color: colors[st] || '#555' }}>{fmt(cnt)}</div>
                  </div>
                );
              })}
            </div>

            {/* 계정별 상품 수 */}
            {prodStats.by_account.length > 0 && (
              <div className="mt-3 pt-3 border-t border-[#f0f0f0]">
                <div className="text-[11px] text-[#888] mb-2">계정별 상품 수</div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {prodStats.by_account.map(a => (
                    <div key={a.account_id} className="flex items-center justify-between px-3 py-1.5 bg-[#f5f5f5] rounded-lg text-[11px]">
                      <span className="text-[#555] font-medium truncate">{a.account_name}</span>
                      <span className="font-bold text-[#333] shrink-0 ml-2">{fmt(a.count)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── 비밀번호 미등록 경고 ── */}
        {accounts.filter(a => !a.has_pw).length > 0 && (
          <div className="bg-[#fffbeb] border border-[#fde68a] rounded-xl p-4 flex items-start gap-3">
            <Lock size={16} className="text-[#d97706] mt-0.5 shrink-0" />
            <div>
              <div className="text-[12px] font-bold text-[#d97706] mb-1">비밀번호 미등록 계정 — 크롤링 불가</div>
              <div className="flex flex-wrap gap-1.5">
                {accounts.filter(a => !a.has_pw).map(a => (
                  <span key={a.id} className="px-2 py-0.5 rounded bg-[#fef3c7] text-[#92400e] text-[11px] font-medium">{a.display_name}</span>
                ))}
              </div>
              <button onClick={() => setShowSettings(true)} className="mt-2 text-[11px] text-[#d97706] font-semibold underline">
                계정설정에서 비밀번호 입력 →
              </button>
            </div>
          </div>
        )}

      </div>

      {/* ── 탭 전환 (상품관리) ── */}
      {tab === 'products' && (
        <div className="fixed inset-0 z-40 bg-[#f5f6fa] overflow-auto">
          <div className="bg-white border-b border-[#e0e0e0] px-6 py-3 flex items-center gap-3">
            <button onClick={() => setTab('dashboard')}
              className="flex items-center gap-1 text-[12px] text-[#555] hover:text-[#333] font-semibold">
              <ChevronLeft size={16} /> 대시보드로
            </button>
            <div className="w-px h-4 bg-[#e0e0e0]" />
            <ShoppingBag size={15} style={{ color: SS }} />
            <span className="text-[13px] font-bold text-[#222]">스마트스토어 상품관리</span>
          </div>
          <div className="px-4 md:px-6 py-4">
            <SmartStoreProductsTab accounts={accounts} />
          </div>
        </div>
      )}

      {showSettings && (
        <AccountSettingsModal
          accounts={accounts}
          onClose={() => { setShowSettings(false); loadAccounts(); }}
          onSaved={loadAccounts}
        />
      )}
    </div>
  );
}

function SumItem({ label, value, color }: { label: string; value: number; color?: string }) {
  const fmtW = (n: number) => {
    if (Math.abs(n) >= 100_000_000) return (n / 100_000_000).toFixed(1) + '억';
    if (Math.abs(n) >= 10_000) return (n / 10_000).toFixed(0) + '만';
    return n.toLocaleString();
  };
  return (
    <span>
      <span className="text-[#888] mr-1">{label}:</span>
      <span className="font-bold" style={{ color: color || '#e67700' }}>{fmtW(value)}원</span>
    </span>
  );
}

function Sep() {
  return <span className="text-[#ddd] hidden md:inline">|</span>;
}
