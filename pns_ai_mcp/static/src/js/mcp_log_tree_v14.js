/**
 * Clear History and Tools buttons on the ai.log list (Odoo 14).
 *
 * SPDX-License-Identifier: Apache-2.0
 * Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
 */
odoo.define('pns_ai_mcp.mcp_log_tree', function (require) {
"use strict";

    var ListController = require('web.ListController');
    var ListRenderer = require('web.ListRenderer');
    require('web.EditableListRenderer');
    var ActionManager = require('web.ActionManager');
    var core = require('web.core');

    // O14 takes an absolute `width` from the arch only as a minimum, then
    // spreads the spare room over every column. O19 keeps it fixed.
    ListRenderer.include({
        _freezeColumnWidths: function () {
            this._super.apply(this, arguments);
            var cls = (this.arch && this.arch.attrs && this.arch.attrs.class) || '';
            if (cls.split(/\s+/).indexOf('o_mcp_log_tree') < 0) {
                return;
            }
            var self = this;
            this.columns.forEach(function (column) {
                var th = self._getColumnHeader(column);
                if (!th) {
                    return;
                }
                var width = column.attrs.width;
                if (width && /^\d+px$/.test(width)) {
                    var cs = window.getComputedStyle(th);
                    var px = (parseFloat(width) + parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight)) + 'px';
                    ['width', 'min-width', 'max-width'].forEach(function (prop) {
                        th.style.setProperty(prop, px, 'important');
                    });
                } else {
                    th.style.removeProperty('width');
                    th.style.removeProperty('max-width');
                }
            });
        },
    });

    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            
            // Only add the button for the ai.log model
            if (this.modelName === 'ai.log') {
                // Stricter checks to avoid errors when duplicating tabs
                if (!this.$buttons || typeof this.$buttons !== 'object' || !this.$buttons.length) {
                    return;
                }
                
                // Check that $buttons has jQuery methods
                if (typeof this.$buttons.prepend !== 'function') {
                    return;
                }
                
                var self = this;
                
                // Avoid duplicates by removing the previous button
                this.$buttons.find('.o_mcp_log_delete_button').remove();
                
                var $deleteButton = $('<button>', {
                    class: 'btn btn-primary o_mcp_log_delete_button',
                    type: 'button',
                    text: 'Clear History',
                    title: 'Deletes the oldest logs, keeping the most recent ones. Can delete all or keep the N newest.',
                    click: function() {
                        self._onDeleteMenuClick();
                    }
                });
                
                try {
                    this.$buttons.prepend($deleteButton);
                } catch (e) {
                    console.warn('Error adding the Clear History button:', e);
                }

                // Operations button
                this.$buttons.find('.o_mcp_log_ops_button').remove();
                var $opsBtn = $('<button>', {
                    type: 'button',
                    class: 'btn btn-secondary o_mcp_btn_sm o_mcp_log_ops_button',
                    html: "<i class='fa fa-cog'></i> Tools",
                    title: "History tools",
                    style: 'margin-left: 4px;',
                    click: function () {
                        self.do_action('pns_ai_mcp.action_log_tools_wizard');
                    },
                });
                this.$buttons.append($opsBtn);
            }
        },

        on_attach_callback: function () {
            this._super.apply(this, arguments);
            if (this.modelName === 'ai.log') {
                this._mcpLogLegendReady();
            }
        },

        /**
         * Promise of the legend bar in the control panel (resolves true once
         * it is there). The usage chip lives inside that bar.
         */
        _mcpLogLegendReady: function () {
            var self = this;
            if (!this._mcpLogLegend) {
                this._mcpLogLegend = this._insertMcpLogLegend().then(function (done) {
                    if (!done) {
                        self._mcpLogLegend = null;
                    }
                    return done;
                });
            }
            return this._mcpLogLegend;
        },

        _insertMcpLogLegend: function () {
            if (this.modelName !== 'ai.log') {
                return Promise.resolve(false);
            }
            // The legend goes into the CONTROL PANEL (fixed area, no scroll) and not
            // before the table: putting it inside the scrolling area created a
            // second vertical scrollbar. This way there is a single scroll (the list's).
            var $cp = $();
            if (this.$buttons && this.$buttons.length) {
                $cp = this.$buttons.closest('.o_control_panel');
            }
            if (!$cp.length) {
                $cp = this.$el.closest('.o_action_manager, .o_action').find('.o_control_panel').first();
            }
            if (!$cp.length) {
                return Promise.resolve(false);
            }
            // Idempotent: if the bar already exists in this control panel, do not duplicate.
            if ($cp.find('.o_mcp_log_legend_bar').length) {
                return Promise.resolve(true);
            }
            // SINGLE SOURCE: the server builds the HTML (ai.log.render_flow_legend),
            // the same method the form uses. Grid and form never diverge.
            return Promise.resolve(this._rpc({
                model: 'ai.log',
                method: 'render_flow_legend',
                args: ['grid'],
            })).then(function (html) {
                if (!html) {
                    return false;
                }
                if (!$cp.find('.o_mcp_log_legend_bar').length) {
                    $cp.append(html);
                }
                return true;
            }, function () {
                return false;
            });
        },
        
        _onDeleteMenuClick: function() {
            this.do_action('pns_ai_mcp.action_ai_log_delete_menu_window');
        },
    });

    // Intercept display_notification with next, to reload the logs view
    ActionManager.include({
        _executeClientAction: function (action, options) {
            var self = this;
            
            var result = this._super.apply(this, arguments);
            
            // If it is display_notification with a reloading next, close the wizard and reload the logs view
            if (action && action.tag === 'display_notification' && action.params && action.params.next) {
                if (action.params.next.tag === 'reload') {
                    // Close the active wizard and reload the logs view
                    if (result && typeof result.then === 'function') {
                        result.then(function() {
                            // Close active dialogs (wizards)
                            if (self._dialogs && Array.isArray(self._dialogs)) {
                                var i = self._dialogs.length - 1;
                                while (i >= 0) {
                                    var dialog = self._dialogs[i];
                                    if (dialog && typeof dialog.close === 'function') {
                                        try {
                                            dialog.close();
                                        } catch (e) {
                                            console.warn('Error closing dialog:', e);
                                        }
                                        break;
                                    }
                                    i--;
                                }
                            }

                            // Find and reload the logs controllers
                            if (self._controllers && Array.isArray(self._controllers)) {
                                for (var j = 0; j < self._controllers.length; j++) {
                                    var controller = self._controllers[j];
                                    if (controller && controller.modelName === 'ai.log' && typeof controller.reload === 'function') {
                                        try {
                                            controller.reload();
                                        } catch (e) {
                                            console.warn('Error reloading controller:', e);
                                        }
                                    }
                                }
                            }

                            // Also reload the current controller if it is a logs one
                            try {
                                var currentController = self.getCurrentController && self.getCurrentController();
                                if (currentController && currentController.modelName === 'ai.log' && typeof currentController.reload === 'function') {
                                    currentController.reload();
                                }
                            } catch (e) {
                                console.warn('Error getting/reloading the current controller:', e);
                            }
                        });
                    } else {
                        try {
                            var currentController = self.getCurrentController && self.getCurrentController();
                            if (currentController && currentController.modelName === 'ai.log' && typeof currentController.reload === 'function') {
                                currentController.reload();
                            }
                        } catch (e) {
                            console.warn('Error getting/reloading the current controller:', e);
                        }
                    }
                }
            }
            
            return result;
        },
    });


    return {};
});

