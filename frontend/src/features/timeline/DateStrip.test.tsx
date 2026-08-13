import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DateStrip } from "@/features/timeline/DateStrip";

function renderStrip(selected = new Date(2026, 7, 12), marked: string[] = []) {
  const onSelect = vi.fn();
  const utils = render(
    <DateStrip
      selected={selected}
      markedKeys={new Set(marked)}
      onSelect={onSelect}
    />,
  );
  return { onSelect, ...utils };
}

describe("DateStrip", () => {
  it("renders the week of the selected date", () => {
    renderStrip();
    expect(screen.getByText("一")).toBeInTheDocument();
    expect(screen.getByText("日")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("marks the selected day with pressed state", () => {
    renderStrip();
    const selected = screen.getByRole("button", { name: "三 12" });
    expect(selected).toHaveAttribute("aria-pressed", "true");
  });

  it("selects a date on click", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderStrip();
    await user.click(screen.getByRole("button", { name: "四 13" }));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ getDate: expect.any(Function) }),
    );
    const picked = onSelect.mock.calls[0]?.[0] as Date;
    expect(picked).toBeDefined();
    expect(picked.getDate()).toBe(13);
  });

  it("shifts a week with the next button", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderStrip();
    await user.click(screen.getByRole("button", { name: "下一周" }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    const picked = onSelect.mock.calls[0]?.[0] as Date;
    expect(picked).toBeDefined();
    expect(picked.getDate()).toBe(19); // same weekday, next week
  });

  it("marks days that have records", () => {
    renderStrip(new Date(2026, 7, 12), ["2026-08-13"]);
    const marked = screen.getByRole("button", { name: "四 13" });
    expect(marked.querySelector(".date-strip-dot")).toHaveClass("marked");
  });
});
