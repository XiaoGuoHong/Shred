import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { TimelineGroup } from "@/api/types";
import { EventCard } from "@/features/timeline/EventCard";

export function MessageGroup({
  group,
  canUndo,
  onUndo,
}: {
  group: TimelineGroup;
  canUndo: boolean;
  onUndo: (messageId: string) => void;
}) {
  const queryClient = useQueryClient();
  const { message, events } = group;
  const isPending = message.status === "pending";
  const isError = message.status === "error";

  const undoMutation = useMutation({
    mutationFn: (id: string) => api.undoMessage(id),
    onSuccess: () => {
      onUndo(message.id);
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) =>
      fetch(`/api/messages/${id}/retry`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
  });

  return (
    <div className={`message-group${isPending ? " message-group-pending" : ""}`}>
      <div className="message-group-header">
        <p className="message-group-text">{message.original_text}</p>
        {isError && message.error_summary && (
          <p className="message-group-error">{message.error_summary}</p>
        )}
        <div className="message-group-actions">
          {isPending && (
            <button
              className="message-group-retry"
              onClick={() => retryMutation.mutate(message.id)}
              disabled={retryMutation.isPending}
            >
              重新分类
            </button>
          )}
          {canUndo && !isPending && (
            <button
              className="message-group-undo"
              onClick={() => undoMutation.mutate(message.id)}
              disabled={undoMutation.isPending}
            >
              撤销本次提交
            </button>
          )}
        </div>
      </div>
      <div className="message-group-events">
        {events.map((event) => (
          <EventCard key={event.id} event={event} />
        ))}
      </div>
    </div>
  );
}
