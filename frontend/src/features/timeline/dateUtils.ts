const WEEKDAY_LABELS = ["日", "一", "二", "三", "四", "五", "六"];

export function toLocalDateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function startOfDay(d: Date): Date {
  const copy = new Date(d);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

export function addDays(d: Date, days: number): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + days);
  return copy;
}

/** Monday-first days of the week containing the anchor date. */
export function weekDays(anchor: Date): Date[] {
  const monday = addDays(startOfDay(anchor), -((anchor.getDay() + 6) % 7));
  return Array.from({ length: 7 }, (_, i) => addDays(monday, i));
}

export function isSameDay(a: Date, b: Date): boolean {
  return toLocalDateKey(a) === toLocalDateKey(b);
}

export function formatDayLabel(date: Date, today: Date): string {
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const weekday = WEEKDAY_LABELS[date.getDay()];

  if (isSameDay(date, today)) {
    return `今天 · ${month}月${day}日`;
  }
  if (isSameDay(date, addDays(today, -1))) {
    return `昨天 · ${month}月${day}日`;
  }
  const year = date.getFullYear();
  const todayYear = today.getFullYear();
  if (year !== todayYear) {
    return `${year}年${month}月${day}日 · 星期${weekday}`;
  }
  return `${month}月${day}日 · 星期${weekday}`;
}

export function formatWeekdayShort(date: Date): string {
  return WEEKDAY_LABELS[date.getDay()] ?? "";
}
