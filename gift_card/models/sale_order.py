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
            gift_card_lines = [line for line in self.env["gift.card.line"].search([]) if rec.id in line.account_move_ids.invoice_line_ids.mapped('sale_line_ids').mapped('order_id').ids]
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
