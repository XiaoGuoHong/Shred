import { useState, type ReactNode } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileDrawer } from "@/components/layout/MobileDrawer";
import type { ViewSelection } from "@/api/types";

export function AppShell({
  view,
  onViewChange,
  children,
}: {
  view: ViewSelection;
  onViewChange: (v: ViewSelection) => void;
  children: ReactNode;
}) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <button
          className="menu-button"
          onClick={() => setDrawerOpen(true)}
          aria-label="打开菜单"
        >
          ☰
        </button>
        <span className="topbar-title">Shred</span>
      </header>

      <Sidebar view={view} onViewChange={onViewChange} />

      <main className="app-main">{children}</main>

      <MobileDrawer
        open={drawerOpen}
        view={view}
        onViewChange={onViewChange}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  );
}
