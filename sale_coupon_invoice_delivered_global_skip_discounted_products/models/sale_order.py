from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _set_delivered_reward_qty_for_program_discount_percentage(self, program):
        # Patch lower than _set_delivered_reward_qty_for_program to avoid conflict
        # with sale_coupon_invoice_delivered_chainable
        self.current_program_id = program
        super()._set_delivered_reward_qty_for_program_discount_percentage(program)
        self.current_program_id = None
