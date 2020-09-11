odoo.define('web.WidgetWrapper', function (require) {
    "use strict";

    const { ComponentWrapper } = require('web.OwlCompatibility');

    class WidgetWrapper extends ComponentWrapper {
        constructor() {
            super(...arguments);
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        get $el() {
            return $(this.el);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        updateState() {
            if (this.componentRef.comp.updateState) {
                this.componentRef.comp.updateState();
            }
        }
    }
    return WidgetWrapper;
});
