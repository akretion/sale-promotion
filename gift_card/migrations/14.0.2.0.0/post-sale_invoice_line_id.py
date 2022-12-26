# Copyright 2022 Akretion (https://www.akretion.com).
# @author Pierrick Brun <pierrick.brun@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    gift_cards = env["gift.card"].search([])
    for card in gift_cards:
        tmpl = card.gift_card_tmpl_id
        product_tmpl = tmpl.product_tmpl_id
        if card.sale_id:
            card.sale_line_id = card.sale_id.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id == product_tmpl
            )
            invoice_lines = card.sale_id.invoice_lines
            if invoice_lines and len(invoice_lines) == 1:
                card.invoice_line_id = invoice_lines
