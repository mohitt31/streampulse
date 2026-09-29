// All dates are ISO calendar days (YYYY-MM-DD) handled in UTC to avoid DST drift.
const DAY = 86_400_000;

export const toMs = (iso: string) => Date.parse(iso + "T00:00:00Z");
export const fromMs = (ms: number) => new Date(ms).toISOString().slice(0, 10);
export const addDays = (iso: string, n: number) => fromMs(toMs(iso) + n * DAY);
export const daysBetween = (a: string, b: string) => Math.round((toMs(b) - toMs(a)) / DAY);

/** 365-day calendar index (1..365), identical to the Python pipeline: Feb 29 shares Feb 28's slot. */
export function doy365(iso: string): number {
  const d = new Date(toMs(iso));
  const y = d.getUTCFullYear();
  const start = Date.UTC(y, 0, 1);
  let doy = Math.round((d.getTime() - start) / DAY) + 1;
  const leap = (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
  const m = d.getUTCMonth() + 1;
  if (leap && m === 2 && d.getUTCDate() === 29) return 59;
  if (leap && m > 2) doy -= 1;
  return doy;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function fmtDay(iso: string, withYear = false): string {
  const d = new Date(toMs(iso));
  const s = `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
  return withYear ? `${s} ${d.getUTCFullYear()}` : s;
}

export function fmtDayLong(iso: string): string {
  const d = new Date(toMs(iso));
  return `${WEEKDAYS[d.getUTCDay()]} ${fmtDay(iso, true)}`;
}

export const todayUtc = () => new Date().toISOString().slice(0, 10);
