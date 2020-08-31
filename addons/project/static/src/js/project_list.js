odoo.define('project.ProjectListView', function (require) {
    "use strict";

    const Dialog = require('web.Dialog');
    const ListView = require('web.ListView');
    const ListController = require('web.ListController');
    const core = require('web.core');
    const view_registry = require('web.view_registry');

    const _t = core._t;

    const ProjectListController = ListController.extend({
        _getActionMenuItems: function (state) {
            if(!this.archiveEnabled || this.selectedRecords.length != 1) {
                return this._super.apply(this, arguments);
            }

            const record = this.getSelectedRecords()[0];
            this.archiveEnabled = !record.data.recurrence_id;
            let actions = this._super.apply(this, arguments);
            this.archiveEnabled = true;

            if(actions && record.data.recurrence_id) {
                actions.items.other.unshift({
                    description: _t('Archive'),
                    callback: () => this._stopRecurrence(record.res_id),
                }, {
                    description: _t('Unarchive'),
                    callback: () => this._toggleArchiveState(false)
                });
            }
            return actions;
        },

        _onDeleteSelectedRecords: async function () {
            const recurringRecords = this.getSelectedRecords().filter(rec => rec.data.recurrence_id);
            if(recurringRecords.length == 1) {
                const record = recurringRecords[0];
                if(record.data.recurrence_id) {
                    return this._stopRecurrence(record);
                }
            }

            return this._super.apply(this, arguments);
        },

        _stopRecurrence(record) {
            new Dialog(this, {
                buttons: [
                    {
                        classes: 'btn-primary',
                        click: () => {
                            this._rpc({
                                model: 'project.task',
                                method: 'action_stop_recurrence',
                                args: [record.res_id],
                            }).then(() => {
                                this.reload();
                            });
                        },
                        close: true,
                        text: _t('Stop Recurrence'),
                    },
                    {
                        click: () => {
                            this._rpc({
                                model: 'project.task',
                                method: 'action_continue_recurrence',
                                args: [record.res_id],
                            }).then(() => {
                                this.reload();
                            });
                        },
                        close: true,
                        text: _t('Continue Recurrence'),
                    },
                    {
                        close: true,
                        text: _t('Discard'),
                    }
                ],
                size: 'medium',
                title: _t('Confirmation'),
                $content: $('<main/>', {
                    role: 'alert',
                    text: _t('It seems that this task is part of a recurrence.'),
                }),
            }).open();
        }
    });
    
    const ProjectListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: ProjectListController,
        }),
    });

    view_registry.add('project_list', ProjectListView);

    return ProjectListView;
});
