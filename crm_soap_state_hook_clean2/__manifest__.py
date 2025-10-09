{
    'name': 'CRM SOAP State Hook (clean)',
    'version': '18.0.1.0.0',
    'category': 'CRM',
    'summary': 'Hook SOAP en Ganado/Perdido con logging',
    'depends': ['crm'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/logging_menu.xml',
        'views/crm_lead_views.xml',
        'wizard/state_confirm_wizard_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
