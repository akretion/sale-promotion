from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_applied_programs_with_rewards_on_current_order(self):
        # We need to sort the programs on sequences
        applied_programs = super()._get_applied_programs_with_rewards_on_current_order()
        return applied_programs.sorted(key="sequence")
