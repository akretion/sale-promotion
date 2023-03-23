from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _set_delivered_reward_qty_for_program_discount_percentage_product_domain(
        self, program
    ):
        specific_products = program._get_discount_domain_product_ids(self)
        lines = self._get_paid_order_lines()
        # We should not exclude reward line that offer this
        # product since we need to offer only the discount
        # on the real paid product
        # (regular product - free product)
        free_product_lines = (
            self.env["coupon.program"]
            .search(
                [
                    ("reward_type", "=", "product"),
                    (
                        "reward_product_id",
                        "in",
                        specific_products.ids,
                    ),
                ]
            )
            .mapped("discount_line_product_id")
        )
        lines = lines.filtered(
            lambda x: x.product_id in (specific_products | free_product_lines)
            or x.is_reward_line
        )
        self._set_delivered_reward_qty_for_program_discount_percentage_on_specific_lines(
            program, lines
        )

    def _set_delivered_reward_qty_for_program_discount_percentage(self, program):
        super()._set_delivered_reward_qty_for_program_discount_percentage(program)
        if program.discount_apply_on == "product_domain":
            self._set_delivered_reward_qty_for_program_discount_percentage_product_domain(
                program
            )
