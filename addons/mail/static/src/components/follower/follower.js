odoo.define('mail/static/src/components/follower/follower.js', function (require) {
'use strict';

const components = {
    FollowerSubtypeList: require('mail/static/src/components/follower_subtype_list/follower_subtype_list.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class Follower extends Component {

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
     * @returns {mail.follower}
     */
    get follower() {
        return this.env.models['mail.follower'].get(this.props.followerLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDetails(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.follower.openProfile();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickEdit(ev) {
        ev.preventDefault();
        this.follower.showSubtypes();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRemove(ev) {
        this.follower.remove();
    }

}

Object.assign(Follower, {
    components,
    props: {
        followerLocalId: String,
    },
    template: 'mail.Follower',
});

return Follower;

});
