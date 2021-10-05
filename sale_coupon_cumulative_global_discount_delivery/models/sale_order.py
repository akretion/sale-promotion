from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_paid_order_lines(self):
        # It is necessary to duplicate this function into a submodule
        # with sale_coupon_delivery as it overrides it without calling super
        paid_order_lines = super()._get_paid_order_lines()
        return self._add_active_program_discount_lines(paid_order_lines)
