odoo.define('mail.messaging.entity.Locale', function (require) {
'use strict';

const {
    fields: {
        attr,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

function LocaleFactory({ Entity }) {

    class Locale extends Entity {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeTextDirection() {
            return this.env._t.database.parameters.direction;
        }

    }

    Locale.entityName = 'Locale';

    Locale.fields = {
        textDirection: attr({
            compute: '_computeTextDirection',
        }),
    };

    return Locale;
}

registerNewEntity('Locale', LocaleFactory);

});
