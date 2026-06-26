import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSt11Data } from '../../hooks/useSt11Data';
import DateNavigator from '../../components/cpc/DateNavigator';
import DateRangePicker from '../../components/cpc/DateRangePicker';
import St11SummaryBar from '../../components/st11/St11SummaryBar';
import St11SummaryTable from '../../components/st11/St11SummaryTable';
import St11MobileCard from '../../components/st11/St11MobileCard';
import St11CostModal from '../../components/st11/St11CostModal';
import St11GradeModal from '../../components/st11/St11GradeModal';
import St11PeriodSummaryModal from '../../components/st11/St11PeriodSummaryModal';
import { todayStr, formatKRW, ymd } from '../../utils/format';
import api from '../../api/client';

export default function St11Dashboard() {
  const {
    date, setDate, summary, delta,
    selectedSeller, setSelectedSeller,
    loading, prevDate, nextDate, goToday,
    periodMode, setPeriodMode,
    rangeStart, setRangeStart, rangeEnd, setRangeEnd, searchRange,
    refresh,
  } = useSt11Data();

  const [costModal, setCostModal] = useState<{ sellerId: string; alias: string; kind?: string } | null>(null);
  const [showGrade, setShowGrade] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [mobileHideEmpty, setMobileHideEmpty] = useState(false);
  const [blockedSellers, setBlockedSellers] = useState<{ seller_id: string; seller_alias: string }[]>([]);
  const [showBlockedPopup, setShowBlockedPopup] = useState(false);
  const [crawlerStats, setCrawlerStats] = useState<{ total: number; active: number; blocked: number; success: number; pending: number } | null>(null);
  const [crawlRunning, setCrawlRunning] = useState(false);
  const [costLastAt, setCostLastAt] = useState<string>('');
  const [showAuthPanel, setShowAuthPanel] = useState(false);
  const [authData, setAuthData] = useState<{
    accounts: {
      login_id: string;
      seller_name: string;
      last_otp_at: string | null;
      sms_received_at: string | null;
      otp_hours: number | null;
      status: 'ok' | 'warning' | 'expired';
    }[];
    running: boolean;
    running_ids: string[];
  } | null>(null);
  const navigate = useNavigate();

  const onCostClick = useCallback((sellerId: string, alias: string, kind?: string) => setCostModal({ sellerId, alias, kind }), []);
  const onRunCrawl = useCallback(async () => {
    try {
      const r = await api.post('/cpc/crawler/eleven-cost/run/');
      if (r.data?.status === 'started') {
        setCrawlRunning(true);
        alert('광고비 크롤 시작! 매시간 크롤과 동일하게 실행됩니다. 진행 중엔 "강제중지"로 멈출 수 있어요.');
      } else {
        alert(r.data?.error || '시작 실패');
      }
    } catch (e: any) {
      alert(e?.response?.data?.error || '크롤 시작 실패 — 이미 다른 크롤이 실행 중일 수 있습니다.');
    }
  }, []);
  const onStopCrawl = useCallback(async () => {
    if (!window.confirm('실행 중인 광고비 크롤을 강제로 중지할까요?')) return;
    try {
      const r = await api.post('/cpc/crawler/eleven-cost/stop/');
      setCrawlRunning(false);
      alert(r.data?.message || '크롤을 중지했습니다.');
    } catch (e: any) {
      alert(e?.response?.data?.error || '중지 실패');
    }
  }, []);
  const onVerifyOtp = useCallback(async (loginIds?: string[]) => {
    try {
      const body = loginIds ? { login_ids: loginIds } : { auto: true };
      const r = await api.post('/cpc/eleven/verify-otp/', body);
      alert(r.data?.message || `인증 시작 (${r.data?.count ?? 0}개 계정)`);
    } catch (e: any) {
      alert(e?.response?.data?.error || '인증 시작 실패');
    }
  }, []);
  const onGradeCrawl = useCallback(async () => {
    try {
      const r = await api.post('/cpc/crawler/trigger/', { platform: '11st', type: 'grade' });
      alert(r.data?.status === 'started' ? '등급 크롤 시작! 1~2분 후 "등급현황"에서 확인하세요.' : '등급 크롤 시작됨');
    } catch (e: any) {
      alert(e?.response?.data?.error || '등급 크롤 시작 실패 — 다른 크롤이 실행 중일 수 있습니다.');
    }
  }, []);

  useEffect(() => {
    api.get('/cpc/crawler/blocked/', { params: { platform: '11st' } })
      .then(r => {
        if (r.data.blocked?.length > 0) {
          setBlockedSellers(r.data.blocked);
          setShowBlockedPopup(true);
        }
      })
      .catch(() => {});

    api.get('/cpc/crawler/accounts/', { params: { page_size: 200 } })
      .then(r => {
        const accts = (r.data.results || r.data || []).filter((a: any) => a.platform === '11st' && a.is_active);
        const blocked = accts.filter((a: any) => a.crawling_status === '차단됨').length;
        const success = accts.filter((a: any) => a.crawling_status === '정상' && a.last_crawled_at).length;
        const pending = accts.filter((a: any) => a.crawling_status === '대기' || !a.last_crawled_at).length;
        setCrawlerStats({ total: accts.length, active: accts.length, blocked, success, pending });
      })
      .catch(() => {});
  }, []);

  // 인증 현황 30초 폴링
  useEffect(() => {
    const fetch = () => api.get('/cpc/eleven/auth-status/').then(r => setAuthData(r.data)).catch(() => {});
    fetch();
    const t = setInterval(fetch, 30000);
    return () => clearInterval(t);
  }, []);

  // 크롤 실행 상태 폴링 (버튼 표시용)
  useEffect(() => {
    const check = () => api.get('/cpc/crawler/eleven-cost/status/')
      .then(r => { setCrawlRunning(!!r.data?.running); setCostLastAt(r.data?.last_collected_at || ''); }).catch(() => {});
    check();
    const t = setInterval(check, 5000);
    return () => clearInterval(t);
  }, []);

  // 크롤 진행 중이면 데이터도 자동 갱신(계정별 수집분이 DB에 커밋될 때마다 화면 반영).
  // 진행→종료 전환 시 마지막 1회 갱신해 최종값 확정. refresh는 ref로 최신 유지(타이머 리셋 방지).
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  const wasRunningRef = useRef(false);
  useEffect(() => {
    if (crawlRunning) {
      wasRunningRef.current = true;
      const t = setInterval(() => refreshRef.current(), 10000);
      return () => clearInterval(t);
    }
    if (wasRunningRef.current) {
      wasRunningRef.current = false;
      refreshRef.current();
    }
  }, [crawlRunning]);

  const lastCollected = (() => {
    if (!summary?.last_collected_at) return '';
    return summary.last_collected_at.replace('T', ' ').slice(0, 16);
  })();

  const mobileFiltered = summary
    ? mobileHideEmpty
      ? summary.sellers.filter(s => s.cpc_spend > 0 || s.charge > 0 || (s.products || 0) > 0)
      : summary.sellers
    : [];

  const costRange = periodMode === 'range'
    ? { start_date: rangeStart, end_date: rangeEnd }
    : periodMode === 'yearly'
      ? { start_date: `${date.slice(0, 4)}-01-01`, end_date: `${date.slice(0, 4)}-12-31` }
      : periodMode === 'monthly'
        ? (() => {
            const d = new Date(date);
            return {
              start_date: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`,
              end_date: ymd(new Date(d.getFullYear(), d.getMonth() + 1, 0)),
            };
          })()
        : undefined;

  const blockedSet = new Set(blockedSellers.map(b => b.seller_id));

  return (
    <div className="min-h-screen bg-[#f5f5f5]">
      {/* 차단 계정 팝업 */}
      {showBlockedPopup && blockedSellers.length > 0 && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40" onClick={() => setShowBlockedPopup(false)}>
          <div className="bg-white rounded-xl p-7 max-w-[440px] w-[90%] shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-4">
              <span className="text-[22px]">&#9888;</span>
              <span className="text-[12px] font-bold text-[#dc2626]">11번가 계정 차단 알림</span>
            </div>
            {blockedSellers.map(b => (
              <div key={b.seller_id} className="flex items-center justify-between p-2 mb-1.5 bg-[#fef2f2] border border-[#fecaca] rounded">
                <div>
                  <span className="font-bold text-[#dc2626]">{b.seller_alias}</span>
                  <span className="text-[#666] ml-1.5 text-[12px]">({b.seller_id})</span>
                </div>
                <button onClick={() => {
                  api.post('/cpc/crawler/blocked/', { seller_id: b.seller_id }).then(() => {
                    const updated = blockedSellers.filter(x => x.seller_id !== b.seller_id);
                    setBlockedSellers(updated);
                    if (updated.length === 0) setShowBlockedPopup(false);
                  }).catch(() => {});
                }} className="px-2.5 py-1 bg-[#16a34a] text-white rounded text-[11px] font-semibold">해제</button>
              </div>
            ))}
            <div className="text-right mt-4">
              <button onClick={() => setShowBlockedPopup(false)} className="px-5 py-1.5 bg-[#dc2626] text-white rounded-md font-semibold text-[12px]">확인</button>
            </div>
          </div>
        </div>
      )}

      {/* 날짜 네비게이션 바 */}
      <div className="bg-white border-b border-[#e0e0e0] px-4 md:px-6 py-2">
        <div className="flex items-center justify-between max-w-[1800px] mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-sm" style={{ background: '#e67700' }} />
            <h1 className="text-[12px] font-bold text-[#333]">11번가 대시보드</h1>
            {summary && (
              <button onClick={() => setShowSummary(true)}
                className="px-2.5 py-1 text-[11px] font-bold bg-[#e67700] text-white rounded hover:bg-[#bf5600]">
                📋 기간 요약
              </button>
            )}
            {loading && <span className="text-[11px] text-[#999] animate-pulse">로딩중...</span>}
          </div>
          {periodMode === 'range' ? (
            <DateRangePicker startDate={rangeStart} endDate={rangeEnd}
              onStartChange={setRangeStart} onEndChange={setRangeEnd} onSearch={searchRange} />
          ) : (
            <DateNavigator date={date} onPrev={prevDate} onNext={nextDate} onToday={goToday} onDateChange={setDate} periodMode={periodMode} />
          )}
        </div>
      </div>

      {/* PC 레이아웃 */}
      <div className="hidden md:block max-w-[1800px] mx-auto px-6 py-3 space-y-2">
        {summary && (
          <>
            <St11SummaryBar
              totals={summary.totals} delta={delta} lastCollected={lastCollected}
              periodMode={periodMode} onPeriodChange={setPeriodMode} onRefresh={refresh}
            />

            {/* 크롤링 현황 바 (한 줄) */}
            {crawlerStats && (
              <div className="bg-white border border-[#e0e0e0] rounded px-5 py-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] md:text-[12px]">
                <span className="font-bold text-[#333]">크롤링 현황</span>
                <button onClick={onGradeCrawl}
                  className="px-2.5 py-1 text-[12px] font-semibold bg-[#e67700] text-white rounded hover:bg-[#bf5600]">등급 크롤</button>
                <span className="text-[#888]">전체 <b className="text-[#333]">{crawlerStats.total}</b></span>
                <span className="text-[#888]">수집완료 <b className="text-[#00a651]">{crawlerStats.success}</b></span>
                <span className="text-[#888]">대기 <b className="text-[#e08000]">{crawlerStats.pending}</b></span>
                {crawlerStats.blocked > 0 && (
                  <span className="text-[#888]">차단 <b className="text-[#dc2626]">{crawlerStats.blocked}</b></span>
                )}
                {costLastAt && (
                  <span className="text-[#888]">광고비 최종수집 <b className="text-[#1e6fd9]">{costLastAt.replace('T', ' ').slice(5, 16)}</b></span>
                )}
                <span className="mx-auto text-[#888]">⏱ 매일 <b className="text-[#e67700]">11·15·17·18·20·22시</b> · 등급 <b className="text-[#e67700]">1·2일 10시</b></span>
                <button onClick={onRunCrawl} disabled={crawlRunning}
                  className="px-2.5 py-1 text-[12px] font-semibold bg-[#00a651] text-white rounded hover:bg-[#008a44] disabled:opacity-40 disabled:cursor-not-allowed">
                  {crawlRunning ? '크롤링 중…' : '크롤링'}</button>
                <button onClick={onStopCrawl} disabled={!crawlRunning}
                  className="px-2.5 py-1 text-[12px] font-semibold bg-[#dc2626] text-white rounded hover:bg-[#b91c1c] disabled:opacity-40 disabled:cursor-not-allowed">강제중지</button>
                <button onClick={() => navigate('/st11-roas')}
                  className="px-2.5 py-1 text-[12px] font-semibold bg-[#1e6fd9] text-white rounded hover:bg-[#1857ad]">ROAS</button>
                <button onClick={() => setShowGrade(true)}
                  className="px-2.5 py-1 text-[12px] font-semibold bg-[#555] text-white rounded hover:bg-[#444]">등급현황</button>
              </div>
            )}

            {/* 인증(로그인) 현황 */}
            {authData && (() => {
              const expired = authData.accounts.filter(a => a.status === 'expired').length;
              const warning = authData.accounts.filter(a => a.status === 'warning').length;
              const toKst = (iso: string | null) => {
                if (!iso) return '-';
                const d = new Date(iso);
                return d.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).replace(/\. /g, '-').replace('.', '');
              };
              return (
                <div className="bg-white border border-[#e0e0e0] rounded">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-1.5 cursor-pointer select-none"
                    onClick={() => setShowAuthPanel(p => !p)}>
                    <span className="font-bold text-[#333] text-[12px]">인증(로그인) 현황</span>
                    {expired > 0 && <span className="text-[11px] font-bold text-[#dc2626]">만료 {expired}개</span>}
                    {warning > 0 && <span className="text-[11px] font-bold text-[#d97706]">경고 {warning}개</span>}
                    {authData.running && (
                      <span className="text-[11px] text-[#1e6fd9] animate-pulse font-semibold">인증 진행 중…</span>
                    )}
                    <button
                      onClick={e => { e.stopPropagation(); onVerifyOtp(); }}
                      disabled={authData.running}
                      className="ml-auto px-2.5 py-1 text-[11px] font-semibold bg-[#e67700] text-white rounded hover:bg-[#bf5600] disabled:opacity-40 disabled:cursor-not-allowed">
                      만료계정 자동인증
                    </button>
                    <span className="text-[11px] text-[#999]">{showAuthPanel ? '▲' : '▼'}</span>
                  </div>
                  {showAuthPanel && (
                    <div className="border-t border-[#e0e0e0] px-4 py-3">
                      <div className="grid gap-1" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }}>
                        {authData.accounts.map(a => {
                          const bg = a.status === 'expired' ? 'bg-[#fef2f2] border-[#fecaca]'
                            : a.status === 'warning' ? 'bg-[#fffbeb] border-[#fde68a]'
                            : 'bg-[#f0fdf4] border-[#bbf7d0]';
                          const nameColor = a.status === 'expired' ? 'text-[#dc2626]'
                            : a.status === 'warning' ? 'text-[#d97706]'
                            : 'text-[#16a34a]';
                          const isRunning = authData.running_ids.includes(a.login_id);
                          return (
                            <div key={a.login_id} className={`border rounded p-2 text-[11px] ${bg}`}>
                              <div className="flex items-center justify-between mb-0.5">
                                <span className={`font-bold ${nameColor}`}>{a.seller_name}</span>
                                {isRunning
                                  ? <span className="text-[10px] text-[#1e6fd9] animate-pulse">인증중…</span>
                                  : <button
                                      onClick={() => onVerifyOtp([a.login_id])}
                                      disabled={authData.running}
                                      className="text-[10px] px-1.5 py-0.5 bg-[#e67700] text-white rounded disabled:opacity-40">
                                      인증
                                    </button>
                                }
                              </div>
                              <div className="text-[#666]">
                                {a.otp_hours !== null ? `${a.otp_hours}h 전` : '미인증'}
                                {a.otp_hours !== null && ` · ${toKst(a.sms_received_at ?? a.last_otp_at)}`}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}

            <St11SummaryTable
              sellers={summary.sellers} totals={summary.totals}
              unmatched={summary.unmatched}
              selectedSeller={selectedSeller} onSelectSeller={setSelectedSeller}
              onCostClick={onCostClick} blockedIds={blockedSet}
              onDismissBlocked={sid => {
                api.post('/cpc/crawler/blocked/', { seller_id: sid }).then(() =>
                  setBlockedSellers(prev => prev.filter(b => b.seller_id !== sid))
                ).catch(() => {});
              }}
            />
          </>
        )}
      </div>

      {/* 모바일 레이아웃 */}
      <div className="md:hidden px-2 py-3 space-y-2">
        {summary && (
          <>
            <St11SummaryBar
              totals={summary.totals} delta={delta} lastCollected={lastCollected}
              periodMode={periodMode} onPeriodChange={setPeriodMode} onRefresh={refresh}
            />
            <div className="bg-white border border-[#e0e0e0] rounded p-3">
              <div className="flex items-center justify-between text-[11px] mb-1">
                <span className="text-[#333] font-bold text-[12px] cursor-pointer" onClick={() => setMobileHideEmpty(h => !h)}>
                  합계 <span className="ml-1 text-[10px] text-[#999] font-normal">{mobileHideEmpty ? `${mobileFiltered.length}개만` : `${summary.sellers.length}개`}</span>
                </span>
                <span className="text-[12px] font-bold text-[#e67700]">
                  CPC {formatKRW(summary.totals.cpc_spend)}
                </span>
              </div>
              <div className="flex items-center gap-3 text-[10px] text-[#666]">
                <span>잔액 <b className="text-[#333]">{formatKRW(summary.totals.balance)}</b></span>
                <span>셀러 <b className="text-[#333]">{summary.totals.seller_count}개</b></span>
                <button onClick={() => setShowGrade(true)} className="ml-auto text-[10px] text-[#e67700] font-bold">등급</button>
              </div>
            </div>
            <div className="bg-white border border-[#e0e0e0] rounded overflow-hidden">
              <div className="flex items-center justify-between px-3 py-2 bg-[#f7f7f7] border-b border-[#e0e0e0] cursor-pointer"
                onClick={() => setMobileHideEmpty(h => !h)}>
                <span className="text-[12px] font-bold text-[#333]">
                  셀러명 <span className="ml-1.5 text-[10px] font-normal text-[#999]">{mobileHideEmpty ? `활동 ${mobileFiltered.length}개` : `전체 ${summary.sellers.length}개`}</span>
                </span>
                <span className={`text-[10px] px-1.5 py-[1px] rounded ${mobileHideEmpty ? 'bg-[#fff3e0] text-[#e67700] font-bold' : 'text-[#999]'}`}>
                  {mobileHideEmpty ? '활동만' : '전체보기'}
                </span>
              </div>
              {mobileFiltered.map((s, i) => (
                <St11MobileCard key={s.seller_id} seller={s} index={i + 1}
                  isSelected={selectedSeller === s.seller_id}
                  onSelect={() => setSelectedSeller(selectedSeller === s.seller_id ? null : s.seller_id)}
                  onCostClick={onCostClick} />
              ))}
            </div>
          </>
        )}
      </div>

      {/* 모달 */}
      {costModal && (
        <St11CostModal sellerId={costModal.sellerId} sellerAlias={costModal.alias} kind={costModal.kind}
          date={date} range={costRange} onClose={() => setCostModal(null)} />
      )}
      {showGrade && <St11GradeModal onClose={() => setShowGrade(false)} />}
      {showSummary && summary && (
        <St11PeriodSummaryModal
          totals={summary.totals} periodMode={periodMode} date={date}
          rangeStart={rangeStart} rangeEnd={rangeEnd} lastCollected={lastCollected}
          onClose={() => setShowSummary(false)} />
      )}
    </div>
  );
}
