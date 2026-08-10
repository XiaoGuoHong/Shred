import { useState, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { CategoryNode } from "@/api/types";

interface MergeDialogProps {
  source: CategoryNode;
  categories: CategoryNode[];
  onClose: () => void;
  onMerged: () => void;
}

function getSameDepthTargets(
  source: CategoryNode,
  allRoots: CategoryNode[],
): CategoryNode[] {
  if (!source.parent_id) {
    return allRoots.filter((c) => c.id !== source.id);
  }
  const parent = allRoots.find((r) => r.id === source.parent_id);
  if (!parent) return [];
  return parent.children.filter((c) => c.id !== source.id);
}

export function MergeDialog({
  source,
  categories,
  onClose,
  onMerged,
}: MergeDialogProps) {
  const queryClient = useQueryClient();
  const [targetId, setTargetId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const targets = getSameDepthTargets(source, categories);

  const mergeMutation = useMutation({
    mutationFn: () =>
      api.mergeCategories({ source_id: source.id, target_id: targetId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      onMerged();
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const handleMerge = useCallback(() => {
    if (!targetId) return;
    setError(null);
    mergeMutation.mutate();
  }, [targetId, mergeMutation]);

  return (
    <div
      className="dialog-overlay"
      role="dialog"
      aria-label="合并分类"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="dialog-panel" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h3 className="dialog-title">合并分类</h3>
          <button
            className="dialog-close"
            onClick={onClose}
            aria-label="关闭"
          >
            ✕
          </button>
        </div>
        <div className="dialog-body">
          <p className="dialog-info">
            将 <strong>{source.name}</strong> 合并到目标分类
          </p>
          {targets.length === 0 ? (
            <p className="dialog-info">没有可合并的目标分类</p>
          ) : (
            <select
              className="dialog-select"
              value={targetId}
              onChange={(e) => {
                setTargetId(e.target.value);
                setError(null);
              }}
            >
              <option value="">选择目标分类</option>
              {targets.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          )}
          {error && <p className="dialog-error">{error}</p>}
        </div>
        <div className="dialog-footer">
          <button className="dialog-btn" onClick={onClose}>
            取消
          </button>
          <button
            className="dialog-btn dialog-btn-primary"
            onClick={handleMerge}
            disabled={!targetId || mergeMutation.isPending}
          >
            {mergeMutation.isPending ? "合并中..." : "合并"}
          </button>
        </div>
      </div>
    </div>
  );
}
