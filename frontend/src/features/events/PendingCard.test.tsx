import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PendingSource, PendingEvent, PendingCard } from "@/features/events/PendingCard";
import type { SourceMessage, ActivityEvent } from "@/api/types";

const errorMessage: SourceMessage = {
  id: "msg-err",
  submission_uuid: "uuid-err",
  original_text: "处理失败的内容",
  submitted_at: "2026-08-10T01:00:00.000Z",
  timezone: "Asia/Shanghai",
  status: "error",
  error_code: "classify_failed",
  error_summary: "分类失败，请重试",
};

const pendingEvent: ActivityEvent = {
  id: "evt-pending",
  source_message_id: "msg-err",
  position: 0,
  title: "待处理事件",
  source_fragment: "待处理片段",
  occurred_at: "2026-08-10T01:00:00.000Z",
  occurrence_precision: "none",
  part_of_day: "",
  tags: [],
  status: "pending",
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe("PendingSource", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders source text and error summary", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <PendingSource message={errorMessage} />
      </Wrapper>,
    );

    expect(screen.getByText("处理失败的内容")).toBeInTheDocument();
    expect(screen.getByText("分类失败，请重试")).toBeInTheDocument();
  });

  it("renders retry and delete buttons", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <PendingSource message={errorMessage} />
      </Wrapper>,
    );

    expect(screen.getByText("重新分类")).toBeInTheDocument();
    expect(screen.getByText("删除")).toBeInTheDocument();
  });

  it("shows confirmation on delete click", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <PendingSource message={errorMessage} />
      </Wrapper>,
    );

    await userEvent.click(screen.getByText("删除"));
    expect(confirmSpy).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });
});

describe("PendingEvent", () => {
  it("renders event title and source fragment", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <PendingEvent event={pendingEvent} />
      </Wrapper>,
    );

    expect(screen.getByText("待处理事件")).toBeInTheDocument();
    expect(screen.getByText("待处理片段")).toBeInTheDocument();
  });

  it("renders edit and reclassify buttons", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <PendingEvent event={pendingEvent} />
      </Wrapper>,
    );

    expect(screen.getByText("手动编辑")).toBeInTheDocument();
    expect(screen.getByText("重新分类")).toBeInTheDocument();
  });
});

describe("PendingCard", () => {
  it("renders source and event sections", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <PendingCard message={errorMessage} events={[pendingEvent]} />
      </Wrapper>,
    );

    expect(screen.getByText("处理失败的内容")).toBeInTheDocument();
    expect(screen.getByText("待处理事件")).toBeInTheDocument();
  });
});
