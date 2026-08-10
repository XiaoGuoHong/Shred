import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { TimelinePage } from "@/features/timeline/TimelinePage";
import type { ViewSelection } from "@/api/types";

export function App() {
  const [view, setView] = useState<ViewSelection>({ kind: "all" });

  return (
    <AppShell view={view} onViewChange={setView}>
      {view.kind === "manage-categories" ? (
        <div className="placeholder-page">
          <p className="placeholder-text">分类管理（即将推出）</p>
        </div>
      ) : view.kind === "settings" ? (
        <div className="placeholder-page">
          <p className="placeholder-text">设置（即将推出）</p>
        </div>
      ) : (
        <TimelinePage view={view} />
      )}
    </AppShell>
  );
}
