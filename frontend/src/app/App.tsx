import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import type { ViewSelection } from "@/api/types";

export function App() {
  const [view, setView] = useState<ViewSelection>({ kind: "all" });

  return <AppShell view={view} onViewChange={setView} />;
}
