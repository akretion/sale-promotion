from odoo import fields, models


class CouponProgram(models.Model):
    _inherit = "coupon.program"

    cumulative = fields.Boolean(
        "Cumulative",
        default=False,
        help="Allow this program to cumulate with another global discount.",
    )

    def _is_global_discount_program(self):
        self.ensure_one()
        return (
            self.promo_applicability == "on_current_order"
            and self.reward_type == "discount"
            and self.discount_type == "percentage"
            and self.discount_apply_on == "on_order"
            and not self.cumulative
        )
