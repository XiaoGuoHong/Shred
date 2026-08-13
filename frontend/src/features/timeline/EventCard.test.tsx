import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EventCard } from "@/features/timeline/EventCard";
import type { ActivityEvent } from "@/api/types";

function makeEvent(overrides: Partial<ActivityEvent> = {}): ActivityEvent {
  return {
    id: "evt-1",
    source_message_id: "msg-1",
    position: 0,
    title: "向10家公司投递简历",
    source_fragment: "投递简历",
    occurred_at: "2026-08-12T08:30:00Z",
    occurrence_precision: "exact",
    part_of_day: "",
    category_id: "cat-1",
    category_path: ["求职", "投递简历"],
    tags: ["投简历", "10家公司"],
    status: "classified",
    ...overrides,
  };
}

function renderCard(event: ActivityEvent) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <EventCard event={event} />
    </QueryClientProvider>,
  );
}

describe("EventCard", () => {
  it("renders title, tags, category and time", () => {
    renderCard(makeEvent());
    expect(screen.getByText("向10家公司投递简历")).toBeInTheDocument();
    expect(screen.getByText("投简历")).toBeInTheDocument();
    expect(screen.getByText("10家公司")).toBeInTheDocument();
    expect(screen.getByText("求职 / 投递简历")).toBeInTheDocument();
    expect(screen.getByText("16:30")).toBeInTheDocument();
  });

  it.each<[string[] | undefined, string]>([
    [["求职"], "briefcase"],
    [["学习"], "book"],
    [["工作"], "doc"],
    [["健身"], "dumbbell"],
    [["生活"], "home"],
    [["其他"], "sparkle"],
    [undefined, "sparkle"],
  ])("maps category %s to icon %s", (path, expected) => {
    renderCard(makeEvent({ category_path: path }));
    const icon = document.querySelector(".event-card-icon [data-icon]");
    expect(icon?.getAttribute("data-icon")).toBe(expected);
  });

  it("shows the ··· menu and opens the editor", async () => {
    const user = userEvent.setup();
    renderCard(makeEvent());

    expect(screen.queryByText("编辑")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "更多操作" }));

    expect(screen.getByText("编辑")).toBeInTheDocument();
    expect(screen.getByText("修改分类")).toBeInTheDocument();
    expect(screen.getByText("删除")).toBeInTheDocument();

    await user.click(screen.getByText("编辑"));
    expect(
      await screen.findByLabelText("标题"),
    ).toBeInTheDocument();
  });

  it("deletes after confirmation", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    renderCard(makeEvent());

    await user.click(screen.getByRole("button", { name: "更多操作" }));
    await user.click(screen.getByText("删除"));

    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining("向10家公司投递简历"),
    );
    confirmSpy.mockRestore();
  });

  it("keeps the card when deletion is cancelled", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    renderCard(makeEvent());

    await user.click(screen.getByRole("button", { name: "更多操作" }));
    await user.click(screen.getByText("删除"));

    expect(screen.getByText("向10家公司投递简历")).toBeInTheDocument();
    confirmSpy.mockRestore();
  });
});
