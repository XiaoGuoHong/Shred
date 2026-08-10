import { useEffect, useRef } from "react";
import type { ViewSelection } from "@/api/types";
import { CategoryTree } from "@/features/categories/CategoryTree";

export function MobileDrawer({
  open,
  view,
  onViewChange,
  onClose,
}: {
  open: boolean;
  view: ViewSelection;
  onViewChange: (v: ViewSelection) => void;
  onClose: () => void;
}) {
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="mobile-drawer-overlay">
      <div ref={drawerRef} className="mobile-drawer">
        <div className="mobile-drawer-header">
          <span className="mobile-drawer-title">Shred</span>
          <button
            className="mobile-drawer-close"
            onClick={onClose}
            aria-label="关闭菜单"
          >
            ✕
          </button>
        </div>
        <nav>
          <ul className="mobile-drawer-nav">
            <li>
              <button
                className={`mobile-drawer-nav-item${view.kind === "all" ? " active" : ""}`}
                onClick={() => {
                  onViewChange({ kind: "all" });
                  onClose();
                }}
              >
                全部记录
              </button>
            </li>
            <li>
              <button
                className={`mobile-drawer-nav-item${view.kind === "pending" ? " active" : ""}`}
                onClick={() => {
                  onViewChange({ kind: "pending" });
                  onClose();
                }}
              >
                待分类
              </button>
            </li>
          </ul>
          <CategoryTree
            onSelect={onViewChange}
            activeCategoryId={
              view.kind === "category" ? view.categoryId : undefined
            }
            onClose={onClose}
          />
          <ul className="mobile-drawer-nav">
            <li>
              <button
                className={`mobile-drawer-nav-item${view.kind === "manage-categories" ? " active" : ""}`}
                onClick={() => {
                  onViewChange({ kind: "manage-categories" });
                  onClose();
                }}
              >
                分类管理
              </button>
            </li>
            <li>
              <button
                className={`mobile-drawer-nav-item${view.kind === "settings" ? " active" : ""}`}
                onClick={() => {
                  onViewChange({ kind: "settings" });
                  onClose();
                }}
              >
                设置
              </button>
            </li>
          </ul>
        </nav>
      </div>
    </div>
  );
}
