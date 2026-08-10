import { useState, useEffect, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ActivityEvent, CategoryNode } from "@/api/types";

interface EventEditorProps {
  event: ActivityEvent;
  onClose: () => void;
  onReclassify?: (eventId: string) => void;
  showReclassify?: boolean;
}

function flattenCategories(nodes: CategoryNode[], depth = 0): { id: string; name: string; depth: number }[] {
  const result: { id: string; name: string; depth: number }[] = [];
  for (const node of nodes) {
    result.push({ id: node.id, name: node.name, depth });
    result.push(...flattenCategories(node.children, depth + 1));
  }
  return result;
}

const PRECISION_OPTIONS = [
  { value: "exact", label: "精确时间" },
  { value: "time", label: "时段" },
  { value: "date", label: "日期" },
  { value: "none", label: "无" },
];

const PART_OPTIONS = [
  { value: "", label: "默认" },
  { value: "early_morning", label: "凌晨" },
  { value: "morning", label: "上午" },
  { value: "noon", label: "中午" },
  { value: "afternoon", label: "下午" },
  { value: "evening", label: "晚上" },
  { value: "night", label: "夜间" },
];

function toLocalDatetimeString(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function EventEditor({ event, onClose, onReclassify, showReclassify }: EventEditorProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.getCategories(),
  });

  const [title, setTitle] = useState(event.title);
  const [occurredAt, setOccurredAt] = useState(toLocalDatetimeString(event.occurred_at));
  const [precision, setPrecision] = useState(event.occurrence_precision);
  const [partOfDay, setPartOfDay] = useState(event.part_of_day ?? "");
  const [categoryId, setCategoryId] = useState(event.category_id ?? "");
  const [tags, setTags] = useState<string[]>(event.tags);
  const [tagInput, setTagInput] = useState("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  function buildPatch() {
    const patch: Record<string, unknown> = {};
    if (title !== event.title) patch.title = title;
    const newOccurredAt = new Date(occurredAt).toISOString();
    if (newOccurredAt !== event.occurred_at) patch.occurred_at = newOccurredAt;
    if (precision !== event.occurrence_precision) patch.occurrence_precision = precision;
    if ((partOfDay || null) !== (event.part_of_day || null)) patch.part_of_day = partOfDay || null;
    if ((categoryId || null) !== (event.category_id || null)) patch.category_id = categoryId || null;
    if (JSON.stringify(tags) !== JSON.stringify(event.tags)) patch.tags = tags;
    return Object.keys(patch).length > 0 ? patch : null;
  }

  const saveMutation = useMutation({
    mutationFn: (patch: Record<string, unknown>) => api.updateEvent(event.id, patch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      onClose();
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteEvent(event.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      onClose();
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const reclassifyMutation = useMutation({
    mutationFn: () => api.reclassifyEvent(event.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      onClose();
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const handleSave = useCallback(() => {
    setError(null);
    const patch = buildPatch();
    if (!patch) {
      onClose();
      return;
    }
    saveMutation.mutate(patch);
  }, [saveMutation, onClose]);

  const handleAddTag = useCallback(() => {
    const trimmed = tagInput.trim();
    if (trimmed && !tags.includes(trimmed)) {
      setTags((prev) => [...prev, trimmed]);
    }
    setTagInput("");
  }, [tagInput, tags]);

  const handleRemoveTag = useCallback((tag: string) => {
    setTags((prev) => prev.filter((t) => t !== tag));
  }, []);

  const flatCategories = categoriesQuery.data ? flattenCategories(categoriesQuery.data) : [];
  const isPending = saveMutation.isPending || deleteMutation.isPending || reclassifyMutation.isPending;

  return (
    <div className="event-editor-overlay" role="dialog" aria-label="编辑活动记录" onClick={(e) => {
      if (e.target === e.currentTarget) onClose();
    }}>
      <div className="event-editor-panel" onClick={(e) => e.stopPropagation()}>
        <div className="event-editor-header">
          <h2 className="event-editor-title">编辑活动记录</h2>
          <button className="event-editor-close" onClick={onClose} aria-label="关闭">✕</button>
        </div>

        <div className="event-editor-body">
          <div className="event-editor-source">
            <label className="event-editor-label">原文</label>
            <p className="event-editor-source-text">{event.source_fragment}</p>
          </div>

          <div className="event-editor-field">
            <label className="event-editor-label" htmlFor="evt-title">标题</label>
            <input
              id="evt-title"
              className="event-editor-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="event-editor-field">
            <label className="event-editor-label" htmlFor="evt-time">时间</label>
            <input
              id="evt-time"
              className="event-editor-input"
              type="datetime-local"
              value={occurredAt}
              onChange={(e) => setOccurredAt(e.target.value)}
            />
          </div>

          <div className="event-editor-field">
            <label className="event-editor-label" htmlFor="evt-precision">时间精度</label>
            <select
              id="evt-precision"
              className="event-editor-select"
              value={precision}
              onChange={(e) => setPrecision(e.target.value)}
            >
              {PRECISION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <div className="event-editor-field">
            <label className="event-editor-label" htmlFor="evt-part">时段</label>
            <select
              id="evt-part"
              className="event-editor-select"
              value={partOfDay}
              onChange={(e) => setPartOfDay(e.target.value)}
            >
              {PART_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <div className="event-editor-field">
            <label className="event-editor-label" htmlFor="evt-category">分类</label>
            <select
              id="evt-category"
              className="event-editor-select"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
            >
              <option value="">未分类</option>
              {flatCategories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {"\u00A0\u00A0".repeat(cat.depth)}{cat.name}
                </option>
              ))}
            </select>
          </div>

          <div className="event-editor-field">
            <label className="event-editor-label">标签</label>
            <div className="event-editor-tags">
              {tags.map((tag) => (
                <span key={tag} className="event-editor-tag">
                  {tag}
                  <button
                    className="event-editor-tag-remove"
                    onClick={() => handleRemoveTag(tag)}
                    aria-label={`移除标签 ${tag}`}
                  >✕</button>
                </span>
              ))}
            </div>
            <div className="event-editor-tag-input-row">
              <input
                className="event-editor-input event-editor-tag-input"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddTag();
                  }
                }}
                placeholder="添加标签..."
              />
              <button
                className="event-editor-tag-add"
                onClick={handleAddTag}
                disabled={!tagInput.trim()}
              >添加</button>
            </div>
          </div>

          {error && <p className="event-editor-error">{error}</p>}
        </div>

        <div className="event-editor-footer">
          {showReclassify && onReclassify && (
            <button
              className="event-editor-reclassify"
              onClick={() => reclassifyMutation.mutate()}
              disabled={isPending}
            >重新分类</button>
          )}
          <div className="event-editor-footer-right">
            <button
              className="event-editor-delete"
              onClick={() => {
                if (window.confirm("确定要删除此活动记录吗？")) {
                  deleteMutation.mutate();
                }
              }}
              disabled={isPending}
            >删除</button>
            <button
              className="event-editor-save"
              onClick={handleSave}
              disabled={isPending}
            >保存</button>
          </div>
        </div>
      </div>
    </div>
  );
}
