import os

if os.environ.get('ENV_NAME') == 'production':
    from .prod import *
else:
    from .dev import *
