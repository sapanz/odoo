import {Component} from "@odoo/owl";

export class DropdownRenderlessButton extends Component {
    static template = "wowl.DropdownRenderlessButton";
    static props = {
        depth: {
            type: Number,
            optional: true
        }
    };

    static defaultProps = {
        depth: 0,
    };

    /**
     * Handlers
     */

    onClicked() {
        this.trigger('dropdown-button-clicked', {depth: this.props.depth})
    }

}
