odoo.define('website_livechat/static/src/models/partner/partner.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class Visitor extends dependencies['mail.model'] {
        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static convertData(data) {
            const data2 = {};
            if ('country_id' in data) {
                if (data.country_id) {
                    data2.__mfield_country = [['insert', {
                        __mfield_id: data.country_id,
                        __mfield_code: data.country_code,
                    }]];
                } else {
                    data2.__mfield_country = [['unlink']];
                }
            }
            if ('history' in data) {
                data2.__mfield_history = data.history;
            }
            if ('is_connected' in data) {
                data2.__mfield_is_connected = data.is_connected;
            }
            if ('lang' in data) {
                data2.__mfield_lang = data.lang;
            }
            if ('name' in data) {
                data2.__mfield_name = data.name;
            }
            if ('partner_id' in data) {
                if (data.partner_id) {
                    data2.__mfield_partner = [['insert', {
                        __mfield_id: data.partner_id,
                    }]];
                } else {
                    data2.__mfield_partner = [['unlink']];
                }
            }
            if ('website' in data) {
                data2.__mfield_website = data.website;
            }
            return data2;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            if (!this.__mfield_partner(this)) {
                return '/mail/static/src/img/smiley/avatar.jpg';
            }
            return this.__mfield_partner(this).__mfield_avatarUrl(this);
        }

        /**
         * @private
         * @returns {mail.country}
         */
        _computeCountry() {
            if (this.__mfield_partner(this) && this.__mfield_partner(this).__mfield_country(this)) {
                return [['link', this.__mfield_partner(this).__mfield_country(this)]];
            }
            if (this.__mfield_country(this)) {
                return [['link', this.__mfield_country(this)]];
            }
            return [['unlink']];
        }

        /**
         * @private
         * @returns {string}
         */
        _computeNameOrDisplayName() {
            if (this.__mfield_partner(this)) {
                return this.__mfield_partner(this).__mfield_nameOrDisplayName(this);
            }
            return this.__mfield_name(this);
        }
    }

    Visitor.fields = {
        /**
         * Url to the avatar of the visitor.
         */
        __mfield_avatarUrl: attr({
            compute: '_computeAvatarUrl',
            dependencies: [
                '__mfield_partner',
                '__mfield_partnerAvatarUrl',
            ],
        }),
        /**
         * Country of the visitor.
         */
        __mfield_country: many2one('mail.country', {
            compute: '_computeCountry',
            dependencies: [
                '__mfield_country',
                '__mfield_partnerCountry',
            ],
        }),
        /**
         * Browsing history of the visitor as a string.
         */
        __mfield_history: attr(),
        /**
         * Determine whether the visitor is connected or not.
         */
        __mfield_is_connected: attr(),
        /**
         * Name of the language of the visitor. (Ex: "English")
         */
        __mfield_lang: attr(),
        /**
         * Name of the visitor.
         */
        __mfield_name: attr(),
        __mfield_nameOrDisplayName: attr({
            compute: '_computeNameOrDisplayName',
            dependencies: [
                '__mfield_name',
                '__mfield_partnerNameOrDisplayName',
            ],
        }),
        /**
         * Partner linked to this visitor, if any.
         */
        __mfield_partner: many2one('mail.partner'),
        __mfield_partnerAvatarUrl: attr({
            related: '__mfield_partner.__mfield_avatarUrl',
        }),
        __mfield_partnerCountry: many2one('mail.country',{
            related: '__mfield_partner.__mfield_country',
        }),
        __mfield_partnerNameOrDisplayName: attr({
            related: '__mfield_partner.__mfield_nameOrDisplayName',
        }),
        /**
         * Threads with this visitor as member
         */
        __mfield_threads: one2many('mail.thread', {
            inverse: '__mfield_visitor',
        }),
        /**
         * Name of the website on which the visitor is connected. (Ex: "Website 1")
         */
        __mfield_website: attr(),
    };

    Visitor.modelName = 'website_livechat.visitor';

    return Visitor;
}

registerNewModel('website_livechat.visitor', factory);

});
