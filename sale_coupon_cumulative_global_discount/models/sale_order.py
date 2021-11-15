from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    processed_programs_ids = fields.Many2many("coupon.program", store=False, copy=False)
    active_programs_ids = fields.Many2many("coupon.program", store=False, copy=False)

    def _update_existing_reward_lines(self):
        # We need to store the already processed programs to take their discount
        # in account in the further discount

        # Ensure we start the computation with no already processed programs
        self.processed_programs_ids -= self.processed_programs_ids
        rv = super()._update_existing_reward_lines()
        # Clean many2many again
        self.processed_programs_ids -= self.processed_programs_ids
        return rv

    def _add_active_program_discount_lines(self, paid_order_lines):
        for program in self.active_programs_ids:
            paid_order_lines |= self.order_line.filtered(
                lambda line: line.product_id == program.discount_line_product_id
            )
        return paid_order_lines

    def _get_paid_order_lines(self):
        # We return product order lines and global discounts in case of
        # a cumulative promotion
        paid_order_lines = super()._get_paid_order_lines()
        return self._add_active_program_discount_lines(paid_order_lines)

    def _get_reward_values_discount(self, program):
        # We set active_programs_ids to processed_programs_ids
        # if we need to take these in account

        # If the current program is a cumulative global discount then take
        # other program in account to compute the final discount

        if (
            program.discount_apply_on == "on_order"
            and program.discount_type == "percentage"
            and program.promo_applicability == "on_current_order"
            and program.cumulative
        ):
            self.active_programs_ids = self.processed_programs_ids
        else:
            self.active_programs_ids -= self.active_programs_ids

        reward_values_discount = super()._get_reward_values_discount(program)

        # Cumulative apply on all programs
        self.processed_programs_ids += program

        return reward_values_discount

    def _get_applied_programs_with_rewards_on_current_order(self):
        # We need to sort the programs on sequences
        applied_programs = super()._get_applied_programs_with_rewards_on_current_order()
        return applied_programs.sorted(key="sequence")
