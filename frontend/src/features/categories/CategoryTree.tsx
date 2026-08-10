import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ViewSelection } from "@/api/types";

interface CategoryTreeProps {
  onSelect: (v: ViewSelection) => void;
  activeCategoryId?: string;
  onClose?: () => void;
}

export function CategoryTree({
  onSelect,
  activeCategoryId,
  onClose,
}: CategoryTreeProps) {
  const [expandedRoots, setExpandedRoots] = useState<Set<string>>(
    () => new Set(),
  );

  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.getCategories(),
  });

  const categories = categoriesQuery.data ?? [];

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

  function handleSelect(categoryId: string) {
    onSelect({ kind: "category", categoryId });
    onClose?.();
  }

  if (categoriesQuery.isLoading) {
    return <div className="category-tree-loading">加载中...</div>;
  }

  if (categoriesQuery.isError) {
    return <div className="category-tree-error">加载分类失败</div>;
  }

  if (categories.length === 0) {
    return <div className="category-tree-empty">暂无分类</div>;
  }

  return (
    <div className="category-tree">
      {categories.map((root) => {
        const isExpanded = expandedRoots.has(root.id);
        const isActive = activeCategoryId === root.id;

        return (
          <div key={root.id} className="category-tree-root">
            <button
              className={`category-tree-item category-tree-root-item${isActive ? " active" : ""}`}
              onClick={() => toggleRoot(root.id)}
            >
              <span className="category-tree-toggle">
                {isExpanded ? "▾" : "▸"}
              </span>
              <span
                className="category-tree-name"
                onClick={(e) => {
                  e.stopPropagation();
                  handleSelect(root.id);
                }}
              >
                {root.name}
              </span>
              <span className="category-tree-count">
                {root.total_event_count}
              </span>
            </button>
            {isExpanded &&
              root.children.map((child) => {
                const isChildActive = activeCategoryId === child.id;
                return (
                  <button
                    key={child.id}
                    className={`category-tree-item category-tree-child-item${isChildActive ? " active" : ""}`}
                    onClick={() => handleSelect(child.id)}
                  >
                    <span className="category-tree-name">{child.name}</span>
                    <span className="category-tree-count">
                      {child.event_count}
                    </span>
                  </button>
                );
              })}
          </div>
        );
      })}
    </div>
  );
}
