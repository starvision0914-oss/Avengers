import { useState, useEffect, useCallback, useRef } from 'react';
import { getSt11Summary, getSt11Last15Min } from '../api/eleven';
import { todayStr, ymd } from '../utils/format';
import type { St11SummaryResponse, St11Last15MinResponse } from '../types/st11';
import type { PeriodMode } from '../types/cpc';

const REFRESH_INTERVAL = 5 * 60 * 1000;
const EMPTY_DELTA: St11Last15MinResponse = { cpc_delta: 0, ad_delta: 0, sales_delta: 0 };

function monthStart(d: string) { return d.slice(0, 8) + '01'; }
function monthEnd(d: string) {
  const dt = new Date(d);
  return ymd(new Date(dt.getFullYear(), dt.getMonth() + 1, 0));
}
function yearStart(d: string) { return d.slice(0, 4) + '-01-01'; }
function yearEnd(d: string) { return d.slice(0, 4) + '-12-31'; }

export function useSt11Data() {
  const [date, setDate] = useState(todayStr);
  const [periodMode, setPeriodMode] = useState<PeriodMode>('daily');
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
      if (mode === 'yearly') range = { start_date: yearStart(d), end_date: yearEnd(d) };
      else if (mode === 'monthly') range = { start_date: monthStart(d), end_date: monthEnd(d) };
      else if (mode === 'range') range = { start_date: rStart, end_date: rEnd };

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

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (periodMode === 'daily' && date === todayStr()) {
      timerRef.current = setInterval(() => {
        fetchAll(date, periodMode, rangeStart, rangeEnd);
      }, REFRESH_INTERVAL);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [date, periodMode, rangeStart, rangeEnd, fetchAll]);

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
  }, [date, periodMode, rangeStart, rangeEnd, fetchAll]);

  return {
    date, setDate, summary, delta,
    selectedSeller, setSelectedSeller,
    loading, prevDate, nextDate, goToday,
    periodMode, setPeriodMode,
    rangeStart, setRangeStart, rangeEnd, setRangeEnd, searchRange,
    refresh,
  };
}
