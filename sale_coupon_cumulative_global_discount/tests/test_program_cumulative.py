from odoo.addons.sale_coupon.tests.common import TestSaleCouponCommon
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

        self.drawerBlack = self.env["product.product"].create(
            {
                "name": "Drawer Black",
                "list_price": 25.0,
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
                "sequence": 20,
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
            2,
            "The best global discount is applied",
        )

        self.env["coupon.program"].create(
            {
                "name": "50% incredible offer",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 50.0,
                "program_type": "promotion_program",
                "sequence": 30,
            }
        )

        program = self.env["coupon.program"].create(
            {
                "name": "5% with prime program",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 5.0,
                "program_type": "promotion_program",
                "sequence": 50,
            }
        )
        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            193.0,  # 386 - 0.5 * 386
            2,
            "The new best global discount is applied",
        )

        program.cumulative = True
        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            183.35,  # 386 - 0.5 * 386 - 0.05 * (386 - 0.5 * 386)
            2,
            "The best global discount and the cumulative are applied sequentially",
        )

    def test_program_cumulative_order(self):
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

        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            347.4,  # 386 - 0.1 * 386
            2,
            "The best global discount is applied",
        )

        program = self.env["coupon.program"].create(
            {
                "name": "5% with prime program",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 5.0,
                "program_type": "promotion_program",
                "sequence": 30,  # Comes after 10%
                "cumulative": True,
            }
        )
        order.recompute_coupon_lines()
        lines = list(order.order_line)
        self.assertEqual(len(lines), 4, "Order should have 4 lines.")
        self.assertEqual(lines[0].name, "Large Cabinet")
        self.assertAlmostEqual(lines[0].price_total, 320.0)
        self.assertEqual(lines[1].name, "Conference chair")
        self.assertAlmostEqual(lines[1].price_total, 66.0)
        self.assertIn("Discount: 10%", lines[2].name)
        self.assertAlmostEqual(lines[2].price_total, -38.6)
        self.assertIn("Discount: 5%", lines[3].name)
        self.assertAlmostEqual(lines[3].price_total, -17.37)

        self.assertAlmostEqual(
            order.amount_total,
            330.03,  # 386 - 0.1 * 386 - 0.05 * (386 - 0.1 * 386)
            2,
            "The best global discount and the cumulative are applied in the right order",
        )

        order._get_reward_lines().unlink()
        program.sequence = 1  # Now comes first

        order.recompute_coupon_lines()

        lines = list(order.order_line)
        self.assertEqual(len(lines), 4, "Order should have 4 lines.")
        self.assertEqual(lines[0].name, "Large Cabinet")
        self.assertAlmostEqual(lines[0].price_total, 320.0)
        self.assertEqual(lines[1].name, "Conference chair")
        self.assertAlmostEqual(lines[1].price_total, 66.0)
        self.assertIn("Discount: 5%", lines[2].name)
        self.assertAlmostEqual(lines[2].price_total, -19.3)
        self.assertIn("Discount: 10%", lines[3].name)
        # self.assertAlmostEqual(lines[3].price_total, -36.67)
        self.assertAlmostEqual(
            lines[3].price_total, -38.6
        )  # 38.6 since it's not cumulative

        self.assertAlmostEqual(
            order.amount_total,
            328.1,  # 386 - 0.05 * 386 - 0.1 * 386 <- Is it what we want?
            2,
            "The best global discount and the cumulative are applied in the new order",
        )
        self.global_promo.cumulative = True
        order.recompute_coupon_lines()

        lines = list(order.order_line)
        self.assertEqual(len(lines), 4, "Order should have 4 lines.")
        self.assertEqual(lines[0].name, "Large Cabinet")
        self.assertAlmostEqual(lines[0].price_total, 320.0)
        self.assertEqual(lines[1].name, "Conference chair")
        self.assertAlmostEqual(lines[1].price_total, 66.0)
        self.assertIn("Discount: 5%", lines[2].name)
        self.assertAlmostEqual(lines[2].price_total, -19.3)
        self.assertIn("Discount: 10%", lines[3].name)
        self.assertAlmostEqual(lines[3].price_total, -36.67)

        self.assertAlmostEqual(
            order.amount_total,
            330.03,  # 386 - 0.05 * 386 - 0.1 * (386 - 0.05 * 386)
            2,
            "The global promo is now cumulative so the total is higher",
        )

    def test_program_cumulative_with_non_global_program(self):
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

        self.env["coupon.program"].create(
            {
                "name": "1 Product F = 5$ discount",
                "promo_code_usage": "no_code_needed",
                "reward_type": "discount",
                "discount_type": "fixed_amount",
                "discount_fixed_amount": 5,
                "sequence": 80,
            }
        )

        self.env["coupon.program"].create(
            {
                "name": "7% reduction on Large Cabinet in cart",
                "promo_code_usage": "no_code_needed",
                "reward_type": "discount",
                "program_type": "promotion_program",
                "discount_type": "percentage",
                "discount_percentage": 7.0,
                "discount_apply_on": "specific_products",
                "discount_specific_product_ids": [(6, 0, [self.largeCabinet.id])],
                "sequence": 90,
            }
        )

        self.env["coupon.program"].create(
            {
                "name": "20% reduction on cheapest",
                "promo_code_usage": "no_code_needed",
                "reward_type": "discount",
                "program_type": "promotion_program",
                "discount_type": "percentage",
                "discount_percentage": 20.0,
                "discount_apply_on": "cheapest_product",
                "sequence": 100,
            }
        )

        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            316.7,  # 386 - 0.1 * 386 - 5 - 0.07 * 320 - 0.2 * 16.5
            2,
            "All the promotions should be taken in account",
        )

        self.env["coupon.program"].create(
            {
                "name": "5% with prime program",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 5.0,
                "program_type": "promotion_program",
                "sequence": 500,  # Comes after 10%
                "cumulative": True,
            }
        )
        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            300.865,  # 386 - 0.1 * 386 - 5 - 0.07 * 320 - 0.2 * 16.5 - 0.05 * (386 - 0.1 * 386 - 5 - 0.07 * 320 - 0.2 * 16.5)
            2,
            "All the previous promotions and the cumulative are applied in the right order",
        )

    def test_program_cumulative_fixed_global_discount_first(self):
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
        self.env["coupon.program"].create(
            {
                "name": "50$ discount",
                "promo_code_usage": "no_code_needed",
                "reward_type": "discount",
                "discount_type": "fixed_amount",
                "discount_fixed_amount": 50,
                "sequence": 20,
            }
        )
        self.env["coupon.program"].create(
            {
                "name": "5% prime",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 5.0,
                "program_type": "promotion_program",
                "sequence": 30,
                "cumulative": True,
            }
        )

        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            282.53,  # 386 - 0.1 * 386 - 50 - 0.05 * (386 - 0.1 * 386 - 50)
            2,
            "Cumulative promo should apply on fixed amount discount.",
        )

    def test_program_cumulative_fixed_global_discount_last(self):
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
        self.env["coupon.program"].create(
            {
                "name": "50$ discount",
                "promo_code_usage": "no_code_needed",
                "reward_type": "discount",
                "discount_type": "fixed_amount",
                "discount_fixed_amount": 50,
                "sequence": 100,
            }
        )
        self.env["coupon.program"].create(
            {
                "name": "5% prime",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 5.0,
                "program_type": "promotion_program",
                "sequence": 30,
                "cumulative": True,
            }
        )

        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            280.03,  # 386 - 0.1 * 386 - 0.05 * (386 - 0.1 * 386) - 50
            2,
            "Cumulative promo should apply on fixed amount discount.",
        )

    def test_program_cumulative_multi_discounts(self):
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
            2,
            "The best global discount is applied",
        )

        self.env["coupon.program"].create(
            {
                "name": "20% prime first",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 20.0,
                "program_type": "promotion_program",
                "sequence": 1,
                "cumulative": True,
            }
        )

        # In order we have the non cumulative 10% here

        self.env["coupon.program"].create(
            {
                "name": "30% prime second",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 30.0,
                "program_type": "promotion_program",
                "sequence": 30,
                "cumulative": True,
            }
        )

        self.env["coupon.program"].create(
            {
                "name": "11% non cumulative",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 11.0,
                "program_type": "promotion_program",
                "sequence": 40,
            }
        )
        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            173.7,  # 386 - 0.2 * 386 - 0.3 * (386 - 0.2 * 386) - 0.11 * 386
            2,
            "Cumulative promo should chain, best non cumulative should apply on full total.",
        )

    def test_program_cumulative_varying_taxes(self):
        order = self.empty_order
        high_tax = self.env["account.tax"].create(
            {
                "name": "25% Tax",
                "amount_type": "percent",
                "amount": 25,
                "price_include": True,
            }
        )
        low_tax = self.env["account.tax"].create(
            {
                "name": "10% Tax",
                "amount_type": "percent",
                "amount": 10,
                "price_include": True,
            }
        )

        self.largeCabinet.taxes_id = high_tax
        self.conferenceChair.taxes_id = low_tax
        self.drawerBlack.taxes_id = False

        self.env["sale.order.line"].create(
            {
                "product_id": self.largeCabinet.id,
                "name": "High Tax Large Cabinet",
                "product_uom_qty": 1.0,
                "order_id": order.id,
            }
        )
        self.env["sale.order.line"].create(
            {
                "product_id": self.conferenceChair.id,
                "name": "Low Tax Conference chair",
                "product_uom_qty": 4.0,
                "order_id": order.id,
            }
        )
        self.env["sale.order.line"].create(
            {
                "product_id": self.drawerBlack.id,
                "name": "Untaxed Drawer Black",
                "product_uom_qty": 2.0,
                "order_id": order.id,
            }
        )
        self.env["coupon.program"].create(
            {
                "name": "5% with prime program",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 5.0,
                "program_type": "promotion_program",
                "sequence": 30,  # Comes after 10%
                "cumulative": True,
            }
        )
        self.assertAlmostEqual(
            order.amount_untaxed,
            366.0,  # 320 / 1.25 + 16.5 * 4 / 1.1 + 25 * 2
            2,
            "Untaxed amount should be 366",
        )
        self.assertAlmostEqual(
            order.amount_total,
            436.0,  # 320 + 16.5 * 4 + 25 * 2
            2,
            "Taxes should apply, taxed total should be 436",
        )
        order.recompute_coupon_lines()

        lines = list(order.order_line)
        self.assertEqual(len(lines), 9, "Order should have 9 lines.")
        self.assertEqual(lines[0].name, "High Tax Large Cabinet")
        self.assertAlmostEqual(lines[0].price_subtotal, 256.0)
        self.assertAlmostEqual(lines[0].price_total, 320.0)
        self.assertEqual(lines[1].name, "Low Tax Conference chair")
        self.assertAlmostEqual(lines[1].price_subtotal, 60.0)
        self.assertAlmostEqual(lines[1].price_total, 66.0)
        self.assertEqual(lines[2].name, "Untaxed Drawer Black")
        self.assertAlmostEqual(lines[2].price_subtotal, 50.0)
        self.assertAlmostEqual(lines[2].price_total, 50.0)
        self.assertIn("Discount: 10%", lines[3].name)
        self.assertIn("25% Tax", lines[3].name)
        self.assertAlmostEqual(lines[3].price_subtotal, -25.6)
        self.assertAlmostEqual(lines[3].price_total, -32.0)
        self.assertIn("Discount: 10%", lines[4].name)
        self.assertIn("10% Tax", lines[4].name)
        self.assertAlmostEqual(lines[4].price_subtotal, -6.0)
        self.assertAlmostEqual(lines[4].price_total, -6.6)

        self.assertIn("Discount: 10%", lines[5].name)
        self.assertAlmostEqual(lines[5].price_subtotal, -5.0)
        self.assertAlmostEqual(lines[5].price_total, -5.0)

        self.assertIn("Discount: 5%", lines[6].name)
        self.assertIn("25% Tax", lines[6].name)
        self.assertAlmostEqual(
            lines[6].price_subtotal, -11.52
        )  # - 0.05 * (256 - 0.1 * 256)
        self.assertAlmostEqual(
            lines[6].price_total, -14.4
        )  # - 0.05 * (320 - 0.1 * 320)

        self.assertIn("Discount: 5%", lines[7].name)
        self.assertIn("10% Tax", lines[7].name)
        self.assertAlmostEqual(
            lines[7].price_subtotal, -2.7
        )  # - 0.05 * (60 - 0.1 * 60)
        self.assertAlmostEqual(lines[7].price_total, -2.97)  # - 0.05 * (66 - 0.1 * 66)
        self.assertIn("Discount: 5%", lines[8].name)
        self.assertAlmostEqual(lines[8].price_subtotal, -2.25)
        self.assertAlmostEqual(lines[8].price_total, -2.25)

        self.assertAlmostEqual(
            order.amount_untaxed,
            312.93,  # 366 - (366 * 0.1) - 0.05 * (366 - (366 * 0.1))
            2,
            "Untaxed discount amount should be 329.40",
        )
        self.assertAlmostEqual(
            order.amount_total,
            372.78,  # 436 - (436 * 0.1) - 0.05 * (436 - (436 * 0.1))
            2,
            "Taxes should apply, taxed total should be 392.40",
        )
