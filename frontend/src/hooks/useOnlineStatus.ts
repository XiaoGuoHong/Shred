import { useState, useEffect, useCallback } from "react";
import { api } from "@/api/client";

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isBackendReachable, setIsBackendReachable] = useState(true);

  const checkBackend = useCallback(async () => {
    try {
      await api.health();
      setIsBackendReachable(true);
    } catch {
      setIsBackendReachable(false);
    }
  }, []);

  useEffect(() => {
    checkBackend();
  }, [checkBackend]);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      checkBackend();
    };
    const handleOffline = () => setIsOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [checkBackend]);

  return { isOnline, isBackendReachable, checkBackend };
}
