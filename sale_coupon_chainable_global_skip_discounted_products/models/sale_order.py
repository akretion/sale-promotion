from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    current_original_program_id = fields.Many2one(
        "coupon.program", store=False, copy=False
    )

    def _get_reward_values_discount_from_specific_products_program(
        self, program, original_program, line
    ):
        self.current_original_program_id = original_program
        rv = super()._get_reward_values_discount_from_specific_products_program(
            program, original_program, line
        )
        self.current_original_program_id = None
        return rv

    def _get_skipped_paid_order_lines(self, paid_order_lines):
        # If we are chaining, any promo with skip_discounted_products should
        # always skip any discounted products in the order
        if (
            self.current_program_id.skip_discounted_products
            or self.current_original_program_id.skip_discounted_products
        ):
            return paid_order_lines.filtered(lambda line: line.discount == 0)
        return paid_order_lines
