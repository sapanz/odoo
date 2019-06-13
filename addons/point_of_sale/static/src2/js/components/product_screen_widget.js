odoo.define("point_of_sale.ProductScreenWidget", function(require) {
    const ProductListWidget = require("point_of_sale.ProductListWidget");
    const ProductCategoriesWidget = require("point_of_sale.ProductCategoriesWidget");
    const OrderWidget = require("point_of_sale.OrderWidget");
    const ActionpadWidget = require("point_of_sale.ActionpadWidget");
    const NumpadWidget = require("point_of_sale.NumpadWidget");
    const { connect } = require("point_of_sale.BackboneStore");

    class ProductScreenWidget extends owl.Component {
        constructor() {
            super(...arguments);
            this.components = {
                ProductListWidget,
                ProductCategoriesWidget,
                OrderWidget,
                ActionpadWidget,
                NumpadWidget
            };
            this.selectProduct = this.selectProduct.bind(this);
        }

        selectProduct(product) {
            // eslint-disable-next-line no-console
            console.debug(product);
            if (product.to_weight && this.props.config.iface_electronic_scale) {
                // TODO: this.gui.show_screen('scale',{product: product});
                this.props.selectedOrder.add_product(product);
            } else {
                this.props.selectedOrder.add_product(product);
            }
        }
    }

    ProductScreenWidget.props = [
        "selectedOrder",
        "products",
        "pricelist",
        "unitsByUOM"
    ];

    function mapModelToProps(model) {
        const { currency, dp, units_by_id, config } = model;
        const selectedOrder = model.get_order();
        let pricelist = model.default_pricelist;
        if (selectedOrder) {
            pricelist = selectedOrder.pricelist;
        }
        return {
            products: model.db.get_product_by_category(0),
            unitsByUOM: units_by_id,
            currency,
            decimalPrecisions: dp,
            pricelist,
            selectedOrder,
            config
        };
    }

    return connect(
        ProductScreenWidget,
        mapModelToProps
    );
});
