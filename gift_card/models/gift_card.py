# Copyright (C) 2021 Akretion (<http://www.akretion.com>).
# @author Kévin Roche <kevin.roche@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class GiftCard(models.Model):
    _name = "gift.card"
    _inherit = ["code.format.mixin", "mail.thread", "mail.activity.mixin"]
    _description = "Gift Card"

    _code_mask = {"mask": "code_mask", "template": "gift_card_tmpl_id"}

    invoice_line_id = fields.Many2one(comodel_name="account.move.line")
    invoice_id = fields.Many2one("account.move", related="invoice_line_id.move_id")
    sale_line_id = fields.Many2one(
        "sale.order.line", help="sale order where the gift card was bought"
    )
    sale_id = fields.Many2one("sale.order", related="sale_line_id.order_id")
    gift_card_tmpl_id = fields.Many2one(
        comodel_name="gift.card.template",
        string="Gift Card Template ID",
        tracking=True,
    )
    payment_ids = fields.Many2many(
        comodel_name="account.payment",
        string="Payments List",
        readonly=True,
    )

    name = fields.Char(
        string="Gift Card",
        readonly=True,
        required=True,
        copy=False,
        default=lambda self: self.env["ir.sequence"].next_by_code("gift.card"),
    )
    buyer_id = fields.Many2one(
        "res.partner",
        string="Gift Card Buyer",
        readonly=True,
    )
    beneficiary_id = fields.Many2one(
        "res.partner",
        string="Gift Card Beneficiary",
        tracking=True,
    )

    gift_card_line_ids = fields.One2many(
        "gift.card.line",
        inverse_name="gift_card_id",
        string="List of Gift Card uses",
        readonly=True,
    )

    information = fields.Text(related="gift_card_tmpl_id.information")

    active = fields.Boolean(default=True, readonly=True, store=True)

    state = fields.Selection(
        [
            ("outdated", "Outdated"),
            ("soldout", "Sold Out"),
            ("active", "Active"),
            ("not_activated", "Not Activated"),
        ],
        string="State",
        required=True,
        default="active",
        compute="_compute_state",
        readonly=True,
        store=True,
        tracking=True,
    )

    is_divisible = fields.Boolean(
        default=True,
        tracking=True,
    )

    duration = fields.Integer(
        string="Gift Card Duration (in months)",
        tracking=True,
    )
    start_date = fields.Date(
        string="Start Date",
        default=lambda self: fields.Date.context_today(self),
        tracking=True,
    )
    end_date = fields.Date(
        string="End Date",
        tracking=True,
    )

    currency_id = fields.Many2one(related="journal_id.currency_id", readonly=True)
    journal_id = fields.Many2one(
        "account.journal",
        string="Gift Card Journal",
        related="gift_card_tmpl_id.journal_id",
        readonly=True,
    )

    initial_amount = fields.Monetary(
        required=True,
        currency_field="currency_id",
        tracking=True,
    )
    available_amount = fields.Monetary(
        currency_field="currency_id",
        store=True,
        compute="_compute_amounts",
        tracking=True,
    )
    total_amount_used = fields.Monetary(
        currency_field="currency_id",
        store=True,
        compute="_compute_amounts",
        inverse="_inverse_amounts",
    )

    account_move_ids = fields.Many2many(
        comodel_name="account.move",
        compute="_compute_account_move_ids",
        string="Invoices",
        readonly=True,
    )

    sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        compute="_compute_sale_order_ids",
        string="Sale Orders",
        readonly=True,
    )

    created_from_backoffice = fields.Boolean(default=False, tracking=True)

    @api.depends("gift_card_line_ids.account_move_ids")
    def _compute_account_move_ids(self):
        for rec in self:
            rec.account_move_ids = rec.gift_card_line_ids.account_move_ids

    @api.depends("gift_card_line_ids.sale_order_ids")
    def _compute_sale_order_ids(self):
        for rec in self:
            rec.sale_order_ids = rec.gift_card_line_ids.sale_order_ids

    @api.depends(
        "start_date", "end_date", "available_amount", "duration", "invoice_id.state"
    )
    def _compute_state(self):
        today = fields.Date.today()
        for card in self:
            if not card.invoice_id or card.invoice_id.state == "draft":
                card.state = "draft"
            elif card.end_date and card.end_date < today:
                card.state = "outdated"
            elif card.available_amount == 0:
                # soldout state is with_delay to avoid that the current
                # gift card's use to be soldout in the process.
                self.with_delay()._update_soldout_state(card)
            elif card.start_date and card.start_date > today:
                card.state = "not_activated"
            else:
                # FIXME: this should be done in a cron
                card.state = "active"

    @api.model
    def cron_update_gift_card_state(self):
        cards = self.search([("state", "not in", ["soldout"])])
        cards._compute_state()

    def _update_soldout_state(self, card):
        card.state = "soldout"

    @api.onchange("start_date", "duration")
    def onchange_duration_end_date(self):
        if self.duration != 0:
            self.end_date = self.start_date + relativedelta(months=self.duration)

    @api.depends(
        "initial_amount",
        "gift_card_line_ids",
        "gift_card_line_ids.amount_used",
        "is_divisible",
        "available_amount",
    )
    def _compute_amounts(self):
        for card in self:
            if card.is_divisible:
                if card.gift_card_line_ids:
                    amount_used = sum(card.gift_card_line_ids.mapped("amount_used"))
                    card.available_amount = card.initial_amount - amount_used
                    card.total_amount_used = amount_used
                else:
                    card.available_amount = card.initial_amount
                    card.total_amount_used = 0
            else:
                if card.gift_card_line_ids:
                    card.available_amount = 0
                    card.gift_card_line_ids[
                        0
                    ].amount_used = card.total_amount_used = card.initial_amount
                else:
                    card.available_amount = card.initial_amount

    def _inverse_amounts(self):
        self._compute_amounts()

    def check_gift_card_code(self, gift_card_code):
        gift_card = self.search([("code", "=", gift_card_code)])
        if gift_card.state == "active":
            return gift_card
        elif gift_card.state == "soldout":
            raise UserError(
                _("The Gift Card was fully used, no more available amount.")
            )
        elif gift_card.state == "outdated":
            raise UserError(_("The Gift Card is no longer available."))
        else:
            raise UserError(_("The Gift Card Code is invalid."))

    def check_gift_card_partner(self, partner):
        if self.beneficiary_id == partner and self.state == "active":
            return True
        else:
            raise UserError(_("The Gift Card Beneficiary is invalid."))

    @api.model
    def create(self, vals):
        if "end_date" not in vals and "start_date" in vals and "duration" in vals:
            vals["end_date"] = vals["start_date"] + relativedelta(
                months=vals["duration"]
            )
        if "beneficiary_id" not in vals:
            vals["beneficiary_id"] = vals.get("buyer_id")
        res = super().create(vals)
        return res
