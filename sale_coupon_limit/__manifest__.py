# Copyright 2021 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Sale Coupon Limit",
    "summary": "Restrict number of promotions per customer or salesman",
    "version": "14.0.1.0.0",
    "development_status": "Production/Stable",
    "category": "Sale",
    "website": "https://github.com/OCA/sale-promotion",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "maintainers": ["chienandalu"],
    "license": "AGPL-3",
    "depends": ["sale_coupon", "sale_commercial_partner"],
    "data": ["views/coupon_program_views.xml", "security/ir.model.access.csv"],
}
