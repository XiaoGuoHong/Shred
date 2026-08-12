import { useMemo, useState } from "react";
import { Icon } from "@/components/icons";
import {
  addDays,
  formatWeekdayShort,
  isSameDay,
  startOfDay,
  toLocalDateKey,
  weekDays,
} from "@/features/timeline/dateUtils";

export function DateStrip({
  selected,
  markedKeys,
  onSelect,
}: {
  selected: Date;
  markedKeys: Set<string>;
  onSelect: (date: Date) => void;
}) {
  const [weekAnchor, setWeekAnchor] = useState(() => startOfDay(selected));
  const days = useMemo(() => weekDays(weekAnchor), [weekAnchor]);

  const shiftWeek = (delta: number) => {
    const next = addDays(weekAnchor, delta * 7);
    setWeekAnchor(next);
    onSelect(next);
  };

  return (
    <div className="date-strip">
      <button
        className="date-strip-nav"
        onClick={() => shiftWeek(-1)}
        aria-label="上一周"
      >
        <Icon name="chevronLeft" size={16} />
      </button>
      <div className="date-strip-days">
        {days.map((day) => {
          const key = toLocalDateKey(day);
          const isSelected = isSameDay(day, selected);
          const isMarked = markedKeys.has(key);
          return (
            <button
              key={key}
              className={`date-strip-day${isSelected ? " selected" : ""}`}
              onClick={() => {
                setWeekAnchor(startOfDay(day));
                onSelect(day);
              }}
              aria-pressed={isSelected}
            >
              <span className="date-strip-weekday">
                {formatWeekdayShort(day)}
              </span>
              <span className="date-strip-number">{day.getDate()}</span>
              <span
                className={`date-strip-dot${isMarked ? " marked" : ""}`}
                aria-hidden="true"
              />
            </button>
          );
        })}
      </div>
      <button
        className="date-strip-nav"
        onClick={() => shiftWeek(1)}
        aria-label="下一周"
      >
        <Icon name="chevronRight" size={16} />
      </button>
    </div>
  );
}
