/** @odoo-module **/
import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class AIChatFullPage extends Component {
    static template = "ai_assistant.ReactChatFullPage";
    
    setup() {
        this.rootRef = useRef("react_fullpage_root");
        this.unmountFn = null;
        
        onMounted(() => {
            if (window.AIChatWidget && window.AIChatWidget.mountFullPage) {
                this.unmountFn = window.AIChatWidget.mountFullPage(this.rootRef.el);
            } else {
                console.warn("AIChatWidget mount function not found.");
            }
        });
        
        onWillUnmount(() => {
            if (this.unmountFn) this.unmountFn();
        });
    }
}

registry.category("actions").add("ai_assistant.react_chat_fullpage", AIChatFullPage);
