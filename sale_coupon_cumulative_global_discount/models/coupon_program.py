from odoo import fields, models


class CouponProgram(models.Model):
    _inherit = "coupon.program"

    cumulative = fields.Boolean(
        "Cumulative",
        default=False,
        help="Allow this program to cumulate with another global discount.",
    )
