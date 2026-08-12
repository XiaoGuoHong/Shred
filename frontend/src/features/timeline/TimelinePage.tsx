import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ViewSelection, TimelineParams, TimelineGroup } from "@/api/types";
import { Composer } from "@/features/timeline/Composer";
import { MessageGroup } from "@/features/timeline/MessageGroup";
import { DateStrip } from "@/features/timeline/DateStrip";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import {
  formatDayLabel,
  startOfDay,
  toLocalDateKey,
} from "@/features/timeline/dateUtils";

const PAGE_SIZE = 50;

function viewToParams(view: ViewSelection): TimelineParams {
  if (view.kind === "pending") {
    return { page_size: PAGE_SIZE, status: "pending" };
  }
  if (view.kind === "category") {
    return { page_size: PAGE_SIZE, category_id: view.categoryId };
  }
  return { page_size: PAGE_SIZE };
}

/** Local date of the group: latest event time, or the source submission time. */
function groupTimeMs(group: TimelineGroup): number {
  if (group.events.length > 0) {
    return Math.max(...group.events.map((e) => new Date(e.occurred_at).getTime()));
  }
  return new Date(group.message.submitted_at).getTime();
}

function groupDayKey(group: TimelineGroup): string {
  return toLocalDateKey(new Date(groupTimeMs(group)));
}

interface DayGroup {
  key: string;
  date: Date;
  groups: TimelineGroup[];
}

export function TimelinePage({ view }: { view: ViewSelection }) {
  const [page, setPage] = useState(1);
  const [selectedDate, setSelectedDate] = useState(() => startOfDay(new Date()));
  const [recentlyClassified, setRecentlyClassified] = useState<Set<string>>(
    () => new Set(),
  );
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );
  const scrolledRef = useRef(false);
  const { isBackendReachable } = useOnlineStatus();

  const params = { ...viewToParams(view), page };

  const timelineQuery = useQuery({
    queryKey: ["timeline", params],
    queryFn: () => api.getTimeline(params),
  });

  useQuery({
    queryKey: ["categories"],
    queryFn: () => api.getCategories(),
  });

  const handleSubmitted = useCallback((messageId: string) => {
    setRecentlyClassified((prev) => {
      const next = new Set(prev);
      next.add(messageId);
      return next;
    });
    const timer = setTimeout(() => {
      setRecentlyClassified((prev) => {
        const next = new Set(prev);
        next.delete(messageId);
        return next;
      });
      timersRef.current.delete(messageId);
    }, 10_000);
    timersRef.current.set(messageId, timer);
  }, []);

  const handleUndo = useCallback(
    (messageId: string) => {
      const timer = timersRef.current.get(messageId);
      if (timer) {
        clearTimeout(timer);
        timersRef.current.delete(messageId);
      }
      setRecentlyClassified((prev) => {
        const next = new Set(prev);
        next.delete(messageId);
        return next;
      });
    },
    [],
  );

  const groups = timelineQuery.data?.groups ?? [];
  const total = timelineQuery.data?.total ?? 0;
  const hasMore = page * PAGE_SIZE < total;

  const dayGroups = useMemo(() => {
    const map = new Map<string, DayGroup>();
    for (const group of groups) {
      const key = groupDayKey(group);
      const existing = map.get(key);
      if (existing) {
        existing.groups.push(group);
      } else {
        map.set(key, {
          key,
          date: startOfDay(new Date(groupTimeMs(group))),
          groups: [group],
        });
      }
    }
    const result = [...map.values()];
    for (const day of result) {
      day.groups.sort((a, b) => groupTimeMs(b) - groupTimeMs(a));
    }
    result.sort((a, b) => b.date.getTime() - a.date.getTime());
    return result;
  }, [groups]);

  const markedKeys = useMemo(
    () => new Set(dayGroups.map((d) => d.key)),
    [dayGroups],
  );

  useEffect(() => {
    if (scrolledRef.current) {
      document
        .getElementById(`day-${toLocalDateKey(selectedDate)}`)
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [selectedDate]);

  useEffect(() => {
    scrolledRef.current = true;
  }, []);

  const showComposer = view.kind === "all" || view.kind === "pending";
  const showDateStrip = view.kind === "all";
  const today = startOfDay(new Date());

  return (
    <div className="timeline">
      {!isBackendReachable && (
        <div className="timeline-offline-banner">本地服务不可用</div>
      )}
      {showComposer && <Composer onSubmitted={handleSubmitted} />}
      {showDateStrip && (
        <DateStrip
          selected={selectedDate}
          markedKeys={markedKeys}
          onSelect={setSelectedDate}
        />
      )}
      {timelineQuery.isLoading && (
        <div className="timeline-loading">加载中...</div>
      )}
      {timelineQuery.isError && (
        <div className="timeline-error">加载失败，请重试</div>
      )}
      {!timelineQuery.isLoading &&
        !timelineQuery.isError &&
        groups.length === 0 && (
          <div className="timeline-empty">暂无记录</div>
        )}
      {dayGroups.map((day) => (
        <section key={day.key} id={`day-${day.key}`} className="timeline-day">
          <header className="timeline-day-header">
            <span className="timeline-day-dot" aria-hidden="true" />
            <h3 className="timeline-day-title">
              {formatDayLabel(day.date, today)}
            </h3>
            <span className="timeline-day-count">
              {day.groups.reduce(
                (acc, g) => acc + (g.events.length > 0 ? g.events.length : 1),
                0,
              )}{" "}
              条记录
            </span>
          </header>
          <div className="timeline-day-body">
            {day.groups.map((group) => (
              <MessageGroup
                key={group.message.id}
                group={group}
                canUndo={recentlyClassified.has(group.message.id)}
                onUndo={handleUndo}
              />
            ))}
          </div>
        </section>
      ))}
      {hasMore && (
        <button
          className="timeline-load-more"
          onClick={() => setPage((p) => p + 1)}
        >
          加载更多
        </button>
      )}
    </div>
  );
}
