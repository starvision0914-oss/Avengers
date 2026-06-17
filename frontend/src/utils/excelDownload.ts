import type { PeriodMode } from '../types/cpc';
import { ymd } from './format';

export function downloadExcel(
  basePath: string,
  periodMode: PeriodMode,
  date: string,
  rangeStart: string,
  rangeEnd: string,
) {
  const params = new URLSearchParams();
  params.set('mode', periodMode);
  if (periodMode === 'range') {
    params.set('start_date', rangeStart);
    params.set('end_date', rangeEnd);
  } else if (periodMode === 'yearly') {
    params.set('start_date', `${date.slice(0, 4)}-01-01`);
    params.set('end_date', `${date.slice(0, 4)}-12-31`);
  } else if (periodMode === 'monthly') {
    const d = new Date(date);
    params.set('start_date', `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`);
    params.set('end_date', ymd(new Date(d.getFullYear(), d.getMonth() + 1, 0)));
  } else {
    params.set('date', date);
  }
  window.open(`${basePath}?${params.toString()}`, '_blank');
}
