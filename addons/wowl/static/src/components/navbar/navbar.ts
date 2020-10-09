import { Component, useState } from "@odoo/owl";
import { useService } from "../../core/hooks";
import { OdooEnv } from "../../types";
import {DropdownRenderless} from "../dropdown/renderless/dropdown_renderless";
import {DropdownRenderlessItem} from "../dropdown/renderless/dropdown_item_renderless";
import {DropdownRenderlessButton} from "../dropdown/renderless/dropdown_button_renderless";

export class NavBar extends Component<{}, OdooEnv> {
  static template = "wowl.NavBar";
  static components = { DropdownRenderless, DropdownRenderlessItem, DropdownRenderlessButton }

  actionManager = useService("action_manager");
  menuRepo = useService("menus");
  state = useState({ menuItems: this.menuRepo.getMenuAsTree("root").childrenTree });

  systrayItems = this.env.registries.systray.getAll();

  onMenuClicked(ev: any) {
    const { payload } = ev.detail;
    if (payload) {
          this.actionManager.doAction(payload.actionID);
    }
  }
}
