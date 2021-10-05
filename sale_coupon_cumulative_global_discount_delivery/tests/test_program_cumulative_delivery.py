from odoo.addons.sale_coupon.tests.common import TestSaleCouponCommon
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestSaleCouponCumulativeDelivery(TestSaleCouponCommon):
    def setUp(self):
        super(TestSaleCouponCumulativeDelivery, self).setUp()

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

        self.tax_15pc_excl = self.env["account.tax"].create(
            {
                "name": "15% Tax excl",
                "amount_type": "percent",
                "amount": 15,
            }
        )
        self.product_delivery_poste = self.env["product.product"].create(
            {
                "name": "The Poste",
                "type": "service",
                "categ_id": self.env.ref("delivery.product_category_deliveries").id,
                "sale_ok": False,
                "purchase_ok": False,
                "list_price": 20.0,
                "taxes_id": [(6, 0, [self.tax_15pc_excl.id])],
            }
        )
        self.carrier = self.env["delivery.carrier"].create(
            {
                "name": "The Poste",
                "fixed_price": 20.0,
                "delivery_type": "base_on_rule",
                "product_id": self.product_delivery_poste.id,
            }
        )
        self.env["delivery.price.rule"].create(
            [
                {
                    "carrier_id": self.carrier.id,
                    "max_value": 5,
                    "list_base_price": 20,
                },
                {
                    "carrier_id": self.carrier.id,
                    "operator": ">=",
                    "max_value": 5,
                    "list_base_price": 50,
                },
                {
                    "carrier_id": self.carrier.id,
                    "operator": ">=",
                    "max_value": 300,
                    "variable": "price",
                    "list_base_price": 0,
                },
            ]
        )
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

    def test_program_cumulative_delivery_no_delivery_discount(self):
        order = self.empty_order
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

        delivery_wizard = Form(
            self.env["choose.delivery.carrier"].with_context(
                {
                    "default_order_id": order.id,
                    "default_carrier_id": self.env["delivery.carrier"].search([])[1],
                }
            )
        )
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            350.03,  # 386 - 0.1 * 386 - 0.05 * (386 - 0.1 * 386) + 20
            2,
            "Delivery should not be discounted by cumulative",
        )

    def test_program_cumulative_delivery_free_shipping_coupon(self):
        order = self.empty_order
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
        self.env["coupon.program"].create(
            {
                "name": "free shipping if > 50 tax exl",
                "promo_code_usage": "code_needed",
                "promo_code": "free_shipping",
                "reward_type": "free_shipping",
                "program_type": "promotion_program",
                "rule_minimum_amount": 50,
                "sequence": 5,  # First to apply
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

        delivery_wizard = Form(
            self.env["choose.delivery.carrier"].with_context(
                {
                    "default_order_id": order.id,
                    "default_carrier_id": self.env["delivery.carrier"].search([])[1],
                }
            )
        )
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()
        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            350.03,  # 386 - 0.1 * 386 - 0.05 * (386 - 0.1 * 386) + 20
            2,
            "Delivery should not be discounted by cumulative",
        )

        self.env["sale.coupon.apply.code"].sudo().apply_coupon(order, "free_shipping")
        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            330.03,  # 386 - 0.1 * 386 - 0.05 * (386 - 0.1 * 386) + 20 - 20
            2,
            "Free delivery should be applied with no other discount on delivery",
        )
