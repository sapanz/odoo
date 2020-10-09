import { Component, hooks, misc } from "@odoo/owl";
const { useRef, useExternalListener } = hooks;
const { Portal } = misc;

export class Dialog extends Component {
  static components = { Portal };
  static defaultProps = {
    fullscreen: false,
    renderFooter: true,
    renderHeader: true,
    size: "modal-lg",
    title: "Odoo",
  };
  static props: {
    fullscreen: boolean;
    renderFooter: boolean;
    renderHeader: boolean;
    size: {
      type: String;
      validate: (s: string) => true;
      // validate: (s: string) => ["modal-xl", "modal-lg", "modal-sm"].includes(s),
    };
    title: string;
  };
  static template = "wowl.Dialog";

  modalRef = useRef("modal");

  constructor() {
    super(...arguments);
    useExternalListener(window, "keydown", this._onKeydown);
  }

  mounted() {
    const dialogContainer = document.querySelector(".o_dialog_container") as HTMLElement;
    const modals = dialogContainer.querySelectorAll(".o_dialog .modal");
    const len = modals.length;
    for (let i = 0; i < len - 1; i++) {
      const modal = modals[i] as HTMLElement;
      modal.classList.add("o_inactive_modal");
    }
    dialogContainer.classList.add("modal-open");
  }

  willUnmount() {
    const dialogContainer = document.querySelector(".o_dialog_container") as HTMLElement;
    const modals = dialogContainer.querySelectorAll(".o_dialog .modal");
    const len = modals.length;
    if (len >= 2) {
      const modal = (this.modalRef.el === modals[len - 1]
        ? modals[len - 2]
        : modals[len - 1]) as HTMLElement;
      modal.focus();
      modal.classList.remove("o_inactive_modal");
    } else {
      dialogContainer.classList.remove("modal-open");
    }
  }

  /**
   * Send an event signaling that the dialog should be closed.
   * @private
   */
  _close() {
    this.trigger("dialog-closed");
  }

  _onKeydown(ev: KeyboardEvent) {
    if (ev.key === "Escape" && !this.modalRef.el?.classList.contains("o_inactive_modal")) {
      console.log("escape");
      ev.preventDefault();
      ev.stopImmediatePropagation();
      ev.stopPropagation();
      this._close();
    }
  }
}
