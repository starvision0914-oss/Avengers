import { useState, useCallback, useEffect } from 'react';
import { useCpcData } from '../../hooks/useCpcData';
import DateNavigator from '../../components/cpc/DateNavigator';
import DateRangePicker from '../../components/cpc/DateRangePicker';
import SummaryBar from '../../components/cpc/SummaryBar';
import AdSummaryTable from '../../components/cpc/AdSummaryTable';
import MobileSellerCard from '../../components/cpc/MobileSellerCard';
import CpcTimeChart from '../../components/cpc/CpcTimeChart';
import AiHistoryModal from '../../components/cpc/AiHistoryModal';
import AiManageModal from '../../components/cpc/AiManageModal';
import SellerGradeModal from '../../components/cpc/SellerGradeModal';
import GmarketAdCostModal from '../../components/cpc/GmarketAdCostModal';
import { todayStr, formatKRW, ymd } from '../../utils/format';
import api from '../../api/client';

export default function CPCDashboard() {
  const {
    date, setDate, summary, timeseries, salesTimeseries, delta,
    selectedSeller, setSelectedSeller,
    loading, prevDate, nextDate, goToday,
    tgMode, setTgMode, tgStatus, manualSend,
    periodMode, setPeriodMode,
    rangeStart, setRangeStart, rangeEnd, setRangeEnd, searchRange,
  } = useCpcData();

  const [mobileHideEmpty, setMobileHideEmpty] = useState(false);
  const [aiModal, setAiModal] = useState<{ sellerId: string; alias: string } | null>(null);
  const [costModal, setCostModal] = useState<{ sellerId: string; alias: string; category?: string } | null>(null);
  const [showAiManage, setShowAiManage] = useState(false);
  const [showSellerGrade, setShowSellerGrade] = useState(false);
  const [blockedSellers, setBlockedSellers] = useState<{ seller_id: string; seller_alias: string }[]>([]);
  const [showBlockedPopup, setShowBlockedPopup] = useState(false);

  const onAiClick = useCallback((sellerId: string, alias: string) => setAiModal({ sellerId, alias }), []);
  const onCostClick = useCallback((sellerId: string, alias: string, category?: string) => setCostModal({ sellerId, alias, category }), []);

  useEffect(() => {
    api.get('/cpc/crawler/blocked/').then(r => {
      if (r.data.blocked?.length > 0) {
        setBlockedSellers(r.data.blocked);
        setShowBlockedPopup(true);
      }
    }).catch(() => {});
  }, []);

  const selectedSellerData = summary?.sellers.find(s => s.seller_id === selectedSeller);
  const sellerAlias = selectedSellerData?.seller_alias ?? '';
  const isToday = periodMode === 'daily' && date === todayStr();

  const lastCollected = (() => {
    if (!summary) return '';
    const times = summary.sellers.map(s => s.last_tx).filter(Boolean) as string[];
    if (!times.length) return '';
    return times.sort().pop()!.replace('T', ' ');
  })();

  const mobileFiltered = summary
    ? mobileHideEmpty
      ? summary.sellers.filter(s => s.ad_total > 0 || s.sales > 0)
      : summary.sellers
    : [];

  const showChart = periodMode === 'daily' && selectedSeller && timeseries.length > 0;
  const blockedSet = new Set(blockedSellers.map(b => b.seller_id));

  const costRange = periodMode === 'range'
    ? { start_date: rangeStart, end_date: rangeEnd }
    : periodMode === 'yearly'
      ? { start_date: `${date.slice(0, 4)}-01-01`, end_date: `${date.slice(0, 4)}-12-31` }
      : periodMode === 'monthly'
        ? (() => { const d = new Date(date); return { start_date: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`, end_date: ymd(new Date(d.getFullYear(), d.getMonth() + 1, 0)) }; })()
        : undefined;

  return (
    <div className="min-h-screen bg-[#f5f5f5]">
      {/* 차단 계정 팝업 */}
      {showBlockedPopup && blockedSellers.length > 0 && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40" onClick={() => setShowBlockedPopup(false)}>
          <div className="bg-white rounded-xl p-7 max-w-[440px] w-[90%] shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-4">
              <span className="text-[22px]">&#9888;</span>
              <span className="text-[12px] font-bold text-[#dc2626]">지마켓 계정 차단 알림</span>
            </div>
            {blockedSellers.map(b => (
              <div key={b.seller_id} className="flex items-center justify-between p-2 mb-1.5 bg-[#fef2f2] border border-[#fecaca] rounded">
                <div>
                  <span className="font-bold text-[#dc2626]">{b.seller_alias}</span>
                  <span className="text-[#666] ml-1.5 text-[12px]">({b.seller_id})</span>
                  <span className="text-[#dc2626] ml-1 text-[12px]">차단됨</span>
                </div>
                <button onClick={() => {
                  api.post('/cpc/crawler/blocked/', { seller_id: b.seller_id }).then(() => {
                    const updated = blockedSellers.filter(x => x.seller_id !== b.seller_id);
                    setBlockedSellers(updated);
                    if (updated.length === 0) setShowBlockedPopup(false);
                  }).catch(() => {});
                }} className="px-2.5 py-1 bg-[#16a34a] text-white rounded text-[11px] font-semibold hover:bg-[#15803d]">해제</button>
              </div>
            ))}
            <p className="mt-3 text-[12px] text-[#555] leading-relaxed">
              2차인증 혹은 비밀번호를 변경하고 차단을 풀어주세요.
            </p>
            <div className="text-right mt-4">
              <button onClick={() => setShowBlockedPopup(false)} className="px-5 py-1.5 bg-[#dc2626] text-white rounded-md font-semibold text-[12px] hover:bg-[#b91c1c]">확인</button>
            </div>
          </div>
        </div>
      )}

      {/* 날짜 네비게이션 바 */}
      <div className="bg-white border-b border-[#e0e0e0] px-4 md:px-6 py-2">
        <div className="flex items-center justify-between max-w-[1800px] mx-auto">
          <div className="flex items-center gap-3">
            <h1 className="text-[12px] font-bold text-[#333]">지마켓 대시보드</h1>
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
      <div className="hidden md:block max-w-[1800px] mx-auto px-6 py-5 space-y-4">
        {summary && (
          <>
            <SummaryBar
              totals={summary.totals} delta={delta} lastCollected={lastCollected}
              tgMode={tgMode} onTgModeChange={setTgMode} tgStatus={tgStatus} onManualSend={manualSend}
              periodMode={periodMode} onPeriodChange={setPeriodMode}
              onAiManage={() => setShowAiManage(true)}
              onSellerGrade={() => setShowSellerGrade(true)}
            />
            <AdSummaryTable
              sellers={summary.sellers} totals={summary.totals}
              selectedSeller={selectedSeller} onSelectSeller={setSelectedSeller}
              onAiClick={onAiClick} onCostClick={onCostClick}
              blockedIds={blockedSet}
              onDismissBlocked={sid => {
                api.post('/cpc/crawler/blocked/', { seller_id: sid }).then(() =>
                  setBlockedSellers(prev => prev.filter(b => b.seller_id !== sid))
                ).catch(() => {});
              }}
            />
            {showChart && (
              <CpcTimeChart data={timeseries} salesData={salesTimeseries} sellerAlias={sellerAlias} />
            )}
            {selectedSellerData?.grade_info && (
              <div className="bg-white border border-[#e0e0e0] rounded px-5 py-3 flex items-center gap-6 text-[12px]">
                <span className="font-bold text-[#333]">{selectedSellerData.seller_alias}</span>
                <span className="text-[#666]">등급 <b className={selectedSellerData.grade_info.seller_grade === '파워이딜러' ? 'text-[#e04040]' : 'text-[#333]'}>{selectedSellerData.grade_info.seller_grade}</b></span>
                <span className="text-[#666]">최대수량 <b className={selectedSellerData.grade_info.max_item_count && selectedSellerData.grade_info.max_item_count >= 10000 ? 'text-[#e04040] font-bold' : 'text-[#333]'}>{selectedSellerData.grade_info.max_item_count?.toLocaleString() ?? '-'}개</b></span>
                <span className="text-[#666]">승인 <b className={selectedSellerData.grade_info.approval_status === '승인' ? 'text-[#00a651]' : 'text-[#e04040]'}>{selectedSellerData.grade_info.approval_status ?? '-'}</b></span>
                {selectedSellerData.grade_info.contact_expiry && (
                  <span className="text-[#666]">연락처인증 <b className="text-[#e08000]">{selectedSellerData.grade_info.contact_expiry}</b></span>
                )}
                <span className="text-[#aaa] text-[10px] ml-auto">수집 {selectedSellerData.grade_info.collected_at}</span>
              </div>
            )}
          </>
        )}
      </div>

      {/* 모바일 레이아웃 */}
      <div className="md:hidden px-2 py-3 space-y-2">
        {summary && (
          <>
            <SummaryBar
              totals={summary.totals} delta={delta} lastCollected={lastCollected}
              tgMode={tgMode} onTgModeChange={setTgMode} tgStatus={tgStatus} onManualSend={manualSend}
              periodMode={periodMode} onPeriodChange={setPeriodMode}
              onAiManage={() => setShowAiManage(true)}
              onSellerGrade={() => setShowSellerGrade(true)}
            />
            <div className="bg-white border border-[#e0e0e0] rounded p-3">
              <div className="flex items-center justify-between text-[11px] mb-1">
                <span className="text-[#333] font-bold text-[12px] cursor-pointer" onClick={() => setMobileHideEmpty(h => !h)}>
                  합계 <span className="ml-1 text-[10px] text-[#999] font-normal">{mobileHideEmpty ? `${mobileFiltered.length}개만` : `${summary.sellers.length}개`}</span>
                </span>
                <span className={`text-[12px] font-bold ${summary.totals.net_profit < 0 ? 'text-[#e04040]' : 'text-[#00a651]'}`}>
                  순이익 {formatKRW(summary.totals.net_profit)}
                </span>
              </div>
              <div className="flex items-center gap-3 text-[10px] text-[#666]">
                <span>CPC <b className="text-[#1a73e8]">{formatKRW(summary.totals.cpc_spend)}</b></span>
                <span>AI <b className="text-[#1a73e8]">{formatKRW(summary.totals.ai_spend)}</b></span>
                <span>광고비 <b className="text-[#1557b0]">{formatKRW(summary.totals.ad_total)}</b></span>
              </div>
            </div>
            <div className="bg-white border border-[#e0e0e0] rounded overflow-hidden">
              <div className="flex items-center justify-between px-3 py-2 bg-[#f7f7f7] border-b border-[#e0e0e0] cursor-pointer"
                onClick={() => setMobileHideEmpty(h => !h)}>
                <span className="text-[12px] font-bold text-[#333]">
                  셀러명 <span className="ml-1.5 text-[10px] font-normal text-[#999]">{mobileHideEmpty ? `활동 ${mobileFiltered.length}개` : `전체 ${summary.sellers.length}개`}</span>
                </span>
                <span className={`text-[10px] px-1.5 py-[1px] rounded ${mobileHideEmpty ? 'bg-[#e7f5ff] text-[#228be6] font-bold' : 'text-[#999]'}`}>
                  {mobileHideEmpty ? '활동만' : '전체보기'}
                </span>
              </div>
              {mobileFiltered.map((s, i) => (
                <MobileSellerCard key={s.seller_id} seller={s} index={i + 1}
                  isSelected={selectedSeller === s.seller_id}
                  onSelect={() => setSelectedSeller(selectedSeller === s.seller_id ? null : s.seller_id)}
                  onAiClick={onAiClick} onCostClick={onCostClick} />
              ))}
            </div>
            {showChart && <CpcTimeChart data={timeseries} salesData={salesTimeseries} sellerAlias={sellerAlias} />}
          </>
        )}
      </div>

      {/* 모달들 */}
      {costModal && (
        <GmarketAdCostModal sellerId={costModal.sellerId} sellerAlias={costModal.alias}
          date={date} range={costRange} category={costModal.category} onClose={() => setCostModal(null)} />
      )}
      {showAiManage && <AiManageModal onClose={() => setShowAiManage(false)} />}
      {showSellerGrade && <SellerGradeModal onClose={() => setShowSellerGrade(false)} />}
      {aiModal && <AiHistoryModal sellerId={aiModal.sellerId} sellerAlias={aiModal.alias} onClose={() => setAiModal(null)} />}
    </div>
  );
}
