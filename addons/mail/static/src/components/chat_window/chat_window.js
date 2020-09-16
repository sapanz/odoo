odoo.define('mail/static/src/components/chat_window/chat_window.js', function (require) {
'use strict';

const components = {
    AutocompleteInput: require('mail/static/src/components/autocomplete_input/autocomplete_input.js'),
    ChatWindowHeader: require('mail/static/src/components/chat_window_header/chat_window_header.js'),
    ThreadView: require('mail/static/src/components/thread_view/thread_view.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');
const { isEventHandled } = require('mail/static/src/utils/utils.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class ChatWindow extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
        /**
         * Reference of the header of the chat window.
         * Useful to prevent click on header from wrongly focusing the window.
         */
        this._chatWindowHeaderRef = useRef('header');
        /**
         * Reference of the autocomplete input (new_message chat window only).
         * Useful when focusing this chat window, which consists of focusing
         * this input.
         */
        this._inputRef = useRef('input');
        /**
         * Reference of thread in the chat window (chat window with thread
         * only). Useful when focusing this chat window, which consists of
         * focusing this thread. Will likely focus the composer of thread, if
         * it has one!
         */
        this._threadRef = useRef('thread');
        // the following are passed as props to children
        this._onAutocompleteSelect = this._onAutocompleteSelect.bind(this);
        this._onAutocompleteSource = this._onAutocompleteSource.bind(this);
    }

    mounted() {
        this.env.messagingBus.on('will_hide_home_menu', this, this._onWillHideHomeMenu.bind(this));
        this.env.messagingBus.on('will_show_home_menu', this, this._onWillShowHomeMenu.bind(this));
        this._update();
    }

    patched() {
        this._update();
    }

    willUnmount() {
        this.env.messagingBus.off('will_hide_home_menu', this, this._onWillHideHomeMenu.bind(this));
        this.env.messagingBus.off('will_show_home_menu', this, this._onWillShowHomeMenu.bind(this));
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.chat_window}
     */
    get chatWindow() {
        return this.env.models['mail.chat_window'].get(this.props.chatWindowLocalId);
    }

    /**
     * Get the content of placeholder for the autocomplete input of
     * 'new_message' chat window.
     *
     * @returns {string}
     */
    get newMessageFormInputPlaceholder() {
        return this.env._t("Search user...");
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Apply visual position of the chat window.
     *
     * @private
     */
    _applyVisibleOffset() {
        const textDirection = this.env.messaging.__mfield_locale(this).__mfield_textDirection(this);
        const offsetFrom = textDirection === 'rtl' ? 'left' : 'right';
        const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
        this.el.style[offsetFrom] = this.chatWindow.visibleOffset + 'px';
        this.el.style[oppositeFrom] = 'auto';
    }

    /**
     * Focus this chat window.
     *
     * @private
     */
    _focus() {
        this.chatWindow.update({
            __mfield_isDoFocus: false,
            __mfield_isFocused: true,
        });
        if (this._inputRef.comp) {
            this._inputRef.comp.focus();
        }
        if (this._threadRef.comp) {
            this._threadRef.comp.focus();
        }
    }

    /**
     * Save the scroll positions of the chat window in the store.
     * This is useful in order to remount chat windows and keep previous
     * scroll positions. This is necessary because when toggling on/off
     * home menu, the chat windows have to be remade from scratch.
     *
     * @private
     */
    _saveThreadScrollTop() {
        if (!this._threadRef.comp || !this.chatWindow.__mfield_threadViewer(this)) {
            return;
        }
        this.chatWindow.__mfield_threadViewer(this).saveThreadCacheScrollPositionsAsInitial(
            this._threadRef.comp.getScrollTop()
        );
    }

    /**
     * @private
     */
    _update() {
        if (!this.chatWindow) {
            // chat window is being deleted
            return;
        }
        if (this.chatWindow.__mfield_isDoFocus(this)) {
            this._focus();
        }
        this._applyVisibleOffset();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when selecting an item in the autocomplete input of the
     * 'new_message' chat window.
     *
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    async _onAutocompleteSelect(ev, ui) {
        const chat = await this.env.messaging.getChat({ partnerId: ui.item.id });
        if (!chat) {
            return;
        }
        this.env.messaging.__mfield_chatWindowManager(this).openThread(chat, {
            makeActive: true,
            replaceNewMessage: true,
        });
    }

    /**
     * Called when typing in the autocomplete input of the 'new_message' chat
     * window.
     *
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onAutocompleteSource(req, res) {
        this.env.models['mail.partner'].imSearch({
            callback: (partners) => {
                const suggestions = partners.map(partner => {
                    return {
                        id: partner.__mfield_id(this),
                        value: partner.__mfield_nameOrDisplayName(this),
                        label: partner.__mfield_nameOrDisplayName(this),
                    };
                });
                res(_.sortBy(suggestions, 'label'));
            },
            keyword: _.escape(req.term),
            limit: 10,
        });
    }

    /**
     * Handle focus of the chat window based on position of click. The click on
     * chat window that folds it should NOT set focus on this chat window.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        const chatWindowHeader = this._chatWindowHeaderRef.el;
        if (chatWindowHeader && chatWindowHeader.contains(ev.target)) {
            // handled in _onClickedHeader
            return;
        }
        if (this.chatWindow.__mfield_isFocused(this)) {
            return;
        }
        if (isEventHandled(ev, 'Message.authorOpenChat')) {
            return;
        }
        if (isEventHandled(ev, 'Message.authorOpenProfile')) {
            return;
        }
        if (isEventHandled(ev, 'PartnerImStatusIcon.openChat')) {
            return;
        }
        this.chatWindow.focus();
    }

    /**
     * Called when clicking on header of chat window. Usually folds the chat
     * window.
     *
     * @private
     * @param {CustomEvent} ev
     */
    _onClickedHeader(ev) {
        ev.stopPropagation();
        if (this.env.messaging.__mfield_device(this).__mfield_isMobile(this)) {
            return;
        }
        if (this.chatWindow.__mfield_isFolded(this)) {
            this.chatWindow.unfold();
            this.chatWindow.focus();
        } else {
            this._saveThreadScrollTop();
            this.chatWindow.fold();
        }
    }

    /**
     * Called when an element in the thread becomes focused.
     *
     * @private
     * @param {FocusEvent} ev
     */
    _onFocusinThread(ev) {
        ev.stopPropagation();
        if (!this.chatWindow) {
            // prevent crash on destroy
            return;
        }
        this.chatWindow.update({ __mfield_isFocused: true });
    }

    /**
     * Focus out the chat window.
     *
     * @private
     */
    _onFocusout() {
        if (this._inputRef.comp) {
            this._inputRef.comp.focusout();
        }
        if (this._threadRef.comp) {
            this._threadRef.comp.focusout();
        }
        if (!this.chatWindow) {
            // ignore focus out due to record being deleted
            return;
        }
        this.chatWindow.update({ __mfield_isFocused: false });
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        /**
         * Prevent auto-focus of fuzzy search in the home menu.
         * Useful in order to allow copy/paste content inside chat window with
         * CTRL-C & CTRL-V when on the home menu.
         */
        ev.stopPropagation();
        if (!this.chatWindow) {
            // prevent crash during delete
            return;
        }
        switch (ev.key) {
            case 'Tab':
                ev.preventDefault();
                if (ev.shiftKey) {
                    this.chatWindow.focusPreviousVisibleUnfoldedChatWindow();
                } else {
                    this.chatWindow.focusNextVisibleUnfoldedChatWindow();
                }
                break;
            case 'Escape':
                if (isEventHandled(ev, 'ComposerTextInput.closeSuggestions')) {
                    break;
                }
                if (isEventHandled(ev, 'Composer.closeEmojisPopover')) {
                    break;
                }
                ev.preventDefault();
                this.chatWindow.focusNextVisibleUnfoldedChatWindow();
                this.chatWindow.close();
                break;
        }
    }

    /**
     * Save the scroll positions of the chat window in the store.
     * This is useful in order to remount chat windows and keep previous
     * scroll positions. This is necessary because when toggling on/off
     * home menu, the chat windows have to be remade from scratch.
     *
     * @private
     */
    async _onWillHideHomeMenu() {
        this._saveThreadScrollTop();
    }

    /**
     * Save the scroll positions of the chat window in the store.
     * This is useful in order to remount chat windows and keep previous
     * scroll positions. This is necessary because when toggling on/off
     * home menu, the chat windows have to be remade from scratch.
     *
     * @private
     */
    async _onWillShowHomeMenu() {
        this._saveThreadScrollTop();
    }

}

Object.assign(ChatWindow, {
    components,
    defaultProps: {
        hasCloseAsBackButton: false,
        isExpandable: false,
        isFullscreen: false,
    },
    props: {
        chatWindowLocalId: String,
        hasCloseAsBackButton: Boolean,
        isExpandable: Boolean,
        isFullscreen: Boolean,
    },
    template: 'mail.ChatWindow',
});

return ChatWindow;

});
