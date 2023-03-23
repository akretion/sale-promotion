# Copyright 2022 Akretion - Florian Mounier
{
    "name": "Sale Coupon Invoice Delivered Apply On Domain",
    "summary": "This module makes sale_coupon_invoice_delivered work with sale_coupon_apply_on_domain.",
    "version": "14.0.1.0.0",
    "category": "Sales",
    "website": "https://github.com/OCA/sale-promotion",
    "depends": [
        "sale_coupon_invoice_delivered",
        "sale_coupon_apply_on_domain",
        # These should not be here, as it is now we need to create
        # as many submodule as the cartesian product of the modules
        # For now we keep it like this to avoid creating a plethora of modules
        "sale_coupon_invoice_delivered_chainable",
    ],
    "author": "Akretion, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "data": [],
    "auto_install": True,
}
