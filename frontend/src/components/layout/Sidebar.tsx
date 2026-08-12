import type { ViewSelection } from "@/api/types";
import { CategoryTree } from "@/features/categories/CategoryTree";
import { Icon, type IconName } from "@/components/icons";

const TOP_NAV: { label: string; view: ViewSelection; kind: string; icon: IconName }[] = [
  { label: "全部记录", view: { kind: "all" }, kind: "all", icon: "list" },
  { label: "待分类", view: { kind: "pending" }, kind: "pending", icon: "clock" },
];

const BOTTOM_NAV: { label: string; view: ViewSelection; kind: string; icon: IconName }[] = [
  { label: "分类管理", view: { kind: "manage-categories" }, kind: "manage-categories", icon: "folder" },
  { label: "设置", view: { kind: "settings" }, kind: "settings", icon: "settings" },
];

export function Sidebar({
  view,
  onViewChange,
}: {
  view: ViewSelection;
  onViewChange: (v: ViewSelection) => void;
}) {
  return (
    <nav className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-brand-mark">
          <Icon name="shredMark" size={22} />
        </span>
        <span className="sidebar-title">Shred</span>
      </div>
      <ul className="sidebar-nav">
        {TOP_NAV.map((item) => (
          <li key={item.kind}>
            <button
              className={`sidebar-nav-item${view.kind === item.kind ? " active" : ""}`}
              onClick={() => onViewChange(item.view)}
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
      />
      <ul className="sidebar-nav sidebar-nav-bottom">
        {BOTTOM_NAV.map((item) => (
          <li key={item.kind}>
            <button
              className={`sidebar-nav-item${view.kind === item.kind ? " active" : ""}`}
              onClick={() => onViewChange(item.view)}
            >
              <Icon name={item.icon} size={17} className="sidebar-nav-icon" />
              <span>{item.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
