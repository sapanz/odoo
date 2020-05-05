odoo.define('mail.messaging.entity.Device', function (require) {
'use strict';

const {
    fields: {
        attr,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

function DeviceFactory({ Entity }) {

    class Device extends Entity {

        /**
         * @override
         */
        static create() {
            const entity = super.create();
            entity._refresh();
            entity._onResize = _.debounce(() => entity._refresh(), 100);
            return entity;
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Called when messaging is started.
         */
        start() {
            // TODO FIXME Not using this.env.window because it's proxified, and
            // addEventListener does not work on proxified window. task-2234596
            window.addEventListener('resize', this._onResize);
        }

        /**
         * Called when messaging is stopped.
         */
        stop() {
            window.removeEventListener('resize', this._onResize);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _refresh() {
            this.update({
                globalWindowInnerHeight: this.env.window.innerHeight,
                globalWindowInnerWidth: this.env.window.innerWidth,
                isMobile: this.env.device.isMobile,
            });
        }
    }

    Device.entityName = 'Device';

    Device.fields = {
        globalWindowInnerHeight: attr(),
        globalWindowInnerWidth: attr(),
        isMobile: attr(),
    };

    return Device;
}

registerNewEntity('Device', DeviceFactory);

});
