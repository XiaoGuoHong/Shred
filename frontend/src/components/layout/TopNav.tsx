import { useEffect, useRef, useState } from "react";
import type { ViewSelection } from "@/api/types";
import { Icon, type IconName } from "@/components/icons";
import { CategoryTree } from "@/features/categories/CategoryTree";

const PRIMARY_NAV: { label: string; view: ViewSelection; kind: string; icon: IconName }[] = [
  { label: "全部记录", view: { kind: "all" }, kind: "all", icon: "list" },
  { label: "待分类", view: { kind: "pending" }, kind: "pending", icon: "clock" },
];

const SECONDARY_NAV: { label: string; view: ViewSelection; kind: string; icon: IconName }[] = [
  { label: "分类管理", view: { kind: "manage-categories" }, kind: "manage-categories", icon: "folder" },
  { label: "设置", view: { kind: "settings" }, kind: "settings", icon: "settings" },
];

export function TopNav({
  view,
  onViewChange,
  onMenuClick,
}: {
  view: ViewSelection;
  onViewChange: (v: ViewSelection) => void;
  onMenuClick: () => void;
}) {
  const [categoryOpen, setCategoryOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!categoryOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setCategoryOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [categoryOpen]);

  const isCategoryActive = view.kind === "category";

  return (
    <header className="top-nav">
      <button
        className="top-nav-brand"
        onClick={() => onViewChange({ kind: "all" })}
        aria-label="Shred 首页"
      >
        <span className="sidebar-brand-mark">
          <Icon name="shredMark" size={20} />
        </span>
        <span className="top-nav-title">Shred</span>
      </button>

      <nav className="top-nav-tabs" aria-label="主导航">
        {PRIMARY_NAV.map((item) => (
          <button
            key={item.kind}
            className={`top-nav-item${view.kind === item.kind ? " active" : ""}`}
            onClick={() => onViewChange(item.view)}
          >
            <Icon name={item.icon} size={15} />
            <span>{item.label}</span>
          </button>
        ))}
        <div className="top-nav-dropdown" ref={dropdownRef}>
          <button
            className={`top-nav-item${isCategoryActive ? " active" : ""}`}
            onClick={() => setCategoryOpen((v) => !v)}
            aria-expanded={categoryOpen}
          >
            <Icon name="folder" size={15} />
            <span>分类</span>
            <Icon
              name="chevronRight"
              size={12}
              className="top-nav-dropdown-chevron"
            />
          </button>
          {categoryOpen && (
            <div className="top-nav-dropdown-panel">
              <CategoryTree
                onSelect={(v) => {
                  onViewChange(v);
                  setCategoryOpen(false);
                }}
                activeCategoryId={
                  view.kind === "category" ? view.categoryId : undefined
                }
              />
            </div>
          )}
        </div>
      </nav>

      <div className="top-nav-spacer" />

      <nav className="top-nav-tabs top-nav-tabs-secondary" aria-label="次要导航">
        {SECONDARY_NAV.map((item) => (
          <button
            key={item.kind}
            className={`top-nav-item${view.kind === item.kind ? " active" : ""}`}
            onClick={() => onViewChange(item.view)}
          >
            <Icon name={item.icon} size={15} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <button className="menu-button top-nav-menu" onClick={onMenuClick} aria-label="打开菜单">
        <Icon name="menu" size={18} />
      </button>
    </header>
  );
}
