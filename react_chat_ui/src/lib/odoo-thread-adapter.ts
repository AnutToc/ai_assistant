import { type RemoteThreadListAdapter } from "@assistant-ui/react";

export const odooThreadListAdapter: RemoteThreadListAdapter = {
  async list() {
    try {
      const res = await fetch("/api/ai/threads");
      if (!res.ok) return { threads: [] };
      const threads = await res.json();
      return {
        threads: threads.map((t: any) => ({
          remoteId: String(t.id),
          title: t.title || "แชทใหม่",
          status: "regular" as const,
        })),
      };
    } catch (e) {
      console.error("Failed to list threads", e);
      return { threads: [] };
    }
  },

  async initialize(threadId: string) {
    try {
      const res = await fetch("/api/ai/threads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "แชทใหม่" }),
      });
      if (!res.ok) {
        throw new Error(`Failed to create thread: ${res.statusText}`);
      }
      const thread = await res.json();
      return { remoteId: String(thread.id) };
    } catch (e) {
      console.error("Failed to initialize thread", e);
      return { remoteId: threadId };
    }
  },

  async rename(remoteId: string, title: string) {
    try {
      await fetch(`/api/ai/threads/${remoteId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
    } catch (e) {
      console.error("Failed to rename thread", e);
    }
  },

  async archive(remoteId: string) {
    try {
      await fetch(`/api/ai/threads/${remoteId}`, { method: "DELETE" });
    } catch (e) {
      console.error("Failed to archive thread", e);
    }
  },

  async delete(remoteId: string) {
    try {
      await fetch(`/api/ai/threads/${remoteId}`, { method: "DELETE" });
    } catch (e) {
      console.error("Failed to delete thread", e);
    }
  },

  async fetch(threadId: string) {
    try {
      const res = await fetch("/api/ai/threads");
      if (res.ok) {
        const threads = await res.json();
        const found = threads.find((t: any) => String(t.id) === String(threadId));
        if (found) {
          return {
            remoteId: String(found.id),
            title: found.title || "แชทใหม่",
            status: "regular" as const,
          };
        }
      }
    } catch (e) {
      console.error("Failed to fetch thread metadata", e);
    }
    return {
      remoteId: threadId,
      title: "แชทใหม่",
      status: "regular" as const,
    };
  },
};
