odoo.define('website_slides.Activity', function (require) {
    "use strict";

    const components = {
        Activity: require('mail/static/src/components/activity/activity.js'),
    };

    const { patch } = require('web.utils');

    patch(components.Activity, 'website_slides/static/src/components/activity/activity.js', {

        async willStart() {
            await this._super(...arguments);
            if (this.activity && this.activity.creator && !this.activity.creator.partner) {
                await this.activity.creator.fetchPartner();
            }
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        async _onGrantAccess(ev) {
            await this.env.services.rpc({
                model: 'slide.channel',
                method: 'action_grant_access',
                args: [this.activity.thread.id, parseInt(ev.currentTarget.dataset.partnerId)],
            });
            this.trigger('reload');
        },
        /**
         * @private
         */
        async _onRefuseAccess(ev) {
            await this.env.services.rpc({
                model: 'slide.channel',
                method: 'action_refuse_access',
                args: [this.activity.thread.id, parseInt(ev.currentTarget.dataset.partnerId)],
            });
            this.trigger('reload');
        },
    });

});