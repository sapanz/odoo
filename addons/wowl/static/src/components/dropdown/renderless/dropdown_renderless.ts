import {Component, useState} from "@odoo/owl";

export class DropdownRenderless extends Component {
    static template = "wowl.DropdownRenderless";
    state = useState({open: this.props.openedByDefault})

    static props = {
        openedByDefault: {
            type: Boolean,
            optional: true,
        },
        depth: {
            type: Number,
            optional: true,
        },
        collapseMode: {
            type: String, // 'all', 'level', 'none'
            optional: true,
        },
    };

    static defaultProps = {
        openedByDefault: false,
        depth: 0,
        collapseMode: 'all',
    };

    /**
     * Private
     */

    /**
     * Toggle the items of the dropdown.
     * If the dropdown has multiple depth, will toggle all the levels.
     * This is because of the recursive DOM elements firing events.
     */
    _toggle() {
        this.state.open = !this.state.open;
    }

    /**
     * Toggle the items of the dropdown.
     * If the dropdown has multiple depth, will only toggle the *depth* level.
     */
    _toggleCurrent(depth: Number) {
        if (this.props.depth == depth) {
            this._toggle();
        }
    }

    /**
     * Handlers
     */

    /**
     * When the toggler element is clicked, we toggle the item visibility.
     * If the dropdown has multiple depth, toggle only the depth that has been clicked.
     */
    dropdownButtonClicked(ev: any) {
        this._toggleCurrent(ev.detail.depth)
    }

    /**
     * When an item (leaf) is clicked, check if the dropdown should collapse.
     * Can collapse one level or all levels.
     * Options are passed through props.
     */
    dropdownItemClicked(ev: any) {

        if (!ev.detail.payload) return; // this is not a leaf.

        this.trigger('item-selected', { payload: ev.detail.payload, depth: ev.detail.depth})

        if (this.props.collapseMode === 'all') {
            this._toggle();
        }

        if (this.props.collapseMode === 'level') {
            this._toggleCurrent(ev.detail.depth)
        }

    }


}
