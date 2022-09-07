from odoo.tests import Form, tagged

from odoo.addons.sale_coupon_invoice_delivered.tests.common import (
    TestSaleCouponInvoiceDeliveredCommon,
)


@tagged("post_install", "-at_install")
class TestSaleCouponInvoiceDeliveredApplyOnDomain(TestSaleCouponInvoiceDeliveredCommon):
    def setUp(self):
        super(TestSaleCouponInvoiceDeliveredApplyOnDomain, self).setUp()
        self.global_promo.name = "10% on product containing chairs"
        self.global_promo.discount_apply_on = "product_domain"
        self.global_promo.discount_product_domain = '[["name","ilike","chair"]]'

    def test_sale_coupon_invoice_delivered_invoicing_partial_delivery_product_domain(
        self,
    ):
        order = self.empty_order
        self.env["sale.order.line"].create(
            {
                "product_id": self.largeCabinet.id,
                "name": "Discounted Large Cabinet",
                "product_uom_qty": 1.0,
                "order_id": order.id,
                "discount": 50.0,
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
            226.0,  # 320/2 + 4 * 16.5
            "Before computing promotions, total should be the sum of product price.",
        )

        order.recompute_coupon_lines()

        self.assertAlmostEqual(
            order.amount_total,
            219.4,  # 226.0 - 0.1 * 4 * 16.5
            2,
            "The global discount is applied",
        )

        self.assertEqual("Discounted Large Cabinet", order.order_line[0].name)
        self.assertEqual(
            order.order_line[0].qty_delivered, 0, "There is no quantity delivered"
        )
        self.assertIn("Conference chair", order.order_line[1].name)
        self.assertEqual(
            order.order_line[1].qty_delivered, 0, "There is no quantity delivered"
        )
        self.assertIn("Discount: 10%", order.order_line[2].name)
        self.assertEqual(
            order.order_line[2].qty_delivered, 0, "There is no quantity delivered"
        )

        order.action_confirm()
        order.picking_ids.move_line_ids[0].qty_done = 1
        order.picking_ids.move_line_ids[1].qty_done = 2

        picking = order.picking_ids.ensure_one()
        res = picking.button_validate()
        # Create backorder
        Form(self.env[res["res_model"]].with_context(res["context"])).save().process()
        self.assertEqual(len(order.picking_ids), 2)

        self.assertEqual("Discounted Large Cabinet", order.order_line[0].name)
        self.assertEqual(
            order.order_line[0].qty_delivered, 1, "Product has been delivered"
        )
        self.assertIn("Conference chair", order.order_line[1].name)
        self.assertEqual(
            order.order_line[1].qty_delivered, 2, "Product has been partially delivered"
        )
        self.assertIn("Discount: 10%", order.order_line[2].name)
        self.assertAlmostEqual(
            order.order_line[2].qty_invoiced,
            0,
            2,
            "Promo is not invoiced",
        )
        self.assertAlmostEqual(
            order.order_line[2].qty_delivered,
            0.5,
            2,
            "Promo is therefore partially delivered on product domain products",
        )

        invoice = order._create_invoices(final=True).ensure_one()
        invoice.action_post()

        self.assertAlmostEqual(
            order.order_line[2].qty_invoiced,
            0.5,
            2,
            "Promo is now partially invoiced on product domain products",
        )

        self.assertEqual("Discounted Large Cabinet", invoice.invoice_line_ids[0].name)
        self.assertEqual(
            invoice.invoice_line_ids[0].quantity, 1, "Product has been invoiced"
        )
        self.assertAlmostEqual(invoice.invoice_line_ids[0].price_unit, 320, 2)
        self.assertAlmostEqual(invoice.invoice_line_ids[0].price_total, 160, 2)
        self.assertIn("Conference chair", invoice.invoice_line_ids[1].name)
        self.assertEqual(
            invoice.invoice_line_ids[1].quantity,
            2,
            "Product has been partially invoiced",
        )
        self.assertAlmostEqual(invoice.invoice_line_ids[1].price_unit, 16.5, 2)
        self.assertAlmostEqual(invoice.invoice_line_ids[1].price_total, 33.0, 2)
        self.assertIn("Discount: 10%", invoice.invoice_line_ids[2].name)
        self.assertEqual(
            invoice.invoice_line_ids[2].quantity,
            0.5,
            "Discount has been partially invoiced on product domain products",
        )
        self.assertAlmostEqual(invoice.invoice_line_ids[2].price_unit, -6.6, 2)
        self.assertAlmostEqual(invoice.invoice_line_ids[2].price_total, -3.3, 2)

        backorder = order.picking_ids.filtered(
            lambda p: p.state == "assigned"
        ).ensure_one()
        backorder.move_line_ids[0].qty_done = 1
        res = backorder.button_validate()
        # Create backorder
        Form(self.env[res["res_model"]].with_context(res["context"])).save().process()
        self.assertEqual(len(order.picking_ids), 3)

        self.assertEqual("Discounted Large Cabinet", order.order_line[0].name)
        self.assertEqual(
            order.order_line[0].qty_delivered, 1, "Product has been delivered"
        )
        self.assertIn("Conference chair", order.order_line[1].name)
        self.assertEqual(
            order.order_line[1].qty_delivered, 3, "Product has been partially delivered"
        )
        self.assertIn("Discount: 10%", order.order_line[2].name)
        self.assertAlmostEqual(
            order.order_line[2].qty_invoiced,
            0.5,
            2,
            "Promo is partially invoiced on product domain products",
        )
        self.assertAlmostEqual(
            order.order_line[2].qty_delivered,
            0.75,
            2,
            "Promo is therefore partially delivered on product domain products",
        )

        invoice = order._create_invoices(final=True).ensure_one()
        invoice.action_post()

        self.assertAlmostEqual(
            order.order_line[2].qty_invoiced,
            0.75,
            2,
            "Promo is more partially invoiced on product domain products",
        )

        self.assertIn("Conference chair", invoice.invoice_line_ids[0].name)
        self.assertEqual(
            invoice.invoice_line_ids[0].quantity,
            1,
            "Product has been partially invoiced",
        )
        self.assertAlmostEqual(invoice.invoice_line_ids[0].price_unit, 16.5, 2)
        self.assertAlmostEqual(invoice.invoice_line_ids[0].price_total, 16.5, 2)
        self.assertIn("Discount: 10%", invoice.invoice_line_ids[1].name)
        self.assertEqual(
            invoice.invoice_line_ids[1].quantity,
            0.25,
            "Discount has been partially invoiced on product domain products",
        )
        self.assertAlmostEqual(invoice.invoice_line_ids[1].price_unit, -6.6, 2)
        self.assertAlmostEqual(invoice.invoice_line_ids[1].price_total, -1.65, 2)

        backorder = order.picking_ids.filtered(
            lambda p: p.state == "assigned"
        ).ensure_one()
        backorder.move_line_ids[0].qty_done = 1
        self.assertEqual(backorder.button_validate(), True)
        self.assertEqual(len(order.picking_ids), 3)

        self.assertEqual("Discounted Large Cabinet", order.order_line[0].name)
        self.assertEqual(
            order.order_line[0].qty_delivered, 1, "Product has been delivered"
        )
        self.assertIn("Conference chair", order.order_line[1].name)
        self.assertEqual(
            order.order_line[1].qty_delivered, 4, "Product has been delivered"
        )
        self.assertIn("Discount: 10%", order.order_line[2].name)
        self.assertEqual(
            order.order_line[2].qty_delivered, 1, "Promo is considered fully delivered"
        )

        invoice = order._create_invoices(final=True).ensure_one()

        invoice.action_post()
        self.assertAlmostEqual(
            order.order_line[2].qty_invoiced,
            1,
            2,
            "Promo is fully invoiced",
        )

        self.assertIn("Conference chair", invoice.invoice_line_ids[0].name)
        self.assertEqual(
            invoice.invoice_line_ids[0].quantity,
            1,
            "Product has been partially invoiced",
        )
        self.assertAlmostEqual(invoice.invoice_line_ids[0].price_unit, 16.5, 2)
        self.assertAlmostEqual(invoice.invoice_line_ids[0].price_total, 16.5, 2)
        self.assertIn("Discount: 10%", invoice.invoice_line_ids[1].name)
        self.assertEqual(
            invoice.invoice_line_ids[1].quantity,
            0.25,
            "Discount has been partially invoiced",
        )
        self.assertAlmostEqual(invoice.invoice_line_ids[1].price_unit, -6.6, 2)
        self.assertAlmostEqual(invoice.invoice_line_ids[1].price_total, -1.65, 2)
