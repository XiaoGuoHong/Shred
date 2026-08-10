import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { TimelineGroup } from "@/api/types";
import { EventCard } from "@/features/timeline/EventCard";
import { PendingSource } from "@/features/events/PendingCard";

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

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteMessage(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
    },
  });

  const classifiedEvents = events.filter((e) => e.status !== "pending" && e.status !== "error");
  const pendingEvents = events.filter((e) => e.status === "pending" || e.status === "error");

  if (isError || isPending) {
    return (
      <div className="message-group message-group-pending">
        <PendingSource message={message} />
        {pendingEvents.length > 0 && (
          <div className="message-group-events">
            {pendingEvents.map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="message-group">
      <div className="message-group-header">
        <p className="message-group-text">{message.original_text}</p>
        <div className="message-group-actions">
          {canUndo && (
            <button
              className="message-group-undo"
              onClick={() => undoMutation.mutate(message.id)}
              disabled={undoMutation.isPending}
            >
              撤销本次提交
            </button>
          )}
          <button
            className="message-group-delete-source"
            onClick={() => {
              const count = events.length;
              const msg = count > 0
                ? `此操作将同时删除 ${count} 条关联的活动记录，确定要继续吗？`
                : "确定要删除这条源消息吗？";
              if (window.confirm(msg)) {
                deleteMutation.mutate(message.id);
              }
            }}
            disabled={deleteMutation.isPending}
          >
            删除
          </button>
        </div>
      </div>
      <div className="message-group-events">
        {classifiedEvents.map((event) => (
          <EventCard key={event.id} event={event} />
        ))}
      </div>
    </div>
  );
}
