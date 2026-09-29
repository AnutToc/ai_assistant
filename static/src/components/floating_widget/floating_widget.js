/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AiSystrayItem extends Component {
    setup() {
        this.action = useService("action");
        this.state = useState({ isVisible: true });
        
        onWillStart(async () => {
            try {
                const res = await fetch("/api/ai/config");
                const config = await res.json();
                if (config.chat_ui_mode === 'react') {
                    this.state.isVisible = false;
                }
            } catch (e) {
                // Keep default visible
            }
        });
    }

    onClickAiIcon() {
        // MVP action: Open the Discuss app when the magic wand is clicked.
        // For a true floating widget, this would instantiate a ChatWindow component.
        this.action.doAction({
            type: 'ir.actions.client',
            tag: 'mail.action_discuss',
            name: 'AI Chat',
        });
    }
}

AiSystrayItem.template = "ai_assistant.SystrayItem";

// Register the component into Odoo's Systray
const systrayRegistry = registry.category("systray");
systrayRegistry.add("ai_assistant.AiSystrayItem", { Component: AiSystrayItem }, { sequence: 15 });
