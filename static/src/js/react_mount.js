odoo.define('ai_assistant.ReactChatFloat', function (require) {
    "use strict";

    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');

    var AIChatReactFloat = Widget.extend({
        template: 'ai_assistant.ReactChatFloat',

        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                // Check config
                return self._rpc({
                    route: '/api/ai/config',
                }).then(function (config) {
                    if (config.chat_ui_mode === 'discuss') {
                        return; // Hidden
                    }
                    if (window.AIChatWidget && window.AIChatWidget.mountFloating) {
                        self.unmountFn = window.AIChatWidget.mountFloating(self.el.querySelector('.ai-react-float-container'));
                    }
                }).catch(function (e) {
                    console.warn("Could not fetch AI chat config", e);
                });
            });
        },

        destroy: function () {
            if (this.unmountFn) {
                this.unmountFn();
            }
            this._super.apply(this, arguments);
        },
    });

    SystrayMenu.Items.push(AIChatReactFloat);

    return AIChatReactFloat;
});
