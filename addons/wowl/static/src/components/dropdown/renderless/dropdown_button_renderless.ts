import {Component} from "@odoo/owl";

export class DropdownRenderlessButton extends Component {
    static template = "wowl.DropdownRenderlessButton";
    static props = {
    };

    static defaultProps = {
    };

    /**
     * Handlers
     */

    onClicked() {
        this.trigger('dropdown-button-clicked')
    }

}
