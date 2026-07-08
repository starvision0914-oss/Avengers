import { ymd } from './format';

// 4개 대시보드(Overview/Gmarket/SmartStore/St11) 공통 기간 프리셋.
// 모든 페이지가 이 함수들로만 날짜를 계산해야 "같은 프리셋 = 같은 기간"이 보장된다.
export type PeriodMode = 'daily' | 'monthly' | 'yearly' | 'recent30' | 'range';
export type PeriodPreset = 'today' | 'yesterday' | 'monthly' | 'yearly' | 'recent30' | 'range';

export interface DateRange { from: string; to: string; }

// KST 타임존 기준 오늘 날짜 (모든 대시보드가 일관되어야 함)
function todayKST(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' });
}

// KST 기준 어제
export function yesterdayStr(): string {
  const d = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  d.setDate(d.getDate() - 1);
  return d.toLocaleDateString('en-CA');
}

// date가 속한 달의 1일 ~ min(그 달 말일, 오늘) — 당월(진행중)이면 오늘까지만, 지난달이면 말일까지 전부
export function monthRangeOf(date: string): DateRange {
  const [y, m] = date.split('-').map(Number);
  const from = ymd(new Date(y, m - 1, 1));
  const end = ymd(new Date(y, m, 0));
  const today = todayKST();
  return { from, to: end > today ? today : end };
}

// date가 속한 해의 1/1 ~ min(12/31, 오늘)
export function yearRangeOf(date: string): DateRange {
  const y = Number(date.slice(0, 4));
  const end = `${y}-12-31`;
  const today = todayKST();
  return { from: `${y}-01-01`, to: end > today ? today : end };
}

// 최근 30일(오늘 포함, rolling) — KST 기준
export function recent30Range(): DateRange {
  const d = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  d.setDate(d.getDate() - 29);
  return { from: d.toLocaleDateString('en-CA'), to: todayKST() };
}

// periodMode + 기준일(date, daily 모드에서만 의미) + 커스텀 범위 → 실제 조회 시작/종료일
export function resolveRange(mode: PeriodMode, date: string, rangeStart: string, rangeEnd: string): DateRange {
  if (mode === 'yearly') return yearRangeOf(date);
  if (mode === 'monthly') return monthRangeOf(date);
  if (mode === 'recent30') return recent30Range();
  if (mode === 'range') return { from: rangeStart, to: rangeEnd };
  return { from: date, to: date }; // daily
}
