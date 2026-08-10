import { useState } from "react";
import type { ActivityEvent } from "@/api/types";
import { EventEditor } from "@/features/events/EventEditor";

const PART_LABELS: Record<string, string> = {
  early_morning: "凌晨",
  morning: "上午",
  noon: "中午",
  afternoon: "下午",
  evening: "晚上",
  night: "夜间",
};

function formatTime(event: ActivityEvent): string {
  if (event.occurrence_precision === "exact" && event.occurred_at) {
    const d = new Date(event.occurred_at);
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    return `${hh}:${mm}`;
  }
  if (event.part_of_day) {
    return PART_LABELS[event.part_of_day] ?? event.part_of_day;
  }
  if (event.occurrence_precision === "date" && event.occurred_at) {
    const d = new Date(event.occurred_at);
    return `${d.getMonth() + 1}月${d.getDate()}日`;
  }
  return "";
}

export function EventCard({ event }: { event: ActivityEvent }) {
  const [editing, setEditing] = useState(false);
  const timeDisplay = formatTime(event);

  return (
    <>
      <div className="event-card">
        <div className="event-card-header">
          <span className="event-card-title">{event.title}</span>
          {timeDisplay && (
            <span className="event-card-time">{timeDisplay}</span>
          )}
        </div>
        {event.category_path && (
          <span className="event-card-category">{event.category_path}</span>
        )}
        {event.tags.length > 0 && (
          <div className="event-card-tags">
            {event.tags.map((tag) => (
              <span key={tag} className="event-card-tag">
                {tag}
              </span>
            ))}
          </div>
        )}
        <div className="event-card-actions">
          <button
            className="event-card-action"
            onClick={() => setEditing(true)}
          >
            编辑
          </button>
          <button className="event-card-action event-card-action-delete">
            删除
          </button>
        </div>
      </div>
      {editing && (
        <EventEditor
          event={event}
          onClose={() => setEditing(false)}
        />
      )}
    </>
  );
}
