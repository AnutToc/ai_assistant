import {
  AssistantRuntimeProvider,
  useRemoteThreadListRuntime,
} from "@assistant-ui/react";
import { Thread } from "@/components/thread.aui";
import { odooThreadListAdapter } from "../lib/odoo-thread-adapter";
import { useOdooChatRuntimeHook } from "../lib/odoo-chat-runtime";
import { useState } from "react";
import { MessageSquare, X } from "lucide-react";

export function FloatingChat() {
  const [isOpen, setIsOpen] = useState(false);

  const runtime = useRemoteThreadListRuntime({
    runtimeHook: useOdooChatRuntimeHook,
    adapter: odooThreadListAdapter,
  });

  return (
    <>
      {/* ปุ่มลอย — ตัวนี้อยู่นอก ai-chat-root เพื่อไม่ให้ถูก scope */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: "fixed",
          bottom: "24px",
          right: "24px",
          zIndex: 99999,
          width: "56px",
          height: "56px",
          borderRadius: "50%",
          background: "#3b82f6",
          color: "white",
          border: "none",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 4px 14px rgba(59, 130, 246, 0.4)",
          transition: "transform 0.2s",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.1)")}
        onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
      >
        {isOpen ? <X size={24} /> : <MessageSquare size={24} />}
      </button>

      {/* หน้าต่างแชท */}
      {isOpen && (
        <div
          className="ai-chat-root"
          style={{
            position: "fixed",
            bottom: "96px",
            right: "24px",
            zIndex: 99999,
            width: "420px",
            height: "620px",
            borderRadius: "16px",
            overflow: "hidden",
            boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
            border: "1px solid #e2e8f0",
          }}
        >
          <AssistantRuntimeProvider runtime={runtime}>
            <div className="flex flex-col h-full w-full">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 bg-primary text-primary-foreground">
                <span className="font-semibold text-sm">🤖 AI Assistant</span>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1 rounded-md hover:bg-white/20 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>
              {/* Chat Area */}
              <div className="flex-1 min-h-0">
                <Thread />
              </div>
            </div>
          </AssistantRuntimeProvider>
        </div>
      )}
    </>
  );
}
