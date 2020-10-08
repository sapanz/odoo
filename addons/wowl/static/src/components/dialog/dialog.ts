import * as owl from "@odoo/owl";
import { OdooEnv } from "../../types";

const { misc, Component, hooks } = owl;
const { useRef } = hooks;
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
    // Update container class
    const dialogContainer = document.body.querySelector(".o_dialog_container");
    dialogContainer?.classList.remove("modal-open");
  }
}

interface DialogProps {
  // should be replaced by using static props as usual (for validation)
  fullscreen: boolean; // used mainly in mobile mode
  renderFooter: boolean;
  renderHeader: boolean;
  size: { validate: (s: string) => "modal-xl" | "modal-lg" | "modal-sm" };
  title: String;
}

export class Dialog extends Component<DialogProps, OdooEnv> {
  static components = { Portal };
  static defaultProps = {
    fullscreen: false,
    renderFooter: true,
    renderHeader: true,
    size: "modal-lg",
    title: "Odoo",
  };
  static props: DialogProps;
  static template = "wowl.Dialog";

  modalRef = useRef("modal");

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
}
