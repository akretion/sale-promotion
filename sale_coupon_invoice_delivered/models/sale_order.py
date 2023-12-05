from odoo import _, api, fields, models
from odoo.tools import float_is_zero


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_delivred_quantity_for_line(self, line):
        return line.qty_delivered

    def _get_program_reward_lines_to_set_delivered_reward_qty(self, program):
        return self.order_line.filtered(
            lambda line: line.product_id == program.discount_line_product_id
        )

    def _set_delivered_reward_qty_for_program_product(self, program):
        # In case of free product reward should be delivered only if the
        # free product is delivered
        product_line = self.order_line.filtered(
            lambda sol: sol.product_id == program.reward_product_id
        )
        reward_lines = self._get_program_reward_lines_to_set_delivered_reward_qty(
            program
        )
        reward_lines._set_delivered_reward_qty(
            1 if self._get_delivred_quantity_for_line(product_line) > 0 else 0
        )

    def _set_delivered_reward_qty_for_program_discount_fixed_amount(self, program):
        reward_lines = self._get_program_reward_lines_to_set_delivered_reward_qty(
            program
        )
        # In case of fixed amount for now let's consider it delivered
        reward_lines._set_delivered_reward_qty(1)

    def _set_delivered_reward_qty_for_program_discount_percentage_cheapest_product(
        self, program
    ):
        reward_lines = self._get_program_reward_lines_to_set_delivered_reward_qty(
            program
        )
        line = self._get_cheapest_line()
        reward_lines._set_delivered_reward_qty(
            1 if self._get_delivred_quantity_for_line(line) > 0 else 0
        )

    def _set_delivered_reward_qty_for_program_discount_percentage_specific_products(
        self, program
    ):
        lines = self._get_paid_order_lines()
        # We should not exclude reward line that offer this
        # product since we need to offer only the discount
        # on the real paid product
        # (regular product - free product)
        free_product_lines = (
            self.env["coupon.program"]
            .search(
                [
                    ("reward_type", "=", "product"),
                    (
                        "reward_product_id",
                        "in",
                        program.discount_specific_product_ids.ids,
                    ),
                ]
            )
            .mapped("discount_line_product_id")
        )
        lines = lines.filtered(
            lambda x: x.product_id
            in (program.discount_specific_product_ids | free_product_lines)
        )
        self._set_delivered_reward_qty_for_program_discount_percentage_on_specific_lines(
            program, lines
        )

    def _set_delivered_reward_qty_for_program_discount_percentage_on_order(
        self, program
    ):
        lines = self._get_paid_order_lines()
        self._set_delivered_reward_qty_for_program_discount_percentage_on_specific_lines(
            program, lines
        )

    def _get_delivered_reward_values_discount_percentage_per_line(self, program, line):
        discount_amount = (
            self._get_delivred_quantity_for_line(line)
            * line.price_reduce
            * (program.discount_percentage / 100)
        )
        return discount_amount

    def _set_delivered_reward_qty_for_program_discount_percentage_on_specific_lines(
        self, program, lines
    ):
        reward_lines = self._get_program_reward_lines_to_set_delivered_reward_qty(
            program
        )
        amount_total = sum(
            [
                line.price_total if line.tax_id.price_include else line.price_subtotal
                for line in self._get_base_order_lines(program)
            ]
        )
        discount_by_taxes = {}
        currently_discounted_amount = 0
        for line in lines:
            discount_line_amount = min(
                self._get_delivered_reward_values_discount_percentage_per_line(
                    program, line
                ),
                amount_total - currently_discounted_amount,
            )

            if discount_line_amount:
                if line.tax_id in discount_by_taxes:
                    discount_by_taxes[line.tax_id] -= discount_line_amount
                else:
                    discount_by_taxes[line.tax_id] = (
                        -discount_line_amount if discount_line_amount > 0 else 0
                    )

            currently_discounted_amount += discount_line_amount

        for line in reward_lines:
            if float_is_zero(
                line.price_unit, precision_rounding=line.currency_id.rounding
            ):
                # If the price unit is 0, we should consider the reward
                # as delivered
                line._set_delivered_reward_qty(1)
                continue

            delivered_reward_qty = (
                discount_by_taxes.get(line.tax_id, 0) / line.price_unit
            )
            # Clamp the delivered reward qty between 0 and the qty of the line
            # (which should be 1)
            delivered_reward_qty = max(
                0, min(delivered_reward_qty, line.product_uom_qty)
            )

            line._set_delivered_reward_qty(delivered_reward_qty)

    def _set_delivered_reward_qty_for_program_discount_percentage(self, program):
        if program.discount_apply_on == "cheapest_product":
            self._set_delivered_reward_qty_for_program_discount_percentage_cheapest_product(
                program
            )
        elif program.discount_apply_on == "specific_products":
            self._set_delivered_reward_qty_for_program_discount_percentage_specific_products(
                program
            )
        elif program.discount_apply_on == "on_order":
            self._set_delivered_reward_qty_for_program_discount_percentage_on_order(
                program
            )

    def _set_delivered_reward_qty_for_program_discount(self, program):
        if program.discount_type == "fixed_amount":
            self._set_delivered_reward_qty_for_program_discount_fixed_amount(program)
        elif program.discount_type == "percentage":
            self._set_delivered_reward_qty_for_program_discount_percentage(program)

    def _set_delivered_reward_qty_for_program(self, program):
        if program.reward_type == "product":
            self._set_delivered_reward_qty_for_program_product(program)
        elif program.reward_type == "discount":
            self._set_delivered_reward_qty_for_program_discount(program)

    def recompute_coupon_lines(self):
        super().recompute_coupon_lines()
        self._update_delivered_coupon_lines_quantity()

    def update_delivered_coupon_lines_quantity(self):
        self._update_delivered_coupon_lines_quantity()

    def _update_delivered_coupon_lines_quantity(self):
        applied_programs = self._get_applied_programs_with_rewards_on_current_order()
        order_lines = (
            self.order_line.filtered(lambda line: line.product_id)
            - self._get_reward_lines()
        )
        products = order_lines.mapped("product_id")

        # Shortcut if everything non reward is delivered then all rewards are
        # delivered
        if all(
            self._get_delivred_quantity_for_line(line) == line.product_uom_qty
            for line in order_lines
        ):
            self._get_reward_lines()._set_delivered_reward_qty(1)
            return

        for program in applied_programs:
            # First check if program still applies on delivered quantities

            # To keep it simple for now only check if at least one of
            # necessary products is delivered, except free products

            valid_products = (
                (
                    program._get_valid_products(products)
                    if program.rule_products_domain
                    and program.rule_products_domain != "[]"
                    else products
                )
                if program.reward_type != "product"
                else program.reward_product_id
            )
            # If the program is a percentage discount and there is other product
            # rewards, we should not consider this product as a valid product
            # for the program if all the products are rewarded, i.e. the
            # percentage promotion does not apply on it
            if program.discount_type == "percentage":
                free_product_programs = applied_programs.filtered(
                    lambda p: p.reward_type == "product" and p != program
                )
                for product_program in free_product_programs:
                    if (
                        order_lines.filtered(
                            lambda sol: sol.product_id
                            == product_program.reward_product_id
                        ).product_uom_qty
                        == self.order_line.filtered(
                            lambda sol: sol.product_id
                            == product_program.discount_line_product_id
                        ).product_uom_qty
                    ):
                        valid_products -= product_program.reward_product_id

            qty_delivered = sum(
                self._get_delivred_quantity_for_line(line)
                for line in order_lines.filtered(
                    lambda sol: sol.product_id in valid_products
                )
            )
            if not qty_delivered:
                reward_lines = (
                    self._get_program_reward_lines_to_set_delivered_reward_qty(program)
                )
                reward_lines._set_delivered_reward_qty(0)
                continue

            # Do we consider reward for rule_minimum_amount delivered only when
            # this minimum amount has been delivered?

            self._set_delivered_reward_qty_for_program(program)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_delivered_method = fields.Selection(
        selection_add=[("reward_stock_move", "Reward from Stock Moves")]
    )
    delivered_reward_qty = fields.Float(
        string="Prorata of reward from delivered quantities",
        digits=0,
    )

    @api.depends("is_reward_line", "product_id.invoice_policy")
    def _compute_qty_delivered_method(self):
        super(SaleOrderLine, self)._compute_qty_delivered_method()

        for line in self:
            if line.is_reward_line and line.product_id.invoice_policy == "delivery":
                line.qty_delivered_method = "reward_stock_move"

    @api.depends("delivered_reward_qty")
    def _compute_qty_delivered(self):
        # Might be interesting to directly compute delivered quantities here instead
        # But it'll be a problem for chainable rewards
        super(SaleOrderLine, self)._compute_qty_delivered()

        for line in self:
            if line.qty_delivered_method == "reward_stock_move":
                line.qty_delivered = line.delivered_reward_qty

    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)
        if "qty_delivered" in vals:
            self.order_id._update_delivered_coupon_lines_quantity()
        return res

    def _get_precise_invoice_qty_for_reward_stock_move(self):
        total_price = (
            self.price_total if self.tax_id.price_include else self.price_subtotal
        )
        if float_is_zero(total_price, precision_rounding=self.currency_id.rounding):
            return 0
        # Get the quantity from the ratio of the total invoiced price
        # and the total reward price
        invoiced_sum = 0.0
        for invoice_line in self.invoice_lines:
            if invoice_line.move_id.state != "cancel":
                if invoice_line.move_id.move_type == "out_invoice":
                    invoiced_sum += (
                        invoice_line.price_total
                        if any(invoice_line.tax_ids.mapped("price_include"))
                        else invoice_line.price_subtotal
                    )
                elif invoice_line.move_id.move_type == "out_refund":
                    invoiced_sum -= (
                        invoice_line.price_total
                        if any(invoice_line.tax_ids.mapped("price_include"))
                        else invoice_line.price_subtotal
                    )
        return invoiced_sum / total_price

    @api.depends(
        "invoice_lines.move_id.state", "invoice_lines.quantity", "price_subtotal"
    )
    def _get_invoice_qty(self):
        for line in self:
            if line.qty_delivered_method == "reward_stock_move":
                line.qty_invoiced = (
                    line._get_precise_invoice_qty_for_reward_stock_move()
                )
            else:
                super(SaleOrderLine, line)._get_invoice_qty()

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        if self.qty_delivered_method == "reward_stock_move":
            res["quantity"] = 1
            res["price_unit"] = (
                self.delivered_reward_qty
                - self._get_precise_invoice_qty_for_reward_stock_move()
            ) * (self.price_total if self.tax_id.price_include else self.price_subtotal)
        return res

    @api.onchange("product_uom_qty")
    def _onchange_product_uom_qty(self):
        rv = super()._onchange_product_uom_qty()

        if (
            self.state == "sale"
            and self.product_id.type in ["product", "consu"]
            and self.order_id.order_line.filtered(
                lambda sol: sol.is_reward_line and sol.qty_invoiced > 0
            )
        ):
            warning_mess = {
                "title": _("Ordered quantity changed on already invoiced order!"),
                "message": _(
                    "You are changing the ordered quantity on an already "
                    "invoiced order with partial promotion delivered! "
                    "This could result on inconsistencies on promotion amount "
                    "for future invoices. Beware!"
                ),
            }
            return {"warning": warning_mess}

        return rv

    def _set_delivered_reward_qty(self, qty):
        self.write({"delivered_reward_qty": qty})
