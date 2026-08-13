import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TopNav } from "@/components/layout/TopNav";

function renderNav(view: Parameters<typeof TopNav>[0]["view"] = { kind: "all" }) {
  const onViewChange = vi.fn();
  const onMenuClick = vi.fn();
  const utils = render(
    <TopNav
      view={view}
      onViewChange={onViewChange}
      onMenuClick={onMenuClick}
    />,
  );
  return { onViewChange, onMenuClick, ...utils };
}

describe("TopNav", () => {
  it("renders all navigation labels", () => {
    renderNav();
    expect(screen.getByRole("button", { name: /全部记录/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /待分类/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /分类管理/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /设置/ })).toBeInTheDocument();
  });

  it("marks the active view", () => {
    renderNav({ kind: "settings" });
    expect(screen.getByRole("button", { name: /设置/ })).toHaveClass("active");
    expect(screen.getByRole("button", { name: /全部记录/ })).not.toHaveClass(
      "active",
    );
  });

  it("emits view changes and menu clicks", async () => {
    const user = userEvent.setup();
    const { onViewChange, onMenuClick } = renderNav();

    await user.click(screen.getByRole("button", { name: /待分类/ }));
    expect(onViewChange).toHaveBeenCalledWith({ kind: "pending" });

    await user.click(screen.getByRole("button", { name: "打开菜单" }));
    expect(onMenuClick).toHaveBeenCalled();
  });
});
