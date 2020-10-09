import { Component } from "@odoo/owl";

export class DropdownRenderlessItem extends Component {
    static template = "wowl.DropdownRenderlessItem";
    static props = {
        payload: {
            type: Object,
            optional: true
        },
    };
    static defaultProps = {
        payload: null,
    };

    /**
     * Handlers
     */
    onClick() {
        this.trigger('dropdown-item-clicked', this.props.payload);
    }

}
