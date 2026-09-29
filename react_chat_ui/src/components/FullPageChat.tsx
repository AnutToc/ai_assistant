import {
  AssistantRuntimeProvider,
  useRemoteThreadListRuntime,
} from "@assistant-ui/react";
import { Thread } from "@/components/thread.aui";
import { ThreadList } from "@/components/thread-list.aui";
import { odooThreadListAdapter } from "../lib/odoo-thread-adapter";
import { useOdooChatRuntimeHook } from "../lib/odoo-chat-runtime";

export function FullPageChat() {
  const runtime = useRemoteThreadListRuntime({
    runtimeHook: useOdooChatRuntimeHook,
    adapter: odooThreadListAdapter,
  });

  return (
    <div className="ai-chat-root" style={{ height: "calc(100vh - 46px)", width: "100%" }}>
      <AssistantRuntimeProvider runtime={runtime}>
        <div className="flex h-full w-full">
          {/* Sidebar สำหรับเลือกแชทเก่า */}
          <div className="w-72 shrink-0 bg-slate-50 flex flex-col">
            <div className="p-3">
              <h2 className="text-sm font-semibold text-slate-700">Chat History</h2>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              <ThreadList />
            </div>
          </div>
          
          {/* ห้องแชทหลัก */}
          <div className="flex-1 flex flex-col min-w-0 bg-white">
            <Thread />
          </div>
        </div>
      </AssistantRuntimeProvider>
    </div>
  );
}
