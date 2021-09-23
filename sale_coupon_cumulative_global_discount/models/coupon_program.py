from odoo import fields, models


class CouponProgram(models.Model):
    _inherit = "coupon.program"

    cumulative = fields.Boolean(
        "Cumulative",
        default=False,
        help="Allow this program to cumulate with another global discount.",
    )

    def _is_global_discount_program(self):
        # Do not consider cumulative program as global discount
        return super()._is_global_discount_program() and not self.cumulative
