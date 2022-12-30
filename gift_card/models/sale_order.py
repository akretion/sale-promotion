# Copyright (C) 2022 Akretion (<http://www.akretion.com>).
# @author Kévin Roche <kevin.roche@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    gift_card_line_ids = fields.Many2many(
        comodel_name="gift.card.line",
        compute="_compute_gift_card_line",
        string="Gift Card uses",
    )
    gift_card_line_count = fields.Integer(compute="_compute_gift_card_line")

    def _compute_gift_card_line(self):
        for rec in self:
            gift_card_lines = [
                line
                for line in self.env["gift.card.line"].search([])
                if rec.id
                in line.account_move_ids.invoice_line_ids.mapped("sale_line_ids")
                .mapped("order_id")
                .ids
            ]
            rec.gift_card_line_ids = [(6, 0, [line.id for line in gift_card_lines])]
            rec.gift_card_line_count = len(gift_card_lines)

    def show_gift_card_line(self):
        views = [
            (self.env.ref("gift_card.gift_card_line_tree_view").id, "tree"),
            (self.env.ref("gift_card.gift_card_line_view_form").id, "form"),
        ]
        return {
            "name": "Gift Card uses",
            "type": "ir.actions.act_window",
            "res_id": self.id,
            "view_mode": "tree,form",
            "res_model": "gift.card.line",
            "target": "current",
            "domain": [("id", "in", self.gift_card_line_ids.ids)],
            "views": views,
        }

    def action_confirm(self):
        res = super().action_confirm()
        self._create_gift_cards()
        return res

    def _create_gift_cards(self):
        for order in self:
            for line in order.order_line:
                tmpl = line.product_id.product_tmpl_id.gift_cart_template_ids
                if tmpl:
                    invoice_line_id = None
                    invoice_line = line.mapped("invoice_lines")
                    if invoice_line and len(invoice_line) == 1:
                        invoice_line_id = invoice_line.id
                    cards = self.env["gift.card"].search(
                        [
                            "|",
                            ("sale_line_id", "=", line.id),
                            ("invoice_line_id", "in", line.invoice_lines.ids),
                        ]
                    )
                    for card in cards:
                        if not card.sale_line_id:
                            card.sale_line_id = line
                    while len(cards) < int(line.product_uom_qty):
                        new_card = self.env["gift.card"].create(
                            {
                                "sale_line_id": line.id,
                                "invoice_line_id": invoice_line_id,
                                "initial_amount": line.price_unit,
                                "is_divisible": tmpl.is_divisible,
                                "duration": tmpl.duration,
                                "buyer_id": line.order_id.partner_id.commercial_partner_id.id,
                                "gift_card_tmpl_id": tmpl.id,
                            }
                        )
                        cards |= new_card


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    gift_card_ids = fields.One2many(
        comodel_name="gift.card", inverse_name="sale_line_id"
    )
