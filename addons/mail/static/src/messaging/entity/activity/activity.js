odoo.define('mail.messaging.entity.Activity', function (require) {
'use strict';

const {
    fields: {
        attr,
        many2many,
        many2one,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

function ActivityFactory({ Entity }) {

    class Activity extends Entity {


        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Delete the record from database and delete the entity.
         */
        async deleteRecord() {
            await this.env.rpc({
                model: 'mail.activity',
                method: 'unlink',
                args: [[this.id]],
            });
            this.delete();
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @return {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('activity_category' in data) {
                data2.category = data.activity_category;
            }
            if ('can_write' in data) {
                data2.canWrite = data.can_write;
            }
            if ('create_data' in data) {
                data2.dateCreate = data.create_date;
            }
            if ('date_deadline' in data) {
                data2.dateDeadline = data.date_deadline;
            }
            if ('force_next' in data) {
                data2.force_next = data.force_next;
            }
            if ('icon' in data) {
                data2.icon = data.icon;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('note' in data) {
                data2.note = data.note;
            }
            if ('res_id' in data) {
                data2.res_id = data.res_id;
            }
            if ('res_model' in data) {
                data2.res_model = data.res_model;
            }
            if ('state' in data) {
                data2.state = data.state;
            }
            if ('summary' in data) {
                data2.summary = data.summary;
            }

            // relation
            if ('activity_type_id' in data) {
                if (!data.activity_type_id) {
                    data2.type = [['unlink-all']];
                } else {
                    data2.type = [
                        ['insert', {
                            displayName: data.activity_type_id[1],
                            id: data.activity_type_id[0],
                        }]
                    ];
                }
            }
            if ('create_uid' in data) {
                if (!data.create_uid) {
                    data2.creator = [['unlink-all']];
                } else {
                    data2.creator = [
                        ['insert', {
                            _displayName: data.create_uid[1],
                            id: data.create_uid[0],
                        }]
                    ];
                }
            }
            if ('mail_template_ids' in data) {
                data2.mailTemplates = [['insert', data.mail_template_ids]];
            }
            if ('user_id' in data) {
                if (!data.user_id) {
                    data2.assignee = [['unlink-all']];
                } else {
                    data2.assignee = [
                        ['insert', {
                            _displayName: data.user_id[1],
                            id: data.user_id[0],
                        }]
                    ];
                }
            }

            return data2;
        }

        async fetchAndUpdate() {
            const data = await this.env.rpc({
                model: 'mail.activity',
                method: 'activity_format',
                args: [this.id],
            });
            this.update(this.constructor.convertData(data));
            if (this.chatter) {
                this.chatter.refresh();
            }
        }

        /**
         * @param {Object} param0
         * @param {mail.messaging.entity.Attachment[]} [param0.attachments=[]]
         * @param {string|boolean} [param0.feedback=false]
         */
        async markAsDone({ attachments = [], feedback = false }) {
            const attachmentIds = attachments.map(attachment => attachment.id);
            await this.env.rpc({
                model: 'mail.activity',
                method: 'action_feedback',
                args: [[this.id]],
                kwargs: {
                    attachment_ids: attachmentIds,
                    feedback,
                },
                context: this.chatter ? this.chatter.context : {},
            });
            if (this.chatter) {
                this.chatter.refresh();
            }
            this.delete();
        }

        /**
         * @param {Object} param0
         * @param {string} param0.feedback
         * @returns {Object}
         */
        async markAsDoneAndScheduleNext({ feedback }) {
            const action = await this.env.rpc({
                model: 'mail.activity',
                method: 'action_feedback_schedule_next',
                args: [[this.id]],
                kwargs: { feedback },
            });
            const chatter = this.chatter;
            if (chatter) {
                this.chatter.refresh();
            }
            this.delete();
            this.env.do_action(action, {
                on_close: () => {
                    if (chatter) {
                        chatter.refreshActivities();
                    }
                },
            });
        }

    }

    Activity.entityName = 'Activity';

    Activity.fields = {
        assignee: many2one('User'),
        attachments: many2many('Attachment', {
            inverse: 'activities',
        }),
        canWrite: attr({
            default: false,
        }),
        category: attr(),
        chatter: many2one('Chatter', {
            inverse: 'activities',
        }),
        creator: many2one('User'),
        dateCreate: attr(),
        dateDeadline: attr(),
        force_next: attr({
            default: false,
        }),
        icon: attr(),
        id: attr(),
        mailTemplates: many2many('MailTemplate', {
            inverse: 'activities',
        }),
        note: attr(),
        res_id: attr(),
        res_model: attr(),
        state: attr(),
        summary: attr(),
        type: many2one('ActivityType', {
            inverse: 'activities',
        }),
    };

    return Activity;
}

registerNewEntity('Activity', ActivityFactory);

});
