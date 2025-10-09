{
    "name": "Contact Referents (CRM)",
    "summary": "Gestiona referentes (familiares/amigos) con validación telefónica E.164 Argentina, vinculados a contactos y oportunidades.",
    "version": "18.0.2.0.0",
    "license": "LGPL-3",
    "author": "Tu Equipo",
    "website": "",
    "depends": ["base", "contacts", "crm"],
    "external_dependencies": {
        "python": ["phonenumbers"]
    },
    "data": [
        "security/ir.model.access.csv",
        "views/referente_views.xml",
        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
        "views/crm_referente_wizard_views.xml"
    ],
    "installable": True,
    "application": False
}