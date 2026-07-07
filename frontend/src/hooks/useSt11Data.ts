import { useState, useEffect, useCallback, useRef } from 'react';
import { getSt11Summary, getSt11Last15Min } from '../api/eleven';
import { todayStr, ymd } from '../utils/format';
import type { St11SummaryResponse, St11Last15MinResponse } from '../types/st11';
import type { PeriodMode, PeriodPreset } from '../utils/periodRange';
import { resolveRange, yesterdayStr } from '../utils/periodRange';

const REFRESH_INTERVAL = 30 * 60 * 1000;
const EMPTY_DELTA: St11Last15MinResponse = { cpc_delta: 0, ad_delta: 0, sales_delta: 0 };

export function useSt11Data() {
  const [date, setDate] = useState(todayStr);
  // Overview/G마켓/스마트스토어와 동일한 기본 진입 화면(당월)로 통일
  const [periodMode, setPeriodMode] = useState<PeriodMode>('monthly');
  const [rangeStart, setRangeStart] = useState(todayStr);
  const [rangeEnd, setRangeEnd] = useState(todayStr);
  const [summary, setSummary] = useState<St11SummaryResponse | null>(null);
  const [delta, setDelta] = useState<St11Last15MinResponse>(EMPTY_DELTA);
  const [selectedSeller, setSelectedSeller] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAll = useCallback(async (d: string, mode: PeriodMode, rStart: string, rEnd: string) => {
    setLoading(true);
    try {
      let range: { start_date: string; end_date: string } | undefined;
      if (mode !== 'daily') {
        const r = resolveRange(mode, d, rStart, rEnd);
        range = { start_date: r.from, end_date: r.to };
      }

      const data = await getSt11Summary(d, range);
      setSummary(data);

      if (mode === 'daily' && d === todayStr()) {
        const dt = await getSt11Last15Min();
        setDelta(dt);
      } else {
        setDelta(EMPTY_DELTA);
      }
    } catch (e) {
      console.error('st11 fetch error', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(date, periodMode, rangeStart, rangeEnd); }, [date, periodMode, fetchAll]);

  // 30분마다 자동 갱신(오늘·일간 모드일 때만). 수동 새로고침 시 타이머를 리셋해
  // "마지막 새로고침으로부터 30분 후"에 다시 돌도록 한다.
  const scheduleTimer = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (periodMode === 'daily' && date === todayStr()) {
      timerRef.current = setInterval(() => {
        fetchAll(date, periodMode, rangeStart, rangeEnd);
      }, REFRESH_INTERVAL);
    }
  }, [date, periodMode, rangeStart, rangeEnd, fetchAll]);

  useEffect(() => {
    scheduleTimer();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [scheduleTimer]);

  const prevDate = () => {
    const d = new Date(date);
    if (periodMode === 'yearly') d.setFullYear(d.getFullYear() - 1);
    else if (periodMode === 'monthly') d.setMonth(d.getMonth() - 1);
    else d.setDate(d.getDate() - 1);
    setDate(ymd(d));
  };

  const nextDate = () => {
    const d = new Date(date);
    if (periodMode === 'yearly') d.setFullYear(d.getFullYear() + 1);
    else if (periodMode === 'monthly') d.setMonth(d.getMonth() + 1);
    else d.setDate(d.getDate() + 1);
    const next = ymd(d);
    if (next <= todayStr()) setDate(next);
  };

  const goToday = () => setDate(todayStr());

  const searchRange = useCallback(() => {
    fetchAll(date, 'range', rangeStart, rangeEnd);
  }, [date, rangeStart, rangeEnd, fetchAll]);

  const refresh = useCallback(() => {
    fetchAll(date, periodMode, rangeStart, rangeEnd);
    scheduleTimer();
  }, [date, periodMode, rangeStart, rangeEnd, fetchAll, scheduleTimer]);

  // Overview/G마켓/스마트스토어와 동일한 6종 프리셋 버튼(PeriodSelector) 클릭 처리
  const pickPeriod = useCallback((preset: PeriodPreset) => {
    const today = todayStr();
    if (preset === 'today') { setPeriodMode('daily'); setDate(today); }
    else if (preset === 'yesterday') { setPeriodMode('daily'); setDate(yesterdayStr()); }
    else if (preset === 'monthly') { setPeriodMode('monthly'); setDate(today); }
    else if (preset === 'yearly') { setPeriodMode('yearly'); setDate(today); }
    else if (preset === 'recent30') { setPeriodMode('recent30'); }
    else { setPeriodMode('range'); }
  }, []);

  return {
    date, setDate, summary, delta,
    selectedSeller, setSelectedSeller,
    loading, prevDate, nextDate, goToday,
    periodMode, setPeriodMode, pickPeriod,
    rangeStart, setRangeStart, rangeEnd, setRangeEnd, searchRange,
    refresh,
  };
}
