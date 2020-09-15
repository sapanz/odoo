odoo.define('job.update_kanban', function (require) {
    'use strict';
    var KanbanRecord = require('web.KanbanRecord');

    KanbanRecord.include({
        /**
         * @override
         * @private
         */
        _openRecord: function () {
            if (this.modelName === 'hr.job' && this.$(".o_hr_job_boxes a").length) {
                this.$(".o_hr_job_boxes a").first().click();
            } else {
                this._super.apply(this, arguments);
            }
        }
    });
});

odoo.define('hr_recruitment.hr_recruitment_kanban', function (require) {
"use strict";

    const config = require('web.config');
    var FormView = require('web.FormView');
    var FormRenderer = require('web.FormRenderer');
    var viewRegistry = require('web.view_registry');

    var RecruitmentFormRenderer = FormRenderer.extend({
        on_attach_callback: function () {
            var self = this;
            self._super.apply(this, arguments);
            if (!config.device.isMobile) {
                return;
            }
            self.$el.closest('.modal').addClass('o_modal_full');
        },
    });
    var RecruitmentFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Renderer: RecruitmentFormRenderer
        }),
    });

    viewRegistry.add('hr_recruitment_kanban', RecruitmentFormView);
});
