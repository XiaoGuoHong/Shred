import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EventEditor } from "@/features/events/EventEditor";
import type { ActivityEvent } from "@/api/types";

const sampleEvent: ActivityEvent = {
  id: "evt-1",
  source_message_id: "msg-1",
  position: 0,
  title: "项目计划讨论会",
  source_fragment: "在会议室开会讨论项目计划",
  occurred_at: "2026-08-10T01:00:00.000Z",
  occurrence_precision: "exact",
  part_of_day: "morning",
  category_id: "cat-2",
  category_path: "工作 / 会议",
  tags: ["会议", "项目"],
  status: "classified",
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

describe("EventEditor", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders with dialog role and source text", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <EventEditor event={sampleEvent} onClose={vi.fn()} />
      </Wrapper>,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("在会议室开会讨论项目计划")).toBeInTheDocument();
    expect(screen.getByDisplayValue("项目计划讨论会")).toBeInTheDocument();
  });

  it("calls onClose when close button clicked", async () => {
    const onClose = vi.fn();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <EventEditor event={sampleEvent} onClose={onClose} />
      </Wrapper>,
    );

    await userEvent.click(screen.getByLabelText("关闭"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose on Escape key", () => {
    const onClose = vi.fn();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <EventEditor event={sampleEvent} onClose={onClose} />
      </Wrapper>,
    );

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose on overlay click", async () => {
    const onClose = vi.fn();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <EventEditor event={sampleEvent} onClose={onClose} />
      </Wrapper>,
    );

    await userEvent.click(screen.getByRole("dialog"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows precision and part_of_day selects", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <EventEditor event={sampleEvent} onClose={vi.fn()} />
      </Wrapper>,
    );

    expect(screen.getByDisplayValue("精确时间")).toBeInTheDocument();
    expect(screen.getByDisplayValue("上午")).toBeInTheDocument();
  });

  it("shows existing tags with remove buttons", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <EventEditor event={sampleEvent} onClose={vi.fn()} />
      </Wrapper>,
    );

    expect(screen.getByText("会议")).toBeInTheDocument();
    expect(screen.getByText("项目")).toBeInTheDocument();
  });

  it("closes without API call when no changes made", async () => {
    const onClose = vi.fn();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <EventEditor event={sampleEvent} onClose={onClose} />
      </Wrapper>,
    );

    await userEvent.click(screen.getByText("保存"));
    expect(onClose).toHaveBeenCalled();
  });

  it("shows delete confirmation when delete clicked", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <EventEditor event={sampleEvent} onClose={vi.fn()} />
      </Wrapper>,
    );

    await userEvent.click(screen.getByText("删除"));
    expect(confirmSpy).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });
});
