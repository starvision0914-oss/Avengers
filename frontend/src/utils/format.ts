const KOREAN_DAYS = ['일', '월', '화', '수', '목', '금', '토'] as const;

export function formatKRW(n: number): string {
  return Math.round(n).toLocaleString('ko-KR');
}

export function formatTime(dt: string): string {
  if (!dt) return '-';
  const t = dt.split(' ')[1];
  if (!t) return '-';
  return t.slice(0, 5);
}

export function getKoreanDay(dateStr: string): string {
  const d = new Date(dateStr);
  return KOREAN_DAYS[d.getDay()];
}

// 로컬 기준 YYYY-MM-DD (toISOString은 UTC로 변환되어 KST에서 하루가 밀리므로 사용 금지)
export function ymd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function todayStr(): string {
  return ymd(new Date());
}

export function isOverdue90(dateStr: string | null): boolean {
  if (!dateStr) return true;
  const feeDate = new Date(dateStr.replace('T', ' ').split(' ')[0]);
  const now = new Date();
  const diff = (now.getTime() - feeDate.getTime()) / (1000 * 60 * 60 * 24);
  return diff > 90;
}

export function feeDateSuffix(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = dateStr.replace('T', ' ').split(' ')[0];
  const parts = d.split('-');
  if (parts.length < 3) return '';
  return `(${parts[1]}/${parts[2]})`;
}
