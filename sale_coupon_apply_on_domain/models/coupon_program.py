import ast

from odoo import models


class CouponProgram(models.Model):
    _inherit = "coupon.program"

    def _filter_not_ordered_reward_programs(self, order):
        # Add matching product_domain programs
        programs = super()._filter_not_ordered_reward_programs(order)
        for program in self:
            if (
                program.reward_type == "discount"
                and program.discount_apply_on == "product_domain"
                and order.order_line.filtered(
                    lambda line: line.product_id
                    in program._get_discount_domain_product_ids(order)
                )
            ):
                programs |= program
        return programs

    def _get_discount_domain_product_ids(self, order):
        self.ensure_one()
        order_lines = (
            order.order_line.filtered(lambda line: line.product_id)
            - order._get_reward_lines()
        )
        products = order_lines.mapped("product_id")
        if self.discount_product_domain:
            domain = ast.literal_eval(self.discount_product_domain)
            return products.filtered_domain(domain)
        return self.env["product.product"]
