import logging
from datetime import datetime, timedelta

from odoo import models
from odoo.tools import populate, groupby

_logger = logging.getLogger(__name__)

# Take X first company to put some stock on it data (it is to focus data on these companies)
COMPANY_NB_WITH_STOCK = 3  # Need to be smaller than 5 (_populate_sizes["small"] of company)


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _populate_factories(self):
        res = super()._populate_factories()
        res.append(("type", populate.randomize(["consu", "service", "product"], [0.3, 0.2, 0.5])))
        # TODO: add tracked product (will need to change the pickings)
        res.append(("tracking", populate.randomize(["none", "lot", "serial"], [0.7, 0.2, 0.1])))
        return res


class Waherouse(models.Model):
    _inherit = "stock.warehouse"

    _populate_sizes = {
        "small": 5,
        "medium": 10,
        "large": 30,
    }
    _populate_dependencies = ["res.company"]

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models["res.company"][:COMPANY_NB_WITH_STOCK]

        def get_name(values, counter, **kwargs):
            return "WH-%d-%d" % (values["company_id"], counter)

        return [
            ('company_id', populate.iterate(company_ids)),
            ('name', populate.compute(get_name)),
            ('code', populate.constant("W{counter}")),
            ('reception_steps', populate.randomize(['one_step', 'two_steps', 'three_steps'], [0.6, 0.2, 0.2])),
            ('delivery_steps', populate.randomize(['ship_only', 'pick_ship', 'pick_pack_ship'], [0.6, 0.2, 0.2])),
        ]


class Location(models.Model):
    _inherit = "stock.location"
    _populate_sizes = {
        "small": 100,
        "medium": 1_000,
        "large": 10_000,
    }
    _populate_dependencies = ["stock.warehouse"]

    def _populate(self, size):
        res = super()._populate(size)
        # TODO : child-parent location
        return res

    def _populate_factories(self):
        return [
            ('name', populate.constant("PL-{counter}")),
            # TODO : usage
        ]


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    _populate_sizes = {"small": 10, "medium": 100, "large": 1_000}
    _populate_dependencies = ["stock.location"]

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models["res.company"][:COMPANY_NB_WITH_STOCK]
        warehouses = self.env["stock.warehouse"].browse(self.env.registry.populated_models["stock.warehouse"])

        def get_company_id(random, **kwargs):
            return random.choice(company_ids)

        def get_name(values, counter, **kwargs):
            return "PT-%d-%d" % (values["company_id"], counter)

        def compute_default_locations(iterator, field_name, model_name):
            random = populate.Random("compute_default_locations")
            for counter, values in enumerate(iterator):
                if values["code"] == "internal":
                    values["warehouse_id"] = random.choice(warehouses.ids)
                    values["location_src"] = #TODO
                    values["location_dest"] = 
                elif values["code"] == "incoming":

                elif values["code"] == "outgoing":

                # location_src: 'required': [('code', 'in', ('internal', 'outgoing'))]
                # location_dest: 'required': [('code', 'in', ('internal', 'incoming'))]

                # Simulate onchange of form
                values["show_operations"] = values["code"] != 'incoming'
                values["show_reserved"] = values["show_operations"] and values["code"] != 'incoming'

                yield values

        return [
            ("company_id", populate.compute(get_company_id)),
            ("name", populate.compute(get_name)),
            ("sequence_code", populate.compute("PT-{counter}-")),
            ("code", populate.iterate(['incoming', 'outgoing', 'internal'], [0.3, 0.3, 0.4])),
            ("compute_default_locations", compute_default_locations),
        ]


