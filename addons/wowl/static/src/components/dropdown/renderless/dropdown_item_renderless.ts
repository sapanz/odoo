import {Component} from "@odoo/owl";

export class DropdownRenderlessItem extends Component {
    static template = "wowl.DropdownRenderlessItem";
    static props = {
        emitClick: {
            type: Boolean,
            optional: true,
        },
        emitHover: {
            type: Boolean,
            optional: true,
        },
        payload: {
            type: Object,
            optional: true
        },
        depth: {
            type: Number,
            optional: true
        }
    };

    static defaultProps = {
        emitClick: true,
        emitHover: false,
        payload: null,
        depth: 0,
    };

    /**
     * Handlers
     */

    onClick() {
        if (!this.props.emitClick) return;
        this.trigger('dropdownItemClicked', {payload: this.props.payload, depth: this.props.depth})
    }

    onHover() {
        if (!this.props.emitHover) return;
        this.trigger('dropdownItemHovered', {payload: this.props.payload, depth: this.props.depth})
    }

}
