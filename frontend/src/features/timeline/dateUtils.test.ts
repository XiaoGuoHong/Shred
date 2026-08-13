import { describe, it, expect } from "vitest";
import {
  addDays,
  formatDayLabel,
  formatWeekdayShort,
  isSameDay,
  startOfDay,
  toLocalDateKey,
  weekDays,
} from "@/features/timeline/dateUtils";

describe("dateUtils", () => {
  it("formats local date keys", () => {
    expect(toLocalDateKey(new Date(2026, 7, 12))).toBe("2026-08-12");
    expect(toLocalDateKey(new Date(2026, 0, 3))).toBe("2026-01-03");
  });

  it("startOfDay zeroes the time", () => {
    const d = startOfDay(new Date(2026, 7, 12, 14, 30, 45));
    expect(d.getHours()).toBe(0);
    expect(d.getMinutes()).toBe(0);
    expect(d.getDate()).toBe(12);
  });

  it("addDays shifts by calendar days", () => {
    const d = addDays(new Date(2026, 7, 31), 1);
    expect(d.getMonth()).toBe(8);
    expect(d.getDate()).toBe(1);
  });

  it("isSameDay compares calendar dates", () => {
    expect(isSameDay(new Date(2026, 7, 12, 23, 59), new Date(2026, 7, 12, 0, 0))).toBe(true);
    expect(isSameDay(new Date(2026, 7, 12), new Date(2026, 7, 13))).toBe(false);
  });

  it("weekDays returns Monday-first week", () => {
    // 2026-08-12 is a Wednesday.
    const days = weekDays(new Date(2026, 7, 12));
    expect(days).toHaveLength(7);
    const monday = days[0];
    const sunday = days[6];
    expect(monday).toBeDefined();
    expect(sunday).toBeDefined();
    expect(formatWeekdayShort(monday!)).toBe("一");
    expect(monday!.getDate()).toBe(10);
    expect(sunday!.getDate()).toBe(16);
  });

  it("formats today and yesterday labels", () => {
    const today = new Date(2026, 7, 12);
    expect(formatDayLabel(new Date(2026, 7, 12), today)).toBe("今天 · 8月12日");
    expect(formatDayLabel(new Date(2026, 7, 11), today)).toBe("昨天 · 8月11日");
  });

  it("formats older dates with weekday", () => {
    const today = new Date(2026, 7, 12);
    expect(formatDayLabel(new Date(2026, 7, 10), today)).toBe("8月10日 · 星期一");
    expect(formatDayLabel(new Date(2025, 11, 31), today)).toBe(
      "2025年12月31日 · 星期三",
    );
  });
});
