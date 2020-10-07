import { Component, useState } from "@odoo/owl";
import { useService } from "../../core/hooks";
import { Dropdown } from "../dropdown/dropdown";

export class NavBar extends Component {
  static template = "wowl.NavBar";
  actionManager = useService("action_manager");
  static components = { Dropdown }
  menuRepo = useService("menus");
  state = useState({ showDropdownMenu: false });

  toggleDropdownMenu() {
    this.state.showDropdownMenu = !this.state.showDropdownMenu;
  }

  _onMenuClicked(menu: any) {
    this.actionManager.doAction(menu.actionID);
    this.state.showDropdownMenu = false;
  }
  state = useState({
    appMenuItems: this.menuRepo.getApps()
  });
}
