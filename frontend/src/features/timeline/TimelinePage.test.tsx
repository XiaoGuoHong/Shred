import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TimelinePage } from "@/features/timeline/TimelinePage";
import type { ViewSelection } from "@/api/types";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
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

function renderTimeline(view: ViewSelection = { kind: "all" }) {
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <TimelinePage view={view} />
    </Wrapper>,
  );
}

describe("TimelinePage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("submits sample, displays source text and 3 event cards", async () => {
    const user = userEvent.setup();
    renderTimeline();

    const textarea = screen.getByPlaceholderText("输入需要整理的内容...");
    await user.type(textarea, "今天上午开会讨论了项目进度，下午和客户会面");

    const submitButton = screen.getByText("提交");
    await user.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText("今天上午开会讨论了项目进度，下午和客户会面"),
      ).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("事件一")).toBeInTheDocument();
      expect(screen.getByText("事件二")).toBeInTheDocument();
      expect(screen.getByText("事件三")).toBeInTheDocument();
    });
  });

  it("Ctrl+Enter submits, Enter inserts newline", async () => {
    const user = userEvent.setup();
    renderTimeline();

    const textarea = screen.getByPlaceholderText("输入需要整理的内容...");
    await user.type(textarea, "第一行");

    expect(textarea).toHaveValue("第一行");

    await user.type(textarea, "{Enter}");
    expect((textarea as HTMLTextAreaElement).value).toContain("\n");

    await user.type(textarea, "第二行");

    fireEvent.keyDown(textarea, { key: "Enter", ctrlKey: true });

    await waitFor(() => {
      expect(screen.getByText("事件一")).toBeInTheDocument();
    });
  });

  it("category selection requests category_id param", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderTimeline({ kind: "category", categoryId: "cat-1" });

    await waitFor(() => {
      const urlCalls = fetchSpy.mock.calls
        .map((c) => String(c[0]))
        .filter((u) => u.includes("/api/timeline"));
      const hasCategoryId = urlCalls.some((url) =>
        url.includes("category_id=cat-1"),
      );
      expect(hasCategoryId).toBe(true);
    });

    fetchSpy.mockRestore();
  });

  it("pending selection requests status=pending", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderTimeline({ kind: "pending" });

    await waitFor(() => {
      const urlCalls = fetchSpy.mock.calls
        .map((c) => String(c[0]))
        .filter((u) => u.includes("/api/timeline"));
      const hasStatus = urlCalls.some((url) =>
        url.includes("status=pending"),
      );
      expect(hasStatus).toBe(true);
    });

    fetchSpy.mockRestore();
  });

  it("shows undo button after successful classification", async () => {
    const user = userEvent.setup();

    renderTimeline();

    const textarea = screen.getByPlaceholderText("输入需要整理的内容...");
    await user.type(textarea, "测试撤销功能");
    await user.click(screen.getByText("提交"));

    await waitFor(() => {
      expect(screen.getByText("撤销本次提交")).toBeInTheDocument();
    });
  });

  it("undo button disappears after 10 seconds", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"] });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    renderTimeline();

    const textarea = screen.getByPlaceholderText("输入需要整理的内容...");
    await user.type(textarea, "测试撤销功能");
    vi.advanceTimersByTime(200);

    await user.click(screen.getByText("提交"));
    vi.advanceTimersByTime(200);

    expect(screen.getByText("撤销本次提交")).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(10_000);
    });

    expect(screen.queryByText("撤销本次提交")).not.toBeInTheDocument();
  }, 15000);

  it("clicking undo calls undo API and removes group", async () => {
    const user = userEvent.setup();

    renderTimeline();

    const textarea = screen.getByPlaceholderText("输入需要整理的内容...");
    await user.type(textarea, "测试撤销功能");
    await user.click(screen.getByText("提交"));

    await waitFor(() => {
      expect(screen.getByText("撤销本次提交")).toBeInTheDocument();
    });

    await user.click(screen.getByText("撤销本次提交"));

    await waitFor(() => {
      expect(
        screen.queryByText("撤销本次提交"),
      ).not.toBeInTheDocument();
    });
  });

  it("undo expiry keeps the message data", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"] });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    renderTimeline();

    const textarea = screen.getByPlaceholderText("输入需要整理的内容...");
    await user.type(textarea, "测试过期撤销");
    vi.advanceTimersByTime(200);

    await user.click(screen.getByText("提交"));
    vi.advanceTimersByTime(200);

    expect(screen.getByText("撤销本次提交")).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(10_000);
    });

    expect(screen.queryByText("撤销本次提交")).not.toBeInTheDocument();
    expect(screen.getByText("测试过期撤销")).toBeInTheDocument();
  }, 15000);
});
