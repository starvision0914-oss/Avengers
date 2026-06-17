import { useState, useEffect, useCallback, useRef } from 'react';
import { getDailySummary, getTimeseries, getLast15Min, sendTelegram, getTgMode, setTgMode as apiSetTgMode } from '../api/gmarket';
import { todayStr, ymd } from '../utils/format';
import type { DailySummaryResponse, TimeseriesRow, SalesTimeseriesRow, Last15MinResponse, TelegramMode, PeriodMode } from '../types/cpc';

const REFRESH_INTERVAL = 5 * 60 * 1000;
const EMPTY_DELTA: Last15MinResponse = { cpc_delta: 0, ai_delta: 0, prime_delta: 0, ad_delta: 0, sales_delta: 0 };

function monthStart(d: string) { return d.slice(0, 8) + '01'; }
function monthEnd(d: string) {
  const dt = new Date(d);
  return ymd(new Date(dt.getFullYear(), dt.getMonth() + 1, 0));
}
function yearStart(d: string) { return d.slice(0, 4) + '-01-01'; }
function yearEnd(d: string) { return d.slice(0, 4) + '-12-31'; }

export function useCpcData() {
  const [date, setDate] = useState(todayStr);
  const [periodMode, setPeriodMode] = useState<PeriodMode>('daily');
  const [rangeStart, setRangeStart] = useState(todayStr);
  const [rangeEnd, setRangeEnd] = useState(todayStr);
  const [summary, setSummary] = useState<DailySummaryResponse | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesRow[]>([]);
  const [salesTimeseries, setSalesTimeseries] = useState<SalesTimeseriesRow[]>([]);
  const [delta, setDelta] = useState<Last15MinResponse>(EMPTY_DELTA);
  const [selectedSeller, setSelectedSeller] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [tgMode, setTgModeState] = useState<TelegramMode>('off');
  const [tgStatus, setTgStatus] = useState<string>('');
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getTgMode().then(m => setTgModeState(m as TelegramMode)).catch(() => {});
  }, []);

  const setTgMode = useCallback(async (mode: TelegramMode) => {
    setTgModeState(mode);
    try { await apiSetTgMode(mode); } catch { /* ignore */ }
  }, []);

  const manualSend = useCallback(async () => {
    try {
      setTgStatus('전송중…');
      const res = await sendTelegram(date, true);
      setTgStatus(res.sent ? (res.changed ? '전송완료' : '변동없음 전송') : '전송실패');
      setTimeout(() => setTgStatus(''), 5000);
    } catch {
      setTgStatus('전송에러');
      setTimeout(() => setTgStatus(''), 5000);
    }
  }, [date]);

  const fetchAll = useCallback(async (d: string, mode: PeriodMode, rStart: string, rEnd: string) => {
    setLoading(true);
    try {
      let range: { start_date: string; end_date: string } | undefined;
      if (mode === 'yearly') range = { start_date: yearStart(d), end_date: yearEnd(d) };
      else if (mode === 'monthly') range = { start_date: monthStart(d), end_date: monthEnd(d) };
      else if (mode === 'range') range = { start_date: rStart, end_date: rEnd };

      const data = await getDailySummary(d, range);
      setSummary(data);

      if (mode === 'daily' && d === todayStr()) {
        const dt = await getLast15Min();
        setDelta(dt);
      } else {
        setDelta(EMPTY_DELTA);
      }
    } catch (e) {
      console.error('fetch error', e);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTimeseries = useCallback(async (d: string, sellerId: string) => {
    try {
      const resp = await getTimeseries(d, [sellerId]);
      setTimeseries(resp.data);
      setSalesTimeseries(resp.sales || []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchAll(date, periodMode, rangeStart, rangeEnd); }, [date, periodMode, fetchAll]);

  useEffect(() => {
    if (selectedSeller && periodMode === 'daily') fetchTimeseries(date, selectedSeller);
    else { setTimeseries([]); setSalesTimeseries([]); }
  }, [date, selectedSeller, periodMode, fetchTimeseries]);

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (periodMode === 'daily' && date === todayStr()) {
      timerRef.current = setInterval(() => {
        fetchAll(date, periodMode, rangeStart, rangeEnd);
        if (selectedSeller) fetchTimeseries(date, selectedSeller);
      }, REFRESH_INTERVAL);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [date, periodMode, selectedSeller, rangeStart, rangeEnd, fetchAll, fetchTimeseries]);

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

  return {
    date, setDate, summary, timeseries, salesTimeseries, delta,
    selectedSeller, setSelectedSeller,
    loading, prevDate, nextDate, goToday,
    tgMode, setTgMode, tgStatus, manualSend,
    periodMode, setPeriodMode,
    rangeStart, setRangeStart, rangeEnd, setRangeEnd, searchRange,
  };
}
