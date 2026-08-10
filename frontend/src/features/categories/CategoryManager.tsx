import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { CategoryNode, ViewSelection } from "@/api/types";
import { MergeDialog } from "@/features/categories/MergeDialog";
import { DeleteCategoryDialog } from "@/features/categories/DeleteCategoryDialog";

interface CategoryManagerProps {
  onViewChange: (v: ViewSelection) => void;
}

export function CategoryManager({ onViewChange }: CategoryManagerProps) {
  const queryClient = useQueryClient();
  const [newName, setNewName] = useState("");
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [mergeSource, setMergeSource] = useState<CategoryNode | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CategoryNode | null>(null);
  const [expandedRoots, setExpandedRoots] = useState<Set<string>>(
    () => new Set(),
  );
  const [error, setError] = useState<string | null>(null);
  const [newChildName, setNewChildName] = useState<Record<string, string>>({});

  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.getCategories(),
  });

  const categories = categoriesQuery.data ?? [];

  const createMutation = useMutation({
    mutationFn: (data: { name: string; parent_id?: string }) =>
      api.createCategory(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      setNewName("");
      setNewChildName({});
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      api.renameCategory(id, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      setRenamingId(null);
      setRenameValue("");
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const handleCreateRoot = useCallback(() => {
    const trimmed = newName.trim();
    if (!trimmed) return;
    createMutation.mutate({ name: trimmed });
  }, [newName, createMutation]);

  const handleCreateChild = useCallback(
    (parentId: string) => {
      const trimmed = (newChildName[parentId] ?? "").trim();
      if (!trimmed) return;
      createMutation.mutate({ name: trimmed, parent_id: parentId });
    },
    [newChildName, createMutation],
  );

  const handleRenameStart = useCallback((node: CategoryNode) => {
    setRenamingId(node.id);
    setRenameValue(node.name);
    setError(null);
  }, []);

  const handleRenameSave = useCallback(
    (id: string) => {
      const trimmed = renameValue.trim();
      if (!trimmed) return;
      renameMutation.mutate({ id, name: trimmed });
    },
    [renameValue, renameMutation],
  );

  const handleMergeComplete = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["categories"] });
    setMergeSource(null);
    onViewChange({ kind: "all" });
  }, [queryClient, onViewChange]);

  const handleDeleteComplete = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["categories"] });
    setDeleteTarget(null);
    onViewChange({ kind: "all" });
  }, [queryClient, onViewChange]);

  function toggleRoot(id: string) {
    setExpandedRoots((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  if (categoriesQuery.isLoading) {
    return <div className="category-manager-loading">加载中...</div>;
  }

  if (categoriesQuery.isError) {
    return <div className="category-manager-error">加载分类失败</div>;
  }

  return (
    <div className="category-manager">
      <h2 className="category-manager-title">分类管理</h2>

      {error && <p className="category-manager-error-msg">{error}</p>}

      <div className="category-manager-create-root">
        <input
          className="category-manager-input"
          placeholder="新增一级分类名称"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleCreateRoot();
          }}
        />
        <button
          className="category-manager-btn"
          onClick={handleCreateRoot}
          disabled={createMutation.isPending || !newName.trim()}
        >
          新增一级分类
        </button>
      </div>

      <ul className="category-manager-list">
        {categories.map((root) => {
          const isExpanded = expandedRoots.has(root.id);

          return (
            <li key={root.id} className="category-manager-root">
              <div className="category-manager-row">
                <button
                  className="category-manager-expand"
                  onClick={() => toggleRoot(root.id)}
                >
                  {isExpanded ? "▾" : "▸"}
                </button>

                {renamingId === root.id ? (
                  <input
                    className="category-manager-input category-manager-rename-input"
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleRenameSave(root.id);
                      if (e.key === "Escape") setRenamingId(null);
                    }}
                    autoFocus
                  />
                ) : (
                  <span className="category-manager-name">
                    {root.name}
                    <span className="category-manager-count">
                      ({root.total_event_count})
                    </span>
                  </span>
                )}

                <div className="category-manager-actions">
                  {renamingId === root.id ? (
                    <>
                      <button
                        className="category-manager-action-btn"
                        onClick={() => handleRenameSave(root.id)}
                        disabled={
                          renameMutation.isPending || !renameValue.trim()
                        }
                      >
                        保存
                      </button>
                      <button
                        className="category-manager-action-btn"
                        onClick={() => setRenamingId(null)}
                      >
                        取消
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        className="category-manager-action-btn"
                        onClick={() => handleRenameStart(root)}
                      >
                        重命名
                      </button>
                      <button
                        className="category-manager-action-btn"
                        onClick={() => setMergeSource(root)}
                      >
                        合并
                      </button>
                      <button
                        className="category-manager-action-btn category-manager-delete-btn"
                        onClick={() => setDeleteTarget(root)}
                      >
                        删除
                      </button>
                    </>
                  )}
                </div>
              </div>

              {isExpanded && (
                <ul className="category-manager-children">
                  {root.children.map((child) => (
                    <li key={child.id} className="category-manager-child">
                      <span className="category-manager-name">
                        {child.name}
                        <span className="category-manager-count">
                          ({child.event_count})
                        </span>
                      </span>
                    </li>
                  ))}
                  <li className="category-manager-add-child">
                    <input
                      className="category-manager-input"
                      placeholder="新增二级分类名称"
                      value={newChildName[root.id] ?? ""}
                      onChange={(e) =>
                        setNewChildName((prev) => ({
                          ...prev,
                          [root.id]: e.target.value,
                        }))
                      }
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleCreateChild(root.id);
                      }}
                    />
                    <button
                      className="category-manager-btn"
                      onClick={() => handleCreateChild(root.id)}
                      disabled={
                        createMutation.isPending ||
                        !(newChildName[root.id] ?? "").trim()
                      }
                    >
                      新增二级分类
                    </button>
                  </li>
                </ul>
              )}
            </li>
          );
        })}
      </ul>

      {mergeSource && (
        <MergeDialog
          source={mergeSource}
          categories={categories}
          onClose={() => setMergeSource(null)}
          onMerged={handleMergeComplete}
        />
      )}

      {deleteTarget && (
        <DeleteCategoryDialog
          category={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onDeleted={handleDeleteComplete}
        />
      )}
    </div>
  );
}