class Picking(models.Model):
    _inherit = "stock.picking"
    _populate_sizes = {"small": 2_000, "medium": 10_000, "large": 100_000}
    _populate_dependencies = ["stock.location", "stock.picking.type", "res.partner"]

    def _populate_factories(self):

        pop_picking_types = self.env['stock.picking.type'].browse(self.env.registry.populated_models["stock.picking.type"])
        pop_location = self.env['stock.location'].browse(self.env.registry.populated_models["stock.location"])

        now = datetime.now()

        def get_until_date(random=None, **kwargs):
            # 95.45 % of picking scheduled between (-10, 30) days and follow a gauss distribution (only +-15% picking is late)
            delta = random.gauss(10, 10)
            return now + timedelta(days=delta)

        def compute_type_information(iterator, field_name, model_name):
            picking_types = pop_picking_types
            locations_internal = pop_location.filtered_domain([('usage', '=', 'internal')])
            locations_out = pop_location.filtered_domain([('usage', '=', 'customer')])
            locations_in = pop_location.filtered_domain([('usage', '=', 'supplier')])
            locations_by_company = dict(groupby(self.env['stock.location'].search([]), key=lambda loc: loc.company_id))

            random = populate.Random("compute_type_information")
            for counter, values in enumerate(iterator):
                picking_type = random.choice(picking_types)
                values['picking_type_id'] = picking_type.id

                source_loc = picking_type.default_location_src_id
                dest_loc = picking_type.default_location_dest_id

                locations_company = self.env['stock.location'].concat(*locations_by_company[picking_type.company_id])
                if not source_loc or random.random() > 0.8:
                    if picking_type.code == "incoming":
                        source_loc = random.choice(locations_out)
                    elif picking_type.code == "outgoing":
                        source_loc = random.choice(locations_in)
                    elif picking_type.code == "internal":
                        source_loc = random.choice(locations_internal & locations_company)
                    else:
                        pass

                if not dest_loc or random.random() > 0.8:
                    if picking_type.code == "incoming":
                        dest_loc = random.choice(locations_in)
                    elif picking_type.code == "outgoing":
                        dest_loc = random.choice(locations_out)
                    elif picking_type.code == "internal":
                        # TODO : need at most 2 internal locations
                        dest_loc = random.choice((locations_internal & locations_company) - source_loc)
                    else:
                        pass

                values['location_id'] = source_loc.id
                values['location_dest_id'] = dest_loc.id
                yield values

        return [
            ("priority", populate.randomize(['1', '0'], [0.05, 0.95])),
            ("scheduled_date", populate.compute(get_until_date)),
            ("compute_type_information", compute_type_information),
        ]


class StockMove(models.Model):
    _inherit = "stock.move"
    _populate_sizes = {"small": 20_000, "medium": 200_000, "large": 2_000_000}
    _populate_dependencies = ["stock.picking"]

    def _populate(self, size):
        res = super()._populate(size)

        picking_ids = res.mapped("picking_id").ids

        # First confirm all IN picking
        random = populate.Random("picking_confirm")
        picking_to_confirm = self.env['stock.picking'].browse(random.sample(picking_ids, int(len(picking_ids) * 0.8)))
        _logger.info("Confirm 80 %% (%d) of pickings" % len(picking_to_confirm))
        picking_to_confirm.action_confirm()

        random = populate.Random("picking_validated")
        picking_to_validate = self.env['stock.picking'].browse(random.sample(picking_to_confirm.ids, int(len(picking_ids) * 0.3)))
        picking_to_validate = picking_to_validate.filtered(lambda p: p.state != "waiting")
        _logger.info("Try Mark as Done +- 30 %% (%d) of Validated pickings (remove waiting ones)" % len(picking_to_validate))
        picking_to_validate.with_context(skip_immediate=True).button_validate()

        return res

    def _populate_factories(self):
        picking_ids = self.env['stock.picking'].browse(self.env.registry.populated_models["stock.picking"])
        product_ids = self.env['product.product'].browse(self.env.registry.populated_models["product.product"]).filtered(lambda p: p.type in ('product', 'consu'))

        def next_picking_generator():
            while picking_ids:
                yield from picking_ids

        def compute_move_information(iterator, field_name, model_name):
            next_picking = next_picking_generator()
            random = populate.Random("compute_move_information")
            for counter, values in enumerate(iterator):
                product = random.choice(product_ids)
                values["product_id"] = product.id
                values["product_uom"] = product.uom_id.id

                picking = next(next_picking)
                values["picking_id"] = picking.id
                values["location_id"] = picking.location_id.id
                values["location_dest_id"] = picking.location_dest_id.id
                values["name"] = picking.name
                values["date"] = picking.scheduled_date
                values["company_id"] = picking.company_id.id
                yield values

        return [
            ("product_uom_qty", populate.randomize([i for i in range(1, 10)], [1 for _ in range(1, 10)])),
            ("compute_move_information", compute_move_information)
        ]
