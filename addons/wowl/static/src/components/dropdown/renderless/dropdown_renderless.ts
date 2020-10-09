import {Component, useState} from "@odoo/owl";

export class DropdownRenderless extends Component {
    static template = "wowl.DropdownRenderless";
    state = useState({open: this.props.openedByDefault})

    static props = {
        openedByDefault: {
            type: Boolean,
            optional: true,
        },
        collapseMode: {
            type: String, // 'all', 'level', 'none'
            optional: true,
        },
    };

    static defaultProps = {
        openedByDefault: false,
        collapseMode: 'all',
    };

    /**
     * Private
     */

    /**
     * Toggle the items of the dropdown.
     * If it has several levels, only the current one is toggled
     */
    _toggle() {
        this.state.open = !this.state.open;
    }

    /**
     * Toggle the items of the dropdown.
     * If it has several levels, all the levels are toggled
     */
     _closeAll() {
        this.state.open = false;
        this.trigger('should-toggle-all');
     }

    /**
     * Handlers
     */

    /**
     * When the toggler element is clicked, we toggle the item visibility.
     * If the dropdown has multiple depth, toggle only the depth that has been clicked.
     */
    dropdownButtonClicked(ev: any) {
        this._toggle()
    }

    /**
     * When an item (leaf) is clicked, check if the dropdown should collapse.
     * Can collapse one level or all levels.
     * Options are passed through props.
     */
    dropdownItemClicked(ev: any) {

        if (!ev.detail.payload) return; // this is not a leaf.

        this.trigger('item-selected', { payload: ev.detail.payload})

        if (this.props.collapseMode === 'all') {
            this._closeAll();
        }

        if (this.props.collapseMode === 'level') {
            this._toggle()
        }

    }


}
