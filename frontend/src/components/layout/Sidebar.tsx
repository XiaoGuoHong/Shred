import type { ViewSelection } from "@/api/types";
import { CategoryTree } from "@/features/categories/CategoryTree";

const TOP_NAV: { label: string; view: ViewSelection; kind: string }[] = [
  { label: "全部记录", view: { kind: "all" }, kind: "all" },
  { label: "待分类", view: { kind: "pending" }, kind: "pending" },
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
        <span className="sidebar-title">Shred</span>
      </div>
      <ul className="sidebar-nav">
        {TOP_NAV.map((item) => (
          <li key={item.kind}>
            <button
              className={`sidebar-nav-item${view.kind === item.kind ? " active" : ""}`}
              onClick={() => onViewChange(item.view)}
            >
              {item.label}
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
      <ul className="sidebar-nav">
        <li>
          <button
            className={`sidebar-nav-item${view.kind === "manage-categories" ? " active" : ""}`}
            onClick={() => onViewChange({ kind: "manage-categories" })}
          >
            分类管理
          </button>
        </li>
        <li>
          <button
            className={`sidebar-nav-item${view.kind === "settings" ? " active" : ""}`}
            onClick={() => onViewChange({ kind: "settings" })}
          >
            设置
          </button>
        </li>
      </ul>
    </nav>
  );
}
