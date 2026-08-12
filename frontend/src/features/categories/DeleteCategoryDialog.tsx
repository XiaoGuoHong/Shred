import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { CategoryNode, DeleteImpact } from "@/api/types";

interface DeleteCategoryDialogProps {
  category: CategoryNode;
  onClose: () => void;
  onDeleted: () => void;
}

export function DeleteCategoryDialog({
  category,
  onClose,
  onDeleted,
}: DeleteCategoryDialogProps) {
  const queryClient = useQueryClient();
  const [impact, setImpact] = useState<DeleteImpact | null>(null);
  const [loadingImpact, setLoadingImpact] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoadingImpact(true);
    setError(null);
    api
      .getDeleteImpact(category.id)
      .then((data) => {
        setImpact(data);
        setLoadingImpact(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoadingImpact(false);
      });
  }, [category.id]);

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteCategory(category.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      onDeleted();
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const canConfirm = impact !== null && !loadingImpact;

  return (
    <div
      className="dialog-overlay"
      role="dialog"
      aria-label="删除分类"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="dialog-panel" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h3 className="dialog-title">删除分类</h3>
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
            确定要删除分类 <strong>{category.name}</strong> 吗？
          </p>
          {loadingImpact && (
            <p className="dialog-loading">正在检查影响...</p>
          )}
          {impact && (
            <div className="delete-impact">
              <p>
                该分类下有 <strong>{impact.descendant_count}</strong> 个子分类
              </p>
              <p>
                关联了 <strong>{impact.affected_event_count}</strong> 个活动记录
              </p>
            </div>
          )}
          {error && <p className="dialog-error">{error}</p>}
        </div>
        <div className="dialog-footer">
          <button className="dialog-btn" onClick={onClose}>
            取消
          </button>
          <button
            className="dialog-btn dialog-btn-danger"
            onClick={() => deleteMutation.mutate()}
            disabled={!canConfirm || deleteMutation.isPending}
          >
            {deleteMutation.isPending ? "删除中..." : "确认删除"}
          </button>
        </div>
      </div>
    </div>
  );
}
