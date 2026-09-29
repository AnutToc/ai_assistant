/** @odoo-module **/
import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class AIChatReactFloat extends Component {
    static template = "ai_assistant.ReactChatFloat";
    
    setup() {
        this.rootRef = useRef("react_float_root");
        this.unmountFn = null;
        
        onMounted(async () => {
            try {
                const res = await fetch("/api/ai/config");
                const config = await res.json();
                if (config.chat_ui_mode === 'discuss') {
                    return; // Hidden when mode is discuss-only
                }
            } catch (e) {
                console.warn("Could not fetch AI chat config, falling back to default", e);
            }

            if (window.AIChatWidget && window.AIChatWidget.mountFloating) {
                this.unmountFn = window.AIChatWidget.mountFloating(this.rootRef.el);
            } else {
                console.warn("AIChatWidget mount function not found. Ensure react_chat_bundle.js is loaded.");
            }
        });
        
        onWillUnmount(() => {
            if (this.unmountFn) this.unmountFn();
        });
    }
}

// Register as a Systray item
registry.category("systray").add("ai_assistant.ReactChatFloat", {
    Component: AIChatReactFloat,
}, { sequence: 2 });
