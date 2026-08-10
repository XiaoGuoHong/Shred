import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { usePersistentDraft } from "@/hooks/usePersistentDraft";

describe("usePersistentDraft", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("restores text from localStorage on mount", () => {
    localStorage.setItem("shred:composer-draft", "saved draft text");
    const { result } = renderHook(() => usePersistentDraft());
    expect(result.current.text).toBe("saved draft text");
  });

  it("starts with empty string when localStorage is empty", () => {
    const { result } = renderHook(() => usePersistentDraft());
    expect(result.current.text).toBe("");
  });

  it("updates localStorage when text changes", () => {
    const { result } = renderHook(() => usePersistentDraft());
    act(() => {
      result.current.setText("new draft");
    });
    expect(localStorage.getItem("shred:composer-draft")).toBe("new draft");
  });

  it("clearDraft removes localStorage and resets text", () => {
    localStorage.setItem("shred:composer-draft", "old draft");
    const { result } = renderHook(() => usePersistentDraft());
    act(() => {
      result.current.clearDraft();
    });
    expect(result.current.text).toBe("");
    expect(localStorage.getItem("shred:composer-draft")).toBeNull();
  });

  it("persists across multiple setText calls", () => {
    const { result } = renderHook(() => usePersistentDraft());
    act(() => {
      result.current.setText("first");
    });
    act(() => {
      result.current.setText("second");
    });
    expect(localStorage.getItem("shred:composer-draft")).toBe("second");
  });
});
