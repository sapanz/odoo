odoo.define('mail/static/src/components/composer_suggested_recipient/composer_suggested_recipient.js', function (require) {
'use strict';

const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { FormViewDialog } = require('web.view_dialogs');
const { ComponentAdapter } = require('web.OwlCompatibility');

const { Component } = owl;
const { useRef } = owl.hooks;

class FormViewDialogComponentAdapter extends ComponentAdapter {

    renderWidget() {
        // Ensure the dialog is properly reconstructed. Without this line, it is
        // impossible to open the dialog again after having it closed a first
        // time, because the DOM of the dialog has disappeared.
        return this.willStart();
    }

}

const components = {
    FormViewDialogComponentAdapter,
};

class ComposerSuggestedRecipient extends Component {

    constructor(...args) {
        super(...args);
        this.id = _.uniqueId('o_ComposerSuggestedRecipient_');
        useModels();
        /**
         * Form view dialog class. Useful to reference it in the template.
         */
        this.FormViewDialog = FormViewDialog;
        /**
         * Reference of the checkbox. Useful to know whether it was checked or
         * not, to properly update the corresponding state in the record or to
         * prompt the user with the partner creation dialog.
         */
        this._checkboxRef = useRef('checkbox');
        /**
         * Reference of the partner creation dialog. Useful to open it, for
         * compatibility with old code.
         */
        this._dialogRef = useRef('dialog');
        /**
         * Whether the dialog is currently open. `_dialogRef` cannot be trusted
         * to know if the dialog is open due to manually calling `open` and
         * potential out of sync with component adapter.
         */
        this._isDialogOpen = false;
        this._onDialogSaved = this._onDialogSaved.bind(this);
    }

    mounted() {
        this._update();
    }

    patched() {
        this._update();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string|undefined}
     */
    get ADD_AS_RECIPIENT_AND_FOLLOWER_REASON() {
        if (!this.suggestedRecipientInfo) {
            return undefined;
        }
        return this.env._t(_.str.sprintf(
            "Add as recipient and follower (reason: %s)",
            this.suggestedRecipientInfo.__mfield_reason(this)
        ));
    }

    /**
     * @returns {string}
     */
    get PLEASE_COMPLETE_CUSTOMER_S_INFORMATION() {
        return this.env._t("Please complete customer's information");
    }

    /**
     * @returns {mail.suggested_recipient_info}
     */
    get suggestedRecipientInfo() {
        return this.env.models['mail.suggested_recipient_info'].get(this.props.suggestedRecipientInfoLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (this._checkboxRef.el && this.suggestedRecipientInfo) {
            this._checkboxRef.el.checked = this.suggestedRecipientInfo.__mfield_isSelected(this);
        }
    }

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onChangeCheckbox() {
        const isChecked = this._checkboxRef.el.checked;
        this.suggestedRecipientInfo.update({ __mfield_isSelected: isChecked });
        if (!this.suggestedRecipientInfo.__mfield_partner(this)) {
            // Recipients must always be partners. On selecting a suggested
            // recipient that does not have a partner, the partner creation form
            // should be opened.
            if (isChecked && this._dialogRef && !this._isDialogOpen) {
                this._isDialogOpen = true;
                this._dialogRef.comp.widget.on('closed', this, () => {
                    this._isDialogOpen = false;
                });
                this._dialogRef.comp.widget.open();
            }
        }
    }

    /**
     * @private
     */
    _onDialogSaved() {
        const thread = this.suggestedRecipientInfo && this.suggestedRecipientInfo.__mfield_thread(this);
        if (!thread) {
            return;
        }
        thread.fetchAndUpdateSuggestedRecipients();
    }
}

Object.assign(ComposerSuggestedRecipient, {
    components,
    props: {
        suggestedRecipientInfoLocalId: String,
    },
    template: 'mail.ComposerSuggestedRecipient',
});

return ComposerSuggestedRecipient;

});
