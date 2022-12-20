from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_reward_values_discount_from_specific_products_program(
        self, program, original_program, line
    ):
        self.current_program_id = original_program
        rv = super()._get_reward_values_discount_from_specific_products_program(
            program, original_program, line
        )
        self.current_program_id = program
        return rv
