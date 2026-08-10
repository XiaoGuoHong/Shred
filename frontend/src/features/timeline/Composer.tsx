import { useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, buildSubmissionInput } from "@/api/client";
import type { TimelineGroup, TimelinePage, SubmitMessageInput } from "@/api/types";
import { usePersistentDraft } from "@/hooks/usePersistentDraft";

export function Composer({
  onSubmitted,
}: {
  onSubmitted: (messageId: string) => void;
}) {
  const { text, setText, clearDraft } = usePersistentDraft();
  const queryClient = useQueryClient();

  const trim = text.trim();

  const mutation = useMutation({
    mutationFn: (input: SubmitMessageInput) => api.submitMessage(input),
    onMutate: async (input: SubmitMessageInput) => {
      const optimistic: TimelineGroup = {
        message: {
          id: input.submission_uuid,
          submission_uuid: input.submission_uuid,
          original_text: input.text,
          submitted_at: input.submitted_at,
          timezone: input.timezone,
          status: "pending",
        },
        events: [],
      };

      const cacheEntries = queryClient.getQueriesData<TimelinePage>({
        queryKey: ["timeline"],
      });

      for (const [key, data] of cacheEntries) {
        if (data) {
          queryClient.setQueryData<TimelinePage>(key, {
            ...data,
            groups: [optimistic, ...data.groups],
            total: data.total + 1,
          });
        }
      }
    },
    onError: (_err, _input) => {
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
    },
    onSuccess: (data, _input) => {
      const cacheEntries = queryClient.getQueriesData<TimelinePage>({
        queryKey: ["timeline"],
      });

      for (const [key, cached] of cacheEntries) {
        if (cached) {
          queryClient.setQueryData<TimelinePage>(key, {
            ...cached,
            groups: cached.groups.map((g) =>
              g.message.submission_uuid === data.message.submission_uuid
                ? { message: data.message, events: data.events }
                : g,
            ),
          });
        }
      }

      clearDraft();
      onSubmitted(data.message.id);
      queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
  });

  const handleSubmit = useCallback(() => {
    if (trim.length === 0 || mutation.isPending) return;
    const input = buildSubmissionInput(text);
    mutation.mutate(input);
  }, [text, trim, mutation]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && e.ctrlKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div className="composer">
      <textarea
        className="composer-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入需要整理的内容..."
        disabled={mutation.isPending}
        rows={4}
      />
      <div className="composer-footer">
        <span className="composer-hint">Ctrl+Enter 提交</span>
        <button
          className="composer-submit"
          onClick={handleSubmit}
          disabled={mutation.isPending || trim.length === 0}
        >
          {mutation.isPending ? "处理中..." : "提交"}
        </button>
      </div>
    </div>
  );
}
