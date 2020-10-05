import { Component, useState } from "@odoo/owl";

export class Dropdown extends Component {
  static template = "wowl.Dropdown";
  state = useState({ showMe: false });
  toggleDropdown = () => { this.state.showMe = !this.state.showMe }
}
