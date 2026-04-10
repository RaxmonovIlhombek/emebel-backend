import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/auth/login/',
        data=b'{"username": "client", "password": "1"}',
        headers={'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req, context=ctx)
    data = json.loads(resp.read())
    print('Login payload:', data)
except Exception as e:
    print('Login error:', e)
    if hasattr(e, 'read'):
        print('Error body:', e.read().decode())
