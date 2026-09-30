odoo.define('ai_assistant.SystrayItem', function (require) {
    "use strict";

    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var core = require('web.core');

    var AiSystrayItem = Widget.extend({
        template: 'ai_assistant.SystrayItem',
        events: {
            'click': '_onClickAiIcon',
        },

        willStart: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                return self._rpc({
                    route: '/api/ai/config',
                }).then(function (config) {
                    self.isVisible = config.chat_ui_mode !== 'react';
                }).catch(function () {
                    self.isVisible = true;
                });
            });
        },

        _onClickAiIcon: function () {
            this.do_action({
                type: 'ir.actions.client',
                tag: 'mail.action_discuss',
                name: 'AI Chat',
            });
        },
    });

    SystrayMenu.Items.push(AiSystrayItem);

    return AiSystrayItem;
});
