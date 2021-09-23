from odoo.addons.sale_coupon.tests.common import TestSaleCouponCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleCouponCumulative(TestSaleCouponCommon):
    def setUp(self):
        super(TestSaleCouponCumulative, self).setUp()

        self.largeCabinet = self.env["product.product"].create(
            {
                "name": "Large Cabinet",
                "list_price": 320.0,
                "taxes_id": False,
            }
        )
        self.conferenceChair = self.env["product.product"].create(
            {
                "name": "Conference Chair",
                "list_price": 16.5,
                "taxes_id": False,
            }
        )

        self.steve = self.env["res.partner"].create(
            {
                "name": "Steve Bucknor",
                "email": "steve.bucknor@example.com",
            }
        )
        self.empty_order = self.env["sale.order"].create({"partner_id": self.steve.id})

        self.global_promo = self.env["coupon.program"].create(
            {
                "name": "10% on all orders",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 10.0,
                "program_type": "promotion_program",
                "sequence": 2,
            }
        )

    def test_program_cumulative(self):
        order = self.empty_order
        self.env["sale.order.line"].create(
            {
                "product_id": self.largeCabinet.id,
                "name": "Large Cabinet",
                "product_uom_qty": 1.0,
                "order_id": order.id,
            }
        )
        self.env["sale.order.line"].create(
            {
                "product_id": self.conferenceChair.id,
                "name": "Conference chair",
                "product_uom_qty": 4.0,
                "order_id": order.id,
            }
        )

        self.assertEqual(
            order.amount_total,
            386,  # 320 + 4 * 16.5
            "Before computing promotions, total should be the sum of product price.",
        )

        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            347.4,  # 386 - 0.1 * 386
            7,
            "The best global discount is applied",
        )

        self.env["coupon.program"].create(
            {
                "name": "50% incredible offer",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 50.0,
                "program_type": "promotion_program",
                "sequence": 3,
            }
        )

        program = self.env["coupon.program"].create(
            {
                "name": "5% with prime program",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 5.0,
                "program_type": "promotion_program",
                "sequence": 3,
            }
        )
        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            193.0,  # 386 - 0.5 * 386
            7,
            "The new best global discount is applied",
        )

        program.cumulative = True
        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            183.35,  # 386 - 0.5 * 386 - 0.05 * (386 - 0.5 * 386)
            7,
            "The best global discount and the cumulative are applied sequentially",
        )
