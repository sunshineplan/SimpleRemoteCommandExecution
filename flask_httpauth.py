'''
flask_httpauth
==================

This module provides Digest HTTP authentication for Flask routes.

:copyright: (C) 2014 by Miguel Grinberg.
:license:   MIT, see LICENSE for more details.

https://github.com/miguelgrinberg/Flask-HTTPAuth
'''

from functools import wraps
from hashlib import md5
from secrets import SystemRandom

from flask import make_response, request, session
from werkzeug.security import safe_str_cmp

__version__ = '3.3.1dev'


class HTTPDigestAuth:
    def __init__(self):
        def default_get_password(username):
            return None

        def default_auth_error():
            return 'Unauthorized Access'

        def _generate_random():
            return md5(str(SystemRandom().random()).encode('utf-8')).hexdigest()

        def default_generate_nonce():
            session['auth_nonce'] = _generate_random()
            return session['auth_nonce']

        def default_verify_nonce(nonce):
            session_nonce = session.get('auth_nonce')
            if nonce is None or session_nonce is None:
                return False
            return safe_str_cmp(nonce, session_nonce)

        def default_generate_opaque():
            session['auth_opaque'] = _generate_random()
            return session['auth_opaque']

        def default_verify_opaque(opaque):
            session_opaque = session.get('auth_opaque')
            if opaque is None or session_opaque is None:
                return False
            return safe_str_cmp(opaque, session_opaque)

        self.get_password(default_get_password)
        self.error_handler(default_auth_error)
        self.generate_nonce(default_generate_nonce)
        self.generate_opaque(default_generate_opaque)
        self.verify_nonce(default_verify_nonce)
        self.verify_opaque(default_verify_opaque)

    def get_password(self, f):
        self.get_password_callback = f
        return f

    def error_handler(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            res = f(*args, **kwargs)
            res = make_response(res)
            if res.status_code == 200:
                # if user didn't set status code, use 401
                res.status_code = 401
            if 'WWW-Authenticate' not in res.headers.keys():
                res.headers['WWW-Authenticate'] = self.authenticate_header()
            return res
        self.auth_error_callback = decorated
        return decorated

    def get_auth(self):
        auth = request.authorization

        # if the auth type does not match, we act as if there is no auth
        # this is better than failing directly, as it allows the callback
        # to handle special cases, like supporting multiple auth types
        if auth is not None and auth.type.lower() != 'digest':
            auth = None

        return auth

    def get_auth_password(self, auth):
        password = None

        if auth and auth.username:
            password = self.get_password_callback(auth.username)

        return password

    def login_required(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = self.get_auth()

            # Flask normally handles OPTIONS requests on its own, but in the
            # case it is configured to forward those to the application, we
            # need to ignore authentication headers and let the request through
            # to avoid unwanted interactions with CORS.
            if request.method != 'OPTIONS':  # pragma: no cover
                password = self.get_auth_password(auth)

                if not self.authenticate(auth, password):
                    # Clear TCP receive buffer of any pending data
                    request.data
                    return self.auth_error_callback()

            return f(*args, **kwargs)
        return decorated

    def generate_nonce(self, f):
        self.generate_nonce_callback = f
        return f

    def verify_nonce(self, f):
        self.verify_nonce_callback = f
        return f

    def generate_opaque(self, f):
        self.generate_opaque_callback = f
        return f

    def verify_opaque(self, f):
        self.verify_opaque_callback = f
        return f

    def get_nonce(self):
        return self.generate_nonce_callback()

    def get_opaque(self):
        return self.generate_opaque_callback()

    def generate_ha1(self, username, password):
        a1 = username + ':Authentication Required:' + password
        a1 = a1.encode('utf-8')
        return md5(a1).hexdigest()

    def authenticate_header(self):
        nonce = self.get_nonce()
        opaque = self.get_opaque()
        return f'Digest realm="Authentication Required",nonce="{nonce}",opaque="{opaque}"'

    def authenticate(self, auth, stored_password_or_ha1):
        if not auth or not auth.username or not auth.realm or not auth.uri \
                or not auth.nonce or not auth.response \
                or not stored_password_or_ha1:
            return False
        if not(self.verify_nonce_callback(auth.nonce)) or \
                not(self.verify_opaque_callback(auth.opaque)):
            return False
        a1 = auth.username + ':' + auth.realm + ':' + \
            stored_password_or_ha1
        ha1 = md5(a1.encode('utf-8')).hexdigest()
        a2 = request.method + ':' + auth.uri
        ha2 = md5(a2.encode('utf-8')).hexdigest()
        a3 = ha1 + ':' + auth.nonce + ':' + ha2
        response = md5(a3.encode('utf-8')).hexdigest()
        return safe_str_cmp(response, auth.response)

    @property
    def username(self):
        if not request.authorization:
            return ''
        return request.authorization.username
