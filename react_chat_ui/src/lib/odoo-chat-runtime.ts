import {
  useLocalRuntime,
  useAui,
  ExportedMessageRepository,
  type ThreadHistoryAdapter,
} from "@assistant-ui/react";
import { useMemo } from "react";
import { odooModelAdapter } from "./odoo-adapter";

export function useOdooChatRuntimeHook() {
  const aui = useAui();

  const history: ThreadHistoryAdapter = useMemo(
    () => ({
      async load() {
        try {
          const threadListItem = aui.threadListItem;
          let remoteId = threadListItem?.source
            ? threadListItem.getState()?.remoteId
            : undefined;

          if (!remoteId) {
            const threadsState = aui.threads?.getState();
            const currentItem = threadsState?.threadItems?.find(
              (t: any) =>
                t.id === threadsState.mainThreadId ||
                t.remoteId === threadsState.mainThreadId
            );
            remoteId = currentItem?.remoteId;
          }

          if (!remoteId) {
            return { messages: [] };
          }

          const res = await fetch(`/api/ai/threads/${remoteId}/messages`);
          if (!res.ok) return { messages: [] };
          const rawMessages = await res.json();

          const converted = rawMessages.map((m: any) => {
            let text = m.content || "";
            let reasoning = "";

            if (m.thinking_steps && Array.isArray(m.thinking_steps)) {
              const stepTexts = m.thinking_steps
                .map((s: any) => s.text || (s.name ? `> 🔧 Tool: ${s.name}` : ""))
                .filter(Boolean)
                .join("");
              if (stepTexts) reasoning = stepTexts;
            }

            const tags = ["thought", "think", "reasoning"];
            for (const tag of tags) {
              const regex = new RegExp(`<${tag}>([\\s\\S]*?)(?:<\\/${tag}>|$)`, "i");
              const match = text.match(regex);
              if (match) {
                const extracted = match[1].trim();
                if (extracted) {
                  reasoning = reasoning ? `${reasoning}\n\n${extracted}` : extracted;
                }
                text = text.replace(regex, "").trim();
              }
            }

            const parts: any[] = [];
            if (reasoning) {
              parts.push({ type: "reasoning", text: reasoning });
            }
            if (text) {
              parts.push({ type: "text", text: text });
            } else if (parts.length === 0) {
              parts.push({ type: "text", text: "" });
            }

            return {
              id: String(m.id),
              role: m.role as "user" | "assistant",
              content: parts,
            };
          });

          return ExportedMessageRepository.fromArray(converted);
        } catch (e) {
          console.error("Error loading thread messages:", e);
          return { messages: [] };
        }
      },

      async append() {
        // Backend persists automatically on streaming
      },
    }),
    [aui]
  );

  return useLocalRuntime(odooModelAdapter, {
    adapters: { history },
  });
}
