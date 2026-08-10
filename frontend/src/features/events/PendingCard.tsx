import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { SourceMessage, ActivityEvent } from "@/api/types";
import { EventEditor } from "@/features/events/EventEditor";
import { useState } from "react";

interface PendingSourceProps {
  message: SourceMessage;
}

export function PendingSource({ message }: PendingSourceProps) {
  const queryClient = useQueryClient();

  const retryMutation = useMutation({
    mutationFn: (id: string) => api.retryMessage(id),
    onSuccess: () => {
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

  return (
    <div className="pending-card">
      <p className="pending-card-source">{message.original_text}</p>
      {message.error_summary && (
        <p className="pending-card-error">{message.error_summary}</p>
      )}
      <div className="pending-card-actions">
        <button
          className="pending-card-retry"
          onClick={() => retryMutation.mutate(message.id)}
          disabled={retryMutation.isPending}
        >
          重新分类
        </button>
        <button
          className="pending-card-delete"
          onClick={() => {
            if (window.confirm("确定要删除这条源消息吗？")) {
              deleteMutation.mutate(message.id);
            }
          }}
          disabled={deleteMutation.isPending}
        >
          删除
        </button>
      </div>
    </div>
  );
}

interface PendingEventProps {
  event: ActivityEvent;
}

export function PendingEvent({ event }: PendingEventProps) {
  const [editing, setEditing] = useState(false);

  return (
    <div className="pending-card pending-card-event">
      <div className="pending-card-event-header">
        <span className="pending-card-event-title">{event.title}</span>
        <span className="pending-card-event-fragment">{event.source_fragment}</span>
      </div>
      <div className="pending-card-actions">
        <button
          className="pending-card-edit"
          onClick={() => setEditing(true)}
        >
          手动编辑
        </button>
        <button
          className="pending-card-reclassify"
          onClick={() => setEditing(true)}
        >
          重新分类
        </button>
      </div>
      {editing && (
        <EventEditor
          event={event}
          onClose={() => setEditing(false)}
          showReclassify
        />
      )}
    </div>
  );
}

interface PendingCardProps {
  message: SourceMessage;
  events: ActivityEvent[];
}

export function PendingCard({ message, events }: PendingCardProps) {
  return (
    <div className="pending-card-list">
      <PendingSource message={message} />
      {events.map((event) => (
        <PendingEvent key={event.id} event={event} />
      ))}
    </div>
  );
}
