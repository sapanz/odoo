odoo.define('website_mass_mailing.editor', function (require) {
'use strict';

const { qweb, _t } = require('web.core');
const Dialog = require('web.Dialog');
var rpc = require('web.rpc');
var WysiwygMultizone = require('web_editor.wysiwyg.multizone');
var options = require('web_editor.snippets.options');


options.registry.mailing_list_subscribe = options.Class.extend({
    popup_template_id: "editor_new_mailing_list_subscribe_button",
    popup_title: _t("Add a Newsletter Subscribe Button"),

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    onBuilt: function () {
        this._super();
        const mailingListID = this._getMailingListID();
        if (mailingListID) {
            this.$target.attr("data-list-id", mailingListID);
        } else {
            let text =  _t('No mailing list exists in the database, Do you want to create a new mailing list!');
            Dialog.confirm(this, text, {
                title: _t("Warning!"),
                confirm_callback: () => {
                    window.location.href = '/web#action=mass_mailing.action_view_mass_mailing_lists';
                },
                cancel_callback: () => {
                    this.getParent()._onRemoveClick($.Event( "click" ));
                },
            });
        }
    },
    /**
     * Replace the current mailing_list_ID with the existing mailing_list_id selected.
     *
     * @see this.selectClass for parameters
     */
    selectMailingList: function (previewMode, widgetValue, params) {
        this.$target.attr("data-list-id", widgetValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _renderCustomXML: function (uiFragment) {
        return this._getMailingListButtons().then((mailingLists) => {
            this.mailingLists = mailingLists;
            const selectEl = uiFragment.querySelector('we-select[data-name="mailing_list"]');
            if (this.mailingLists.length && selectEl) {
                this.mailingLists.forEach(option => selectEl.append(option.cloneNode(true)));
            }
        });
    },
    /**
     * @private
     */
    _getMailingListButtons: function () {
        return rpc.query({
            model: 'mailing.list',
            method: 'name_search',
            args: ['', [['is_public', '=', true]]],
            context: this.options.recordInfo.context,
        }).then((data) => {
            // Create the buttons for the mailing list we-select
            return Object.keys(data).map(key => {
                const record = data[key];
                const button = document.createElement('we-button');
                button.dataset.selectMailingList = record[0];
                button.textContent = record[1];
                return button;
            });
        });
    },
    /**
     * @private
     */
    _getMailingListID: function () {
        let listID = parseInt(this.$target.attr('data-list-id'));
        if (!listID && this.mailingLists.length) {
            listID = this.mailingLists[0].dataset.selectMailingList;
        }
        return listID;
    },
});

options.registry.recaptchaSubscribe = options.Class.extend({
    xmlDependencies: ['/google_recaptcha/static/src/xml/recaptcha.xml'],

    /**
     * Toggle the recaptcha legal terms
     */
    toggleRecaptchaLegal: function (previewMode, value, params) {
        const recaptchaLegalEl = this.$target[0].querySelector('.o_recaptcha_legal_terms');
        if (recaptchaLegalEl) {
            recaptchaLegalEl.remove();
        } else {
            const template = document.createElement('template');
            template.innerHTML = qweb.render("google_recaptcha.recaptcha_legal_terms");
            this.$target[0].appendChild(template.content.firstElementChild);
        }
    },

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'toggleRecaptchaLegal':
                return !this.$target[0].querySelector('.o_recaptcha_legal_terms') || '';
        }
        return this._super(...arguments);
    },
});

options.registry.newsletter_popup = options.registry.mailing_list_subscribe.extend({
    popup_template_id: "editor_new_mailing_list_subscribe_popup",
    popup_title: _t("Add a Newsletter Subscribe Popup"),

    /**
     * @override
     */
    start: function () {
        this.$target.on('hidden.bs.modal.newsletter_popup_option', () => {
            this.trigger_up('snippet_option_visibility_update', {show: false});
        });
        return this._super(...arguments);
    },
    /**
     * @override
     */
    onTargetShow: function () {
        // Open the modal
        this.$target.data('quick-open', true);
        return this._refreshPublicWidgets();
    },
    /**
     * @override
     */
    onTargetHide: function () {
        // Close the modal
        const $modal = this.$('.modal');
        if ($modal.length && $modal.is('.modal_shown')) {
            $modal.modal('hide');
        }
    },
    /**
     * @override
     */
    cleanForSave: function () {
        var self = this;
        var content = this.$target.data('content');
        if (content) {
            this.trigger_up('get_clean_html', {
                $layout: $('<div/>').html(content),
                callback: function (html) {
                    self.$target.data('content', html);
                },
            });
        }
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this.$target.off('.newsletter_popup_option');
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    onBuilt: async function () {
        await this._super(...arguments);
        this._assignUniqueID();
    },
    /**
     * @override
     */
    selectMailingList: async function (previewMode, widgetValue, params) {
        await this._super(...arguments);
        this.$target.data('quick-open', true);
        this.$target.removeData('content');
        return this._refreshPublicWidgets();
    },
    /**
    * Changes the newsletter style.
    *
    * @see this.selectClass for parameters
    */
    layout: function (previewMode, widgetValue, params) {
        this.$target[0].dataset.layout = widgetValue;
    },
    /**
    * Changes the newsletter size.
    *
    * @see this.selectClass for parameters
    */
    modalSize: function (previewMode, widgetValue, params) {
        this.$target[0].dataset.modalSize = widgetValue;
    },
    /**
    * Changes the newsletter Backdrop color.
    *
    * @see this.selectClass for parameters
    */
    backdropColor: function (previewMode, widgetValue, params) {
        this.$target[0].dataset.backdropColor = widgetValue ? widgetValue: 'var(--black-50)';
    },
    /**
     * @see this.selectClass for parameters
     */
    setBackdrop(previewMode, widgetValue, params) {
        this.backdropColor(previewMode, widgetValue, params);
    },
    /**
     * @see this.selectClass for parameters
     */
    consentsDuration(previewMode, widgetValue, params) {
        this.$target[0].dataset.consentsDuration = widgetValue;
    },

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * Creates a unique ID.
     *
     * @private
     */
    _assignUniqueID: function () {
        const listID = this._getMailingListID();
        let content = 'newsletter popup';
        this.mailingLists.forEach((list) => {
            if (parseInt(list.dataset.selectMailingList) === listID) {
                content = list.textContent;
                return;
            }
        });
        this.$target.attr('id', content + Date.now());
    },
    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'selectMailingList':
                return this._getMailingListID();
            case 'layout':
            case 'modalSize':
            case 'backdropColor':
            case 'consentsDuration':
                return this.$target[0].dataset[methodName];
        }
        return this._super(...arguments);
    },
});

WysiwygMultizone.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _saveElement: function (outerHTML, recordInfo, editable) {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        var $popups = $(editable).find('.o_newsletter_popup');
        _.each($popups, function (popup) {
            var $popup = $(popup);
            var content = $popup.data('content');
            if (content) {
                defs.push(self._rpc({
                    route: '/website_mass_mailing/set_content',
                    params: {
                        'newsletter_id': parseInt($popup.attr('data-list-id')),
                        'content': content,
                    },
                }));
            }
        });
        return Promise.all(defs);
    },
});
});
