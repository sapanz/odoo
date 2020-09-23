odoo.define('payment_ogone.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');
    const _t = core._t;

    checkoutForm.include({
        //    arj fixme: why this is needed ? without that, it does not find the functions _onOgoneTriggerTransaction _onOgonePaymentStatus
        custom_events: {
            ogone_trigger_transaction: '_onOgoneTriggerTransaction',
        },
        /**
         * Custom event used by some acquirer.
         * May be called when an iframe is coming back from the acquirer website. See Ogone...
        */
        _onOgoneTriggerTransaction: function (ev) { },
    });

    const ogoneMixin = {
        /**
         * Custom event used when the flexcheckout api has finished and return to our Odoo return url.
         * May be called when an iframe is coming back from the acquirer website. See Ogone...
        */
        _onOgoneTriggerTransaction: function (ev) {
            ev.stopPropagation();
            // The feedback spinner returned from ogone form in the iframe.
            // We must init the tx and after
            this._super(...arguments);
            // urls are encoded twice: one in python and once by Ogone.
            const initTxRoute = decodeURIComponent(decodeURIComponent(ev.data.initTxRoute));
            const landingRoute = decodeURIComponent(decodeURIComponent(ev.data.landingRoute));
            const paymentOptionId = ev.data.paymentOptionId !== undefined ? parseInt(ev.data.paymentOptionId) : null;
            const referencePrefix = ev.data.referencePrefix;
            const currencyId = ev.data.currencyId !== undefined ? parseInt(ev.data.currencyId) : null;
            const partnerId = ev.data.partnerId !== undefined ? parseInt(ev.data.partnerId) : null;
            const amount = ev.data.amount !== undefined ? parseFloat(ev.data.amount) : null;
            const orderId = ev.data['Alias.OrderId'] !== undefined ? parseFloat(ev.data['Alias.OrderId']) : null;
            const acquirerId = ev.data.acquirerId !== undefined ? parseFloat(ev.data.acquirerId) : null;
            const flow = ev.data.flow;
            const ogoneValues = {
                AliasId: ev.data['Alias.AliasId'],
                NCError: ev.data['Alias.NCError'],
                NCErrorCN: ev.data['Alias.NCErrorCN'], 
                NCErrorCVC: ev.data['Alias.NCErrorCVC'],
                NCErrorCardNo: ev.data['Alias.NCErrorCardNo'],
                NCErrorED: ev.data['Alias.NCErrorED'],
                Status: ev.data['Alias.Status'],
                SHASign: ev.data.SHASign,
                StorePermanently: ev.data['Alias.StorePermanently'],
                Bin: ev.data['Card.Bin'],
                CardHolderName: ev.data['Card.CardHolderName'],
                CardNumber: ev.data['Card.CardNumber'],
                Cvc: ev.data['Card.Cvc'],
                ExpiryDate: ev.data['Card.ExpiryDate'],
                referencePrefix: ev.data['referencePrefix'],
            };
            const tokenizationRequested = ev.data['Alias.StorePermanently'] === 'Y' ? true : false;
            this._rpc({
                route: initTxRoute,
                params: {
                    'payment_option_id': paymentOptionId,
                    'reference_prefix': referencePrefix,
                    'amount': amount,
                    'currency_id': currencyId,
                    'partner_id': partnerId,
                    'order_id': orderId,
                    'flow': flow,
                    'is_validation': false,
                    'tokenization_requested': tokenizationRequested,
                    'landing_route': landingRoute,
                    'init_tx_route': initTxRoute,
                },
            }).then(processingValues => {
                console.log(processingValues);
                console.log("THEN after init tx");
                return this._rpc({
                     route: '/payment/ogone/payments',
                     params: {
                         'acquirer_id': acquirerId,
                         'reference': processingValues.reference,
                         'partner_id': processingValues.partner_id,
                         'ogone_values': ogoneValues,
                     },
                });
            }).then(result => {
                // We redirect the parent page to the payment status page
                console.log(result)
                if (result.status == 'pending' &&  result.hasOwnProperty('html_3ds')) {
                    document.getElementsByClassName("o_payment_feedback")[0].innerHTML = result.html_3ds;
                    self.document.forms.downloadform3D.submit()
                } else if (result.state_message) {
                    // The error message is not empty. arj fixme: check other cards to see if the state_mesage is filled in other conditions.
                    document.getElementsByClassName("o_payment_feedback")[0].innerText = result.state_message;
                }
//                window.top.location.href = document.location.origin + '/payment/status'
//                    debugger;
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Prepare the inline form of Ogone for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {undefined}
         */
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
            console.log(paymentOptionId);
            if (provider !== 'ogone' || flow == 'token') {
                return this._super(...arguments);
            }
            this._setPaymentFlow('direct');
            const referencePrefix = this.txContext.referencePrefix;
            const orderId = this.txContext.orderId ? parseInt(this.txContext.orderId) : undefined;
            const isValidation = this.txContext.isValidation !== undefined
                ? this.txContext.isValidation : false;
            const landingRoute = this.txContext.landingRoute;
            // Get the available payment methods
            this._rpc({
                route: '/payment/ogone/payment_methods',
                params: {
                    'acquirer_id': paymentOptionId,
                    'partner_id': parseInt(this.txContext.partnerId),
                    'amount': this.txContext.amount ? parseFloat(this.txContext.amount) : undefined,
                    'currency_id': this.txContext.currencyId
                        ? parseInt(this.txContext.currencyId)
                        : undefined,
                    'payment_option_id': paymentOptionId,
                    'reference_prefix': referencePrefix,
                    'order_id': orderId,
                    'flow': flow,
                    'landing_route': landingRoute,
                    'init_tx_route': this.txContext.initTxRoute,
                    'isValidation': isValidation,
                },
            }).then(paymentMethodsResult => {
                let iframe = document.getElementById('ogone-dropin-container_' + paymentMethodsResult['acquirer_id']);
                iframe.firstElementChild.src = paymentMethodsResult['ogone_iframe_url'];
                // Disable pay button because user must use the Submit form inside the iframe
                document.querySelector('button[name=o_payment_submit_button]').style.visibility = 'hidden';

            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("An error occured when displayed this payment form."),
                    error.message.data.message
                );
            });
        },

        _enableButton: function () {
            // ogone display a CC form in the iframe. The pay button hidden when it is selected.
            // We display the button for other acquirers.
            document.querySelector('button[name=o_payment_submit_button]').style.visibility = 'visible';
            return this._super(...arguments);
        },


    };
    checkoutForm.include(ogoneMixin);
    manageForm.include(ogoneMixin);
});
