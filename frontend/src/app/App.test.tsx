import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { App } from "@/app/App";
import { Providers } from "@/app/providers";

function renderApp() {
  return render(
    <Providers>
      <App />
    </Providers>,
  );
}

describe("App", () => {
  it("renders all navigation labels in Chinese", () => {
    renderApp();

    expect(screen.getByText("全部记录")).toBeInTheDocument();
    expect(screen.getByText("待分类")).toBeInTheDocument();
    expect(screen.getByText("分类管理")).toBeInTheDocument();
    expect(screen.getByText("设置")).toBeInTheDocument();
  });

  it("renders the composer on the default view", () => {
    renderApp();

    expect(
      screen.getByPlaceholderText("输入需要整理的内容..."),
    ).toBeInTheDocument();
  });

  it("marks the active navigation item", () => {
    renderApp();

    const allButton = screen.getByRole("button", { name: "全部记录" });
    expect(allButton).toHaveClass("active");

    const pendingButton = screen.getByRole("button", { name: "待分类" });
    expect(pendingButton).not.toHaveClass("active");
  });
});
