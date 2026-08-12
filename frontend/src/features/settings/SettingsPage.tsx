import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const [localBaseUrl, setLocalBaseUrl] = useState("");
  const [localModel, setLocalModel] = useState("");
  const [initialized, setInitialized] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);
  const [clearMessage, setClearMessage] = useState<string | null>(null);

  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.getSettings(),
  });

  if (settingsQuery.data && !initialized) {
    setLocalBaseUrl(settingsQuery.data.api_base_url);
    setLocalModel(settingsQuery.data.model_name);
    setInitialized(true);
  }

  const settings = settingsQuery.data;

  const saveMutation = useMutation({
    mutationFn: (data: { api_base_url?: string; model_name?: string }) =>
      api.updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      setSaveError(null);
    },
    onError: (err: Error) => {
      setSaveError(err.message);
    },
  });

  const testMutation = useMutation({
    mutationFn: () => api.testConnection(),
    onSuccess: (data) => {
      if (data.ok) {
        setTestResult("连接成功");
        setTestError(null);
      } else {
        setTestError(data.error_message ?? "连接失败");
        setTestResult(null);
      }
    },
    onError: (err: Error) => {
      setTestError(err.message);
      setTestResult(null);
    },
  });

  const clearMutation = useMutation({
    mutationFn: () => api.clearPreferences(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      setClearConfirm(false);
      setClearMessage("偏好记忆已清除");
    },
    onError: (err: Error) => {
      setClearMessage(err.message);
    },
  });

  const handleSave = useCallback(() => {
    setSaveError(null);
    setTestResult(null);
    setTestError(null);
    saveMutation.mutate({
      api_base_url: localBaseUrl,
      model_name: localModel,
    });
  }, [localBaseUrl, localModel, saveMutation]);

  const handleTestConnection = useCallback(() => {
    setTestResult(null);
    setTestError(null);
    testMutation.mutate();
  }, [testMutation]);

  const handleClearConfirm = useCallback(() => {
    setClearConfirm(false);
    clearMutation.mutate();
  }, [clearMutation]);

  const handleExport = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault();
      try {
        await api.exportData();
      } catch (err) {
        setSaveError(err instanceof Error ? err.message : "导出失败");
      }
    },
    [],
  );

  if (settingsQuery.isLoading) {
    return <div className="settings-loading">加载中...</div>;
  }

  if (settingsQuery.isError) {
    return <div className="settings-error">加载设置失败</div>;
  }

  return (
    <div className="settings-page">
      <h2 className="settings-title">设置</h2>

      <div className="settings-section">
        <h3 className="settings-section-title">模型配置</h3>

        <div className="settings-field">
          <label className="settings-label">API 地址</label>
          <input
            className="settings-input"
            type="text"
            value={localBaseUrl}
            onChange={(e) => setLocalBaseUrl(e.target.value)}
            placeholder="https://api.openai.com/v1"
          />
        </div>

        <div className="settings-field">
          <label className="settings-label">模型名称</label>
          <input
            className="settings-input"
            type="text"
            value={localModel}
            onChange={(e) => setLocalModel(e.target.value)}
            placeholder="gpt-4o"
          />
        </div>

        <p className="settings-privacy-notice">
          使用云端模型时，记录内容会发送到你配置的模型服务。API Key
          仅从本地 Docker 环境读取，不会显示在页面中。
        </p>

        <p className="settings-lan-warning">
          默认绑定仅限本机访问（127.0.0.1）。若开启局域网访问，Shred
          本身不提供认证机制，请注意网络安全。PWA 功能需要 HTTPS
          或同设备 localhost 环境。
        </p>

        <div className="settings-field">
          <label className="settings-label">API Key 状态</label>
          <span className="settings-status">
            {settings?.api_key_configured ? (
              <span className="settings-status-ok">已配置</span>
            ) : (
              <span className="settings-status-missing">未配置</span>
            )}
          </span>
        </div>

        <div className="settings-field">
          <label className="settings-label">偏好记忆数量</label>
          <span className="settings-value">{settings?.preference_count ?? 0}</span>
        </div>
      </div>

      <div className="settings-section">
        <h3 className="settings-section-title">操作</h3>

        <div className="settings-actions">
          <button
            className="settings-btn settings-btn-primary"
            onClick={handleSave}
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending ? "保存中..." : "保存配置"}
          </button>

          <button
            className="settings-btn settings-btn-outline"
            onClick={handleTestConnection}
            disabled={testMutation.isPending}
          >
            {testMutation.isPending ? "测试中..." : "测试连接"}
          </button>
        </div>

        {saveError && <p className="settings-error-msg">{saveError}</p>}

        {testResult && (
          <p className="settings-success-msg">{testResult}</p>
        )}
        {testError && <p className="settings-error-msg">{testError}</p>}
      </div>

      <div className="settings-section">
        <h3 className="settings-section-title">数据管理</h3>

        <div className="settings-actions">
          {clearConfirm ? (
            <div className="settings-confirm-row">
              <span className="settings-confirm-text">
                确定要清除所有偏好记忆吗？
              </span>
              <button
                className="settings-btn settings-btn-danger"
                onClick={handleClearConfirm}
                disabled={clearMutation.isPending}
              >
                确认清除
              </button>
              <button
                className="settings-btn settings-btn-outline"
                onClick={() => setClearConfirm(false)}
              >
                取消
              </button>
            </div>
          ) : (
            <button
              className="settings-btn settings-btn-danger"
              onClick={() => {
                setClearConfirm(true);
                setClearMessage(null);
              }}
            >
              清除偏好记忆
            </button>
          )}

          <a
            className="settings-btn settings-btn-outline"
            href="/api/export"
            onClick={handleExport}
          >
            导出数据
          </a>
        </div>

        {clearMessage && (
          <p className="settings-message">{clearMessage}</p>
        )}
      </div>
    </div>
  );
}
