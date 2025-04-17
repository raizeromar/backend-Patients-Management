SPECTACULAR_DOCS = {
    'TITLE': 'Patients Management API',
    'DESCRIPTION': '''
    API for managing patients, medicines, and medical records.
        
    Features:
    - Patient management with medical history
    - Medicine inventory and prescriptions
    - Medical records with doctor assignments
    - Detailed reporting capabilities
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'AUTHENTICATION_WHITELIST': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'TAGS': [
        {'name': 'patients', 'description': 'Patient management operations'},
        {'name': 'medicines', 'description': 'Medicine inventory operations'},
        {'name': 'records', 'description': 'Medical records operations'},
        {'name': 'doctors', 'description': 'Doctor management operations'},
        {'name': 'prescribed-medicines', 'description': 'Prescription management operations'},
        {'name': 'reports', 'description': 'Report generation endpoints'},
    ],
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayOperationId': True,
    }
}
