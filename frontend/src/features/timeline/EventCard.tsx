import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ActivityEvent } from "@/api/types";
import { EventEditor } from "@/features/events/EventEditor";
import { Icon, type IconName } from "@/components/icons";

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

/** Map the top-level category to a lightweight linear icon. */
function iconForCategory(path: string[] | undefined): IconName {
  const root = path?.[0] ?? "";
  if (root.includes("求职") || root.includes("面试")) return "briefcase";
  if (root.includes("学习") || root.includes("阅读") || root.includes("课程"))
    return "book";
  if (root.includes("工作") || root.includes("办公") || root.includes("项目"))
    return "doc";
  if (root.includes("健身") || root.includes("运动") || root.includes("锻炼"))
    return "dumbbell";
  if (root.includes("生活") || root.includes("家务") || root.includes("家庭"))
    return "home";
  return "sparkle";
}

export function EventCard({ event }: { event: ActivityEvent }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [focusCategory, setFocusCategory] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const timeDisplay = formatTime(event);
  const iconName = iconForCategory(event.category_path);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [menuOpen]);

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteEvent(event.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
  });

  const openEditor = (category: boolean) => {
    setFocusCategory(category);
    setEditing(true);
    setMenuOpen(false);
  };

  const handleDelete = () => {
    setMenuOpen(false);
    const ok = window.confirm(`确定要删除「${event.title}」这条记录吗？`);
    if (ok) {
      deleteMutation.mutate();
    }
  };

  return (
    <>
      <div className="event-card">
        <span className="event-card-icon" aria-hidden="true">
          <Icon name={iconName} size={17} />
        </span>
        <div className="event-card-body">
          <span className="event-card-title">{event.title}</span>
          <div className="event-card-meta">
            {event.category_path && event.category_path.length > 0 && (
              <span className="event-card-category">
                {event.category_path.join(" / ")}
              </span>
            )}
            {event.tags.map((tag) => (
              <span key={tag} className="event-card-tag">
                {tag}
              </span>
            ))}
          </div>
        </div>
        <div className="event-card-side">
          {timeDisplay && (
            <span className="event-card-time">{timeDisplay}</span>
          )}
          <div className="event-card-menu" ref={menuRef}>
            <button
              className="event-card-more"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="更多操作"
              aria-expanded={menuOpen}
            >
              <Icon name="more" size={18} />
            </button>
            {menuOpen && (
              <div className="event-card-menu-pop">
                <button
                  className="event-card-action"
                  onClick={() => openEditor(false)}
                >
                  <Icon name="edit" size={14} />
                  编辑
                </button>
                <button
                  className="event-card-action"
                  onClick={() => openEditor(true)}
                >
                  <Icon name="tag" size={14} />
                  修改分类
                </button>
                <button
                  className="event-card-action event-card-action-delete"
                  onClick={handleDelete}
                >
                  <Icon name="trash" size={14} />
                  删除
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
      {editing && (
        <EventEditor
          event={event}
          onClose={() => setEditing(false)}
          focusCategory={focusCategory}
        />
      )}
    </>
  );
}
