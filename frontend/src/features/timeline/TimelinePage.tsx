import { useState, useCallback, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ViewSelection, TimelineParams } from "@/api/types";
import { Composer } from "@/features/timeline/Composer";
import { MessageGroup } from "@/features/timeline/MessageGroup";

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

export function TimelinePage({ view }: { view: ViewSelection }) {
  const [page, setPage] = useState(1);
  const [recentlyClassified, setRecentlyClassified] = useState<Set<string>>(
    () => new Set(),
  );
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );

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

  const showComposer =
    view.kind === "all" || view.kind === "pending";

  return (
    <div className="timeline">
      {showComposer && <Composer onSubmitted={handleSubmitted} />}
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
      {groups.map((group) => (
        <MessageGroup
          key={group.message.id}
          group={group}
          canUndo={recentlyClassified.has(group.message.id)}
          onUndo={handleUndo}
        />
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
