odoo.define('ai_assistant.ReactChatFullPage', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');

    var AIChatFullPage = AbstractAction.extend({
        template: 'ai_assistant.ReactChatFullPage',

        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (window.AIChatWidget && window.AIChatWidget.mountFullPage) {
                    self.unmountFn = window.AIChatWidget.mountFullPage(
                        self.el.querySelector('.ai-react-fullpage-container')
                    );
                } else {
                    console.warn("AIChatWidget mount function not found.");
                }
            });
        },

        destroy: function () {
            if (this.unmountFn) {
                this.unmountFn();
            }
            this._super.apply(this, arguments);
        },
    });

    core.action_registry.add('ai_assistant.react_chat_fullpage', AIChatFullPage);

    return AIChatFullPage;
});
