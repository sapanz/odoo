odoo.define('mail/static/src/components/activity_box/activity_box.js', function (require) {
'use strict';

const components = {
    Activity: require('mail/static/src/components/activity/activity.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class ActivityBox extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Chatter}
     */
    get chatter() {
        return this.env.models['mail.chatter'].get(this.props.chatterLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickTitle() {
        this.chatter.toggleActivityBoxVisibility();
    }

}

Object.assign(ActivityBox, {
    components,
    props: {
        chatterLocalId: String,
    },
    template: 'mail.ActivityBox',
});

return ActivityBox;

});
