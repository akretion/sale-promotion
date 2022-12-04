# Copyright (C) 2021 Akretion (<http://www.akretion.com>).
# @author Kévin Roche <kevin.roche@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    gift_card_line_ids = fields.Many2many(
        comodel_name="gift.card.line",
        compute="_compute_gift_card_line",
        string="Gift Card uses",
        )
    gift_card_line_count = fields.Integer(compute="_compute_gift_card_line")

    def _compute_gift_card_line(self):
        for rec in self:
            gift_card_lines = [line for line in self.env["gift.card.line"].search([]) if rec.id in line.account_move_ids.ids]
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
            "view_mode": "tree",
            "res_model": "gift.card.line",
            "target": "current",
            "domain": [("id", "in", self.gift_card_line_ids.ids)],
            "views": views,
        }

    def action_post(self):
        res = super().action_post()
        for move in self:
            move._create_gift_card()
        return res

    def _create_gift_card(self):
        for sale in self.invoice_line_ids.mapped("sale_line_ids").mapped("order_id"):
            for line in sale.order_line:
                tmpl = line.product_id.product_tmpl_id.gift_cart_template_ids
                if tmpl:
                    i = 0
                    while i < int(line.product_uom_qty):
                        self.env["gift.card"].create(
                            {
                                "sale_id": sale.id,
                                "initial_amount": line.price_unit,
                                "is_divisible": tmpl.is_divisible,
                                "duration": tmpl.duration,
                                "buyer_id": sale.partner_id.id,
                                "gift_card_tmpl_id": tmpl.id,
                            }
                        )
                        i += 1