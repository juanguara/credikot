# -*- coding: utf-8 -*-
{
    "name": "ir_logging_retention",
    "summary": "Purge programado de ir.logging con retención por días",
    "version": "18.0.1.0.1",
    "author": "Credikot / n8n & Odoo",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "data/ir_cron.xml",
        "views/res_config_settings_views.xml"
    ],
    "installable": True,
    "application": False
}
