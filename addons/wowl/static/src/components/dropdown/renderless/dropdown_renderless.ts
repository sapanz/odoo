import { Component, useState } from "@odoo/owl";
import { ClientAction } from "../../../services/action_manager/helpers";

export enum DropdownToggleMode {
    Click = 'click',
    Hover = 'hover'
}

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
        toggleMode: {
            type: DropdownToggleMode,
            optional: true,
        }
    };

    static defaultProps = {
        openedByDefault: false,
        collapseMode: 'all',
        toggleMode: DropdownToggleMode.Click,
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
    onTogglerClicked() {
        if (this.props.toggleMode === DropdownToggleMode.Click) {
            this._toggle();
        }
    }

    onTogglerHovered() {
        if (this.props.toggleMode === DropdownToggleMode.Hover) {
            this._toggle();
        }
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
