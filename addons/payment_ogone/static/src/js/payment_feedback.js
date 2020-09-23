odoo.define('payment_ogone.payment_feedback', function (require) {
    "use strict";
    const publicWidget = require('web.public.widget');
    const PaymentCheckoutForm = require('payment.checkout_form');
    publicWidget.registry.ogoneFeedback = PaymentCheckoutForm.extend({
        selector: '.o_payment_feedback',
        start: function () {
            this.feedback();
        },
        feedback: function () {
            const urlParameters = this._getUrlParameters(document.URL);
            // Extract contextual values from the radio button
            const paymentOptionId = parseInt(urlParameters['paymentOptionId'], 10);
            const provider = 'ogone';
            const flow = 'direct';
            const feedbackParams = Object.assign({}, urlParameters, {provider: provider, flow: flow});
            console.log("FEEDBACK PARAMS");
            console.log(feedbackParams);
            if (!isNaN(paymentOptionId)) {
                this.trigger_up('ogone_trigger_transaction', feedbackParams);
            }
        },

        _getUrlParameters: function (url) {
            // Get the url parameters 
            const rawParameters = url.split('?')[1].split('&');
            let config = {};
            rawParameters.forEach(option => {
                const splittedOption = option.split('=');
                config[splittedOption[0]] = splittedOption[1];
            });
            return config;
        },

    });
});
