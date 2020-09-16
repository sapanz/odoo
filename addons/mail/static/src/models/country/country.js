odoo.define('mail/static/src/models/country/country.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { clear } = require('mail/static/src/model/model_field_command.js');
const { attr } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class Country extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.__mfield_id}`;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeFlagUrl() {
            if (!this.__mfield_code(this)) {
                return clear();
            }
            return `/base/static/img/country_flags/${this.__mfield_code(this)}.png`;
        }

    }

    Country.fields = {
        __mfield_code: attr(),
        __mfield_flagUrl: attr({
            compute: '_computeFlagUrl',
            dependencies: [
                '__mfield_code',
            ],
        }),
        __mfield_id: attr(),
        __mfield_name: attr(),
    };

    Country.modelName = 'mail.country';

    return Country;
}

registerNewModel('mail.country', factory);

});
