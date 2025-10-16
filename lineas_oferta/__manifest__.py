# ============================================
# __manifest__.py
# ============================================
{
    'name': 'Líneas de Oferta',
    'version': '18.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Gestión de líneas de oferta para oportunidades CRM',
    'description': """
        Módulo para gestionar líneas de oferta asociadas a oportunidades.
        - Integración con API externa
        - Selección única de oferta
        - Sincronización automática
    """,
    'depends': ['crm', 'crm_contact_referents', 'card_validation'],
    'data': [
        'security/ir.model.access.csv',
        'views/lineas_oferta_views.xml',
        'views/cliente_alerta_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
