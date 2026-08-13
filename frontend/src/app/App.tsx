import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { TimelinePage } from "@/features/timeline/TimelinePage";
import { CategoryManager } from "@/features/categories/CategoryManager";
import { SettingsPage } from "@/features/settings/SettingsPage";
import type { ViewSelection } from "@/api/types";

export function App() {
  const [view, setView] = useState<ViewSelection>({ kind: "all" });

  return (
    <AppShell view={view} onViewChange={setView}>
      {view.kind === "manage-categories" ? (
        <CategoryManager onViewChange={setView} />
      ) : view.kind === "settings" ? (
        <SettingsPage />
      ) : (
        <TimelinePage view={view} onViewChange={setView} />
      )}
    </AppShell>
  );
}
