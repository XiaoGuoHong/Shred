import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CategoryManager } from "@/features/categories/CategoryManager";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  }
  Wrapper.displayName = "Wrapper";
  return Wrapper;
}

describe("CategoryManager", () => {
  it("renders title and create root button", async () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryManager onViewChange={vi.fn()} />
      </Wrapper>,
    );

    expect(
      await screen.findByText("分类管理"),
    ).toBeInTheDocument();
    expect(screen.getByText("新增一级分类")).toBeInTheDocument();
  });

  it("displays root categories with event counts", async () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryManager onViewChange={vi.fn()} />
      </Wrapper>,
    );

    expect(await screen.findByText("工作")).toBeInTheDocument();
    expect(screen.getByText("个人")).toBeInTheDocument();
    expect(screen.getByText("(2)")).toBeInTheDocument();
    expect(screen.getByText("(1)")).toBeInTheDocument();
  });

  it("expands root to show children and add-child input", async () => {
    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryManager onViewChange={vi.fn()} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    const expandButtons = screen.getAllByText("▸");
    await user.click(expandButtons[0]!);

    expect(await screen.findByText("会议")).toBeInTheDocument();
    expect(screen.getByText("新增二级分类")).toBeInTheDocument();
  });

  it("creates category on button click", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryManager onViewChange={vi.fn()} />
      </Wrapper>,
    );

    await screen.findByText("新增一级分类");
    const input = screen.getByPlaceholderText("新增一级分类名称");
    await user.type(input, "新分类");

    await user.click(screen.getByText("新增一级分类"));

    await waitFor(() => {
      const createCalls = fetchSpy.mock.calls.filter(
        (c) =>
          String(c[0]).includes("/api/categories") &&
          c[1]?.method === "POST",
      );
      expect(createCalls.length).toBeGreaterThan(0);
    });

    fetchSpy.mockRestore();
  });

  it("enters rename mode and shows save/cancel", async () => {
    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryManager onViewChange={vi.fn()} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    const renameButtons = screen.getAllByText("重命名");
    await user.click(renameButtons[0]!);

    expect(screen.getByText("保存")).toBeInTheDocument();
    expect(screen.getByText("取消")).toBeInTheDocument();
  });

  it("cancels rename on Escape", async () => {
    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryManager onViewChange={vi.fn()} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    await user.click(screen.getAllByText("重命名")[0]!);

    const input = screen.getByDisplayValue("工作");
    await user.keyboard("{Escape}");

    expect(screen.queryByText("保存")).not.toBeInTheDocument();
    const renameButtons = screen.getAllByText("重命名");
    expect(renameButtons.length).toBeGreaterThanOrEqual(1);
  });

  it("opens merge dialog", async () => {
    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryManager onViewChange={vi.fn()} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    await user.click(screen.getAllByText("合并")[0]!);

    expect(
      await screen.findByRole("dialog", { name: "合并分类" }),
    ).toBeInTheDocument();
  });

  it("opens delete dialog", async () => {
    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryManager onViewChange={vi.fn()} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    await user.click(screen.getAllByText("删除")[0]!);

    expect(
      await screen.findByRole("dialog", { name: "删除分类" }),
    ).toBeInTheDocument();
  });

  it("does not show 新增二级分类 on children", async () => {
    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryManager onViewChange={vi.fn()} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    await user.click(screen.getAllByText("▸")[0]!);

    await screen.findByText("会议");
    const addChildButtons = screen.getAllByText("新增二级分类");
    expect(addChildButtons.length).toBe(1);
  });

  it("creates child category with correct parent_id", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryManager onViewChange={vi.fn()} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    await user.click(screen.getAllByText("▸")[0]!);

    const childInput = screen.getByPlaceholderText("新增二级分类名称");
    await user.type(childInput, "新子分类");
    await user.click(screen.getByText("新增二级分类"));

    await waitFor(() => {
      const createCalls = fetchSpy.mock.calls.filter(
        (c) =>
          String(c[0]).includes("/api/categories") &&
          c[1]?.method === "POST",
      );
      const hasChildCall = createCalls.some((call) => {
        const body = JSON.parse(
          (call[1] as RequestInit).body as string,
        );
        return body.parent_id === "cat-1";
      });
      expect(hasChildCall).toBe(true);
    });

    fetchSpy.mockRestore();
  });
});
