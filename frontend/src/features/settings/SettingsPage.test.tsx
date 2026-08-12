import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { SettingsPage } from "@/features/settings/SettingsPage";
import type { SettingsConfig } from "@/api/types";

const defaultSettings: SettingsConfig = {
  api_base_url: "https://api.openai.com/v1",
  model_name: "gpt-4o",
  api_key_configured: true,
  preference_count: 3,
};

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

describe("SettingsPage", () => {
  beforeEach(() => {
    server.use(
      http.get("/api/settings", () =>
        HttpResponse.json(defaultSettings),
      ),
    );
  });

  it("displays base URL, model name, key status, preference count", async () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <SettingsPage />
      </Wrapper>,
    );

    expect(await screen.findByDisplayValue("https://api.openai.com/v1")).toBeInTheDocument();
    expect(screen.getByDisplayValue("gpt-4o")).toBeInTheDocument();
    expect(screen.getByText("已配置")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("shows 未配置 when key is not configured", async () => {
    server.use(
      http.get("/api/settings", () =>
        HttpResponse.json({ ...defaultSettings, api_key_configured: false }),
      ),
    );

    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <SettingsPage />
      </Wrapper>,
    );

    expect(await screen.findByText("未配置")).toBeInTheDocument();
  });

  it("has no password or API key input field", async () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <SettingsPage />
      </Wrapper>,
    );

    await screen.findByText("API 地址");

    const inputs = screen.getAllByRole("textbox");
    for (const input of inputs) {
      const el = input as HTMLInputElement;
      expect(el.type).not.toBe("password");
    }
    const labels = screen.getAllByRole("textbox");
    const hasKeyInput = labels.some(
      (el) =>
        el.getAttribute("placeholder")?.toLowerCase().includes("key") ||
        el.getAttribute("placeholder")?.toLowerCase().includes("password") ||
        el.getAttribute("name")?.toLowerCase().includes("key") ||
        el.getAttribute("name")?.toLowerCase().includes("password"),
    );
    expect(hasKeyInput).toBe(false);
  });

  it("shows successful connection test result", async () => {
    server.use(
      http.post("/api/settings/test-connection", () =>
        HttpResponse.json({ ok: true }),
      ),
    );

    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <SettingsPage />
      </Wrapper>,
    );

    await screen.findByText("测试连接");
    await user.click(screen.getByText("测试连接"));

    expect(await screen.findByText("连接成功")).toBeInTheDocument();
  });

  it("shows connection test error", async () => {
    server.use(
      http.post("/api/settings/test-connection", () =>
        HttpResponse.json({
          ok: false,
          error_code: "model_unreachable",
          error_message: "无法连接到 API 服务器",
        }),
      ),
    );

    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <SettingsPage />
      </Wrapper>,
    );

    await screen.findByText("测试连接");
    await user.click(screen.getByText("测试连接"));

    expect(await screen.findByText("无法连接到 API 服务器")).toBeInTheDocument();
  });

  it("preserves form values on save error", async () => {
    server.use(
      http.patch("/api/settings", () =>
        HttpResponse.json(
          { error: { code: "invalid_url", message: "无效的 API 地址" } },
          { status: 422 },
        ),
      ),
    );

    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <SettingsPage />
      </Wrapper>,
    );

    await screen.findByDisplayValue("https://api.openai.com/v1");
    const urlInput = screen.getByDisplayValue("https://api.openai.com/v1");
    await user.clear(urlInput);
    await user.type(urlInput, "invalid-url");

    await user.click(screen.getByText("保存配置"));

    await waitFor(() => {
      expect(screen.getByText("无效的 API 地址")).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue("invalid-url")).toBeInTheDocument();
  });

  it("requires confirmation before clearing preferences", async () => {
    server.use(
      http.delete("/api/preferences", () =>
        new HttpResponse(null, { status: 204 }),
      ),
    );

    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <SettingsPage />
      </Wrapper>,
    );

    await screen.findByText("清除偏好记忆");
    await user.click(screen.getByText("清除偏好记忆"));

    expect(screen.getByText("确定要清除所有偏好记忆吗？")).toBeInTheDocument();
    expect(screen.getByText("确认清除")).toBeInTheDocument();
    expect(screen.getByText("取消")).toBeInTheDocument();

    await user.click(screen.getByText("确认清除"));

    await waitFor(() => {
      expect(screen.getByText("偏好记忆已清除")).toBeInTheDocument();
    });
  });

  it("triggers export download", async () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <SettingsPage />
      </Wrapper>,
    );

    await screen.findByText("导出数据");

    const exportLink = screen.getByText("导出数据");
    expect(exportLink.tagName).toBe("A");
    expect(exportLink.getAttribute("href")).toBe("/api/export");
  });

  it("displays privacy notice", async () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <SettingsPage />
      </Wrapper>,
    );

    expect(
      await screen.findByText(/使用云端模型时/),
    ).toBeInTheDocument();
  });

  it("displays LAN warning", async () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <SettingsPage />
      </Wrapper>,
    );

    expect(
      await screen.findByText(/默认绑定仅限本机访问/),
    ).toBeInTheDocument();
  });

  it("save does not trigger test-connection", async () => {
    let testCalled = false;
    server.use(
      http.patch("/api/settings", () =>
        HttpResponse.json(defaultSettings),
      ),
      http.post("/api/settings/test-connection", () => {
        testCalled = true;
        return HttpResponse.json({ ok: true });
      }),
    );

    const user = userEvent.setup();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <SettingsPage />
      </Wrapper>,
    );

    await screen.findByText("保存配置");
    await user.click(screen.getByText("保存配置"));

    await waitFor(() => {
      expect(testCalled).toBe(false);
    });
  });
});
