import type { ViewSelection } from "@/api/types";

const NAV_ITEMS: { label: string; view: ViewSelection; kind: string }[] = [
  { label: "全部记录", view: { kind: "all" }, kind: "all" },
  { label: "待分类", view: { kind: "pending" }, kind: "pending" },
  { label: "分类管理", view: { kind: "manage-categories" }, kind: "manage-categories" },
  { label: "设置", view: { kind: "settings" }, kind: "settings" },
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
        {NAV_ITEMS.map((item) => (
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
    </nav>
  );
}
