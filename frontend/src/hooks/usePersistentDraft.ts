import { useState, useEffect, useCallback, useRef } from "react";

const DRAFT_KEY = "shred:composer-draft";

export function usePersistentDraft() {
  const [text, setText] = useState<string>(
    () => localStorage.getItem(DRAFT_KEY) ?? "",
  );
  const skipSaveRef = useRef(false);

  useEffect(() => {
    if (skipSaveRef.current) {
      skipSaveRef.current = false;
      return;
    }
    localStorage.setItem(DRAFT_KEY, text);
  }, [text]);

  const clearDraft = useCallback(() => {
    localStorage.removeItem(DRAFT_KEY);
    skipSaveRef.current = true;
    setText("");
  }, []);

  return { text, setText, clearDraft };
}
