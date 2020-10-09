import { Component, hooks, misc } from "@odoo/owl";
const { useRef, useExternalListener } = hooks;
const { Portal } = misc;

const displayed: Dialog[] = [];

function display(dialog: Dialog) {
  const activeDialog = displayed[displayed.length - 1];
  // Deactivate previous dialog (if any)
  activeDialog?.modalRef.el?.classList.add("o_inactive_modal");
  displayed.push(dialog);
  // Update container class
  const dialogContainer = document.body.querySelector(".o_dialog_container");
  dialogContainer?.classList.add("modal-open");
}

function hide(dialog: Dialog) {
  // Remove given dialog from the list
  displayed.splice(displayed.indexOf(dialog), 1);
  const lastDialog = displayed[displayed.length - 1];
  if (lastDialog) {
    // Activate last dialog
    lastDialog.el?.focus();
    lastDialog.modalRef.el?.classList.remove("o_inactive_modal");
  } else {
    debugger
    // Update container class
    const dialogContainer = document.body.querySelector(".o_dialog_container");
    dialogContainer?.classList.remove("modal-open");
  }
}

export class Dialog extends Component  {
  static components = { Portal };
  static defaultProps = {
    fullscreen: false,
    renderFooter: true,
    renderHeader: true,
    size: "modal-lg",
    title: "Odoo",
  };
  static props: {
      fullscreen: boolean,
      renderFooter: boolean,
      renderHeader: boolean,
      size: {
        type: String,
        validate: (s: string) => true,
        // validate: (s: string) => ["modal-xl", "modal-lg", "modal-sm"].includes(s),
      },
      title: string,
  };
  static template = "wowl.Dialog";

  modalRef = useRef("modal");
  
  constructor() {
      super(...arguments);
      useExternalListener(window, 'keydown', this._onKeydown);
  }

  mounted() {
    display(this);
  }

  willUnmount() {
    hide(this);
  }

  /**
   * Send an event signaling that the dialog should be closed.
   * @private
   */
  _close() {
    this.trigger("dialog-closed");
  }

  _onKeydown(ev: KeyboardEvent) {
    if (
        ev.key === 'Escape' &&
        displayed[displayed.length - 1] === this
    ) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        ev.stopPropagation();
        this._close();
    }
  }
}
