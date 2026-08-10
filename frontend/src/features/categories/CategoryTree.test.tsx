import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CategoryTree } from "@/features/categories/CategoryTree";

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

describe("CategoryTree", () => {
  it("renders root categories from mock API", async () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryTree onSelect={vi.fn()} />
      </Wrapper>,
    );

    expect(await screen.findByText("工作")).toBeInTheDocument();
    expect(screen.getByText("个人")).toBeInTheDocument();
  });

  it("expands root to show children on toggle click", async () => {
    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryTree onSelect={vi.fn()} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    const toggleButtons = screen.getAllByText("▸");
    await user.click(toggleButtons[0]!);

    expect(await screen.findByText("会议")).toBeInTheDocument();
  });

  it("calls onSelect with category view when child clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryTree onSelect={onSelect} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    const toggleButtons = screen.getAllByText("▸");
    await user.click(toggleButtons[0]!);
    await user.click(screen.getByText("会议"));

    expect(onSelect).toHaveBeenCalledWith({
      kind: "category",
      categoryId: "cat-2",
    });
  });

  it("calls onClose after selection when provided", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryTree onSelect={vi.fn()} onClose={onClose} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    const toggleButtons = screen.getAllByText("▸");
    await user.click(toggleButtons[0]!);
    await user.click(screen.getByText("会议"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows event count badges", async () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryTree onSelect={vi.fn()} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("collapses expanded root on second toggle click", async () => {
    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryTree onSelect={vi.fn()} />
      </Wrapper>,
    );

    await screen.findByText("工作");
    const toggleButtons = screen.getAllByText("▸");
    await user.click(toggleButtons[0]!);
    expect(screen.getByText("会议")).toBeInTheDocument();

    const collapseButton = screen.getByText("▾");
    await user.click(collapseButton);
    expect(screen.queryByText("会议")).not.toBeInTheDocument();
  });

  it("highlights active category", async () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryTree onSelect={vi.fn()} activeCategoryId="cat-1" />
      </Wrapper>,
    );

    const workBtn = (await screen.findByText("工作")).closest("button");
    expect(workBtn).toHaveClass("active");
  });

  it("selects root category when name is clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <CategoryTree onSelect={onSelect} />
      </Wrapper>,
    );

    const workName = await screen.findByText("工作");
    await user.click(workName);

    expect(onSelect).toHaveBeenCalledWith({
      kind: "category",
      categoryId: "cat-1",
    });
  });
});
