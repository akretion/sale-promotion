from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _update_delivered_coupon_lines_quantity(self):
        # Start with no processed program
        self.processed_programs_ids -= self.processed_programs_ids
        super()._update_delivered_coupon_lines_quantity()

        # Clean all temporary fields
        self.active_programs_ids -= self.active_programs_ids
        self.processed_programs_ids -= self.processed_programs_ids

    def _set_delivered_reward_qty_for_program(self, program):
        # Call _get_reward_values_discount to avoid duplicating
        # the chainable algorithm
        self._get_reward_values_discount(program)
        super()._set_delivered_reward_qty_for_program(program)

    def _get_delivered_reward_values_discount_from_specific_products_program(
        self, program, original_program, line
    ):
        # Compute the original_program discount on program specific_products
        # We can't call super here due to sale_coupon_delivery being a bad citizen
        self.original_paid_order_lines = True
        lines = self._get_paid_order_lines()
        self.original_paid_order_lines = False

        # First filter out lines with different taxes than the current line
        lines = lines.filtered(lambda x: x.tax_id == line.tax_id)

        # Then if the orginal_program is also on specific products, we need to
        # remove the other lines
        lines = self._filter_lines_rewarded_for_program_on_specific_products(
            lines, original_program
        )

        # Then remove the current program other lines too
        lines = self._filter_lines_rewarded_for_program_on_specific_products(
            lines, program
        )

        # Finally apply the same computation as in sale_coupon.sale_order
        amount_total = sum(
            self._get_base_order_lines(original_program).mapped("price_subtotal")
        )
        currently_discounted_amount = 0
        discount = 0
        for line in lines:
            discount_line_amount = min(
                super()._get_delivered_reward_values_discount_percentage_per_line(
                    original_program, line
                ),
                amount_total - currently_discounted_amount,
            )
            discount -= discount_line_amount
            currently_discounted_amount += discount_line_amount

        return discount

    def _get_delivered_reward_values_discount_percentage_per_line(self, program, line):
        if (
            not line.is_reward_line
            or program.discount_apply_on in ["on_order", "cheapest_product"]
            or not self.active_programs_ids
        ):
            return super()._get_delivered_reward_values_discount_percentage_per_line(
                program, line
            )
        # We have active_programs and this program is on specific_products
        # We need to check if this line is a reward from an active program
        original_program = self.active_programs_ids.filtered(
            lambda x: x.discount_line_product_id == line.product_id
        )
        if (
            not original_program
            or original_program.reward_type != "discount"
            or original_program.discount_type != "percentage"
        ):
            return super()._get_delivered_reward_values_discount_percentage_per_line(
                program, line
            )

        # This line price is a reward but the reward is not on these specific products
        # We need to recompute partial discount here:
        discount = (
            self._get_delivered_reward_values_discount_from_specific_products_program(
                program, original_program, line
            )
        )

        return discount * (program.discount_percentage / 100)
