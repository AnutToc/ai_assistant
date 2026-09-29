import { type ChatModelAdapter } from "@assistant-ui/react";

export const odooModelAdapter: ChatModelAdapter = {
  async *run(options) {
    const { messages, abortSignal } = options;
    const threadId =
      (options as any).unstable_threadId || (options as any).config?.threadId;

    // 1. Prepare message payload for Odoo backend
    const payloadMessages = messages.map((m) => {
      let textContent = "";
      if (Array.isArray(m.content)) {
        textContent = m.content
          .map((c) => {
            if (c.type === "text") return c.text;
            return "";
          })
          .join("");
      } else {
        textContent = String(m.content || "");
      }
      return { role: m.role, content: textContent };
    });

    let fullRawText = "";
    let serverThought = "";

    function getYieldContent() {
      let combinedThought = serverThought;
      let text = fullRawText;

      // Extract <thought>, <think>, <reasoning> XML tags from text if model outputs them directly
      const tags = ["thought", "think", "reasoning"];
      for (const tag of tags) {
        const regex = new RegExp(`<${tag}>([\\s\\S]*?)(?:<\\/${tag}>|$)`, "i");
        const match = text.match(regex);
        if (match) {
          const extracted = match[1].trim();
          if (extracted) {
            combinedThought = combinedThought
              ? `${combinedThought}\n\n${extracted}`
              : extracted;
          }
          text = text.replace(regex, "").trim();
        }
      }

      const parts: any[] = [];
      if (combinedThought) {
        parts.push({ type: "reasoning", text: combinedThought });
      }
      if (text) {
        parts.push({ type: "text", text: text });
      } else if (!combinedThought) {
        parts.push({ type: "text", text: "" });
      }
      return parts;
    }

    try {
      const response = await fetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          thread_id: threadId,
          messages: payloadMessages,
        }),
        signal: abortSignal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        yield {
          content: [
            {
              type: "text",
              text: `⚠️ เกิดข้อผิดพลาดจากเซิร์ฟเวอร์ (${response.status}): ${errorText}`,
            },
          ],
        };
        return;
      }

      if (!response.body) {
        throw new Error("No response body received");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataRaw = line.slice(6).trim();
            if (!dataRaw) continue;

            try {
              const data = JSON.parse(dataRaw);
              if (data._event === "text-delta" && data.text) {
                fullRawText += data.text;
                yield { content: getYieldContent() };
              } else if (data._event === "thinking" && data.text) {
                serverThought += data.text;
                yield { content: getYieldContent() };
              } else if (data._event === "tool-call") {
                fullRawText += `\n> 🔧 **กำลังใช้งาน:** \`${data.name}\`...\n\n`;
                yield { content: getYieldContent() };
              } else if (data._event === "tool-result") {
                fullRawText += `> ✅ **ผลลัพธ์:** ${data.summary || "สำเร็จ"} (${data.duration_ms || 0}ms)\n\n`;
                yield { content: getYieldContent() };
              } else if (data._event === "error") {
                fullRawText += `\n\n❌ **Error:** ${data.error}\n`;
                yield { content: getYieldContent() };
              }
            } catch (e) {
              console.error("Failed to parse SSE line", e);
            }
          }
        }
      }

      yield { content: getYieldContent() };
    } catch (err: any) {
      if (err.name === "AbortError") return;
      console.error("Chat adapter error:", err);
      const isTimeout =
        err.message?.toLowerCase().includes("timeout") ||
        err.message?.toLowerCase().includes("failed to fetch") ||
        err.message?.toLowerCase().includes("network error");
      const errNote = isTimeout
        ? "การเชื่อมต่อขัดข้อง หรือ AI ใช้เวลาประมวลผลนานเกินกำหนด (Network/Timeout Error)"
        : err.message;

      const currentParts = getYieldContent();
      const errorMsg = `\n\n⚠️ **${errNote}**`;

      if (currentParts.length > 0) {
        const textPart = currentParts.find((p: any) => p.type === "text");
        if (textPart) {
          textPart.text = (textPart.text || "") + errorMsg;
        } else {
          currentParts.push({ type: "text", text: errorMsg });
        }
        yield { content: currentParts };
      } else {
        yield {
          content: [
            {
              type: "text",
              text: `❌ ไม่สามารถเชื่อมต่อกับ AI Assistant ได้: ${errNote}`,
            },
          ],
        };
      }
    }
  },
};
