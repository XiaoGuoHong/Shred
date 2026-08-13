import { useState, type ReactNode } from "react";
import { TopNav } from "@/components/layout/TopNav";
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
      <TopNav
        view={view}
        onViewChange={onViewChange}
        onMenuClick={() => setDrawerOpen(true)}
      />

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
