odoo.define('website_livechat/static/src/models/thread/thread.js', function (require) {
'use strict';

const {
    registerClassPatchModel,
    registerFieldPatchModel,
} = require('mail/static/src/model/model_core.js');
const { many2one } = require('mail/static/src/model/model_field.js');

registerClassPatchModel('mail.thread', 'website_livechat/static/src/models/thread/thread.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('visitor' in data) {
            if (data.visitor) {
                data2.__mfield_visitor = [[
                    'insert',
                    this.env.models['website_livechat.visitor'].convertData(data.visitor)
                ]];
            } else {
                data2.__mfield_visitor = [['unlink']];
            }
        }
        return data2;
    },

});

registerFieldPatchModel('mail.thread', 'website_livechat/static/src/models/thread/thread.js', {
    /**
     * Visitor connected to the livechat.
     */
    __mfield_visitor: many2one('website_livechat.visitor', {
        inverse: '__mfield_threads',
    }),
});

});
