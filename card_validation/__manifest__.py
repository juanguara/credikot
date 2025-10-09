# -*- coding: utf-8 -*-
{
    "name": "CKT - Validaciones de Tarjetas",
    "version": "18.0.1.0",
    "author": "Credikot",
    "website": "https://cooperativacredikot.com.ar",
    "category": "CRM",
    "license": "LGPL-3",
    "depends": ["base", "crm"],
    "data": [
        "security/ckt_security.xml",
        "security/ir.model.access.csv",
        "views/ckt_card_validation_views.xml",
        "views/partner_inherit.xml",
        "views/crm_lead_inherit.xml",
    ],
    "installable": True,
    "application": False,
    "summary": "Entidad de validaciones de tarjetas y vínculo con CRM (por x_studio_solicitud) y Partner (por VAT).",
    "description": """
Guarda resultados de validación de tarjetas (ofuscadas), con vendor, vencimiento y resultado.
Asocia a crm.lead por x_studio_solicitud y a res.partner por VAT (CUIT/DNI).
""",
}

