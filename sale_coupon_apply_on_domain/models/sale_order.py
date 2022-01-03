from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_reward_values_discount(self, program):
        if (
            program.reward_type != "discount"
            or program.discount_apply_on != "product_domain"
        ):
            return super()._get_reward_values_discount(program)

        # Patching program to reuse super machinery:
        program.original_discount_apply_on = "product_domain"
        program.discount_apply_on = "specific_products"
        old_discount_specific_product_ids = program.discount_specific_product_ids
        program.discount_specific_product_ids = (
            program._get_discount_domain_product_ids(self)
        )
        # Copy program and patch discount_apply_on and discount_specific_product_ids
        rv = super()._get_reward_values_discount(program)
        program.original_discount_apply_on = None
        program.discount_apply_on = "product_domain"
        program.discount_specific_product_ids = old_discount_specific_product_ids
        return rv
