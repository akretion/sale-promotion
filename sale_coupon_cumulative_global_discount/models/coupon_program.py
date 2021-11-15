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


class SaleCouponApplyCode(models.TransientModel):
    _inherit = "sale.coupon.apply.code"

    def process_coupon(self):
        # Force a global recompute since orders can be cumulative
        order = self.env["sale.order"].browse(self.env.context.get("active_id"))
        super().process_coupon()
        order.recompute_coupon_lines()
