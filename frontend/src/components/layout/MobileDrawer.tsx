import { useEffect, useRef } from "react";
import type { ViewSelection } from "@/api/types";
import { CategoryTree } from "@/features/categories/CategoryTree";
import { Icon, type IconName } from "@/components/icons";

const DRAWER_NAV: { label: string; view: ViewSelection; kind: string; icon: IconName }[] = [
  { label: "全部记录", view: { kind: "all" }, kind: "all", icon: "list" },
  { label: "待分类", view: { kind: "pending" }, kind: "pending", icon: "clock" },
  { label: "分类管理", view: { kind: "manage-categories" }, kind: "manage-categories", icon: "folder" },
  { label: "设置", view: { kind: "settings" }, kind: "settings", icon: "settings" },
];

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
          <span className="sidebar-brand-mark">
            <Icon name="shredMark" size={22} />
          </span>
          <span className="mobile-drawer-title">Shred</span>
          <button
            className="mobile-drawer-close"
            onClick={onClose}
            aria-label="关闭菜单"
          >
            <Icon name="x" size={18} />
          </button>
        </div>
        <nav>
          <ul className="mobile-drawer-nav">
            {DRAWER_NAV.map((item) => (
              <li key={item.kind}>
                <button
                  className={`mobile-drawer-nav-item${view.kind === item.kind ? " active" : ""}`}
                  onClick={() => {
                    onViewChange(item.view);
                    onClose();
                  }}
                >
                  <Icon name={item.icon} size={17} className="sidebar-nav-icon" />
                  <span>{item.label}</span>
                </button>
              </li>
            ))}
          </ul>
          <CategoryTree
            onSelect={onViewChange}
            activeCategoryId={
              view.kind === "category" ? view.categoryId : undefined
            }
            onClose={onClose}
          />
        </nav>
      </div>
    </div>
  );
}
