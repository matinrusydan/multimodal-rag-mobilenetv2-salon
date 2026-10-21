"""OAuth loopback tests use fake HTTP, browser, clock and a temporary store."""
import argparse
import base64
import hashlib
import io
import json
import sys
from urllib.parse import parse_qs, urlencode

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app import chatgpt_auth as auth


def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


@pytest.fixture
def login_flow(monkeypatch, tmp_path):
    monkeypatch.setattr(auth, 'auth_path', lambda: tmp_path / 'app.credentials')
    monkeypatch.setattr(auth, '_protect', lambda raw, decrypt=False: raw)
    clock = {'now': 0}
    monkeypatch.setattr(auth.time, 'monotonic', lambda: clock['now'])
    monkeypatch.setattr(auth.time, 'time', lambda: 1000)
    flow = {'params': {}, 'browser': [], 'http': [], 'responses': [], 'states': ['correct'],
            'clock': clock, 'identity_changes': {}}
    original_urlencode = auth.urlencode
    def capture_params(params):
        flow['params'].update(params)
        return original_urlencode(params)
    monkeypatch.setattr(auth, 'urlencode', capture_params)
    monkeypatch.setattr(auth.webbrowser, 'open', lambda url: flow['browser'].append(url) or True)

    class Server:
        def __init__(self, address, callback):
            flow['address'] = address
            self.callback = callback
            self.server_port = address[1] or 43210
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def handle_request(self):
            clock['now'] += 1
            if not flow['states']: return
            state = flow['states'].pop(0)
            query = {'state': flow['params']['state'] if state == 'correct' else 'wrong',
                     'code': 'callback-secret-code', 'client_id': 'issued-client'}
            handler = object.__new__(self.callback)
            handler.path = '/auth/callback?' + urlencode(query)
            handler.send_response = lambda status: flow['responses'].append(status)
            handler.send_header = lambda *args: None
            handler.end_headers = lambda: None
            handler.wfile = io.BytesIO()
            handler.do_GET()
    monkeypatch.setattr(auth, 'HTTPServer', Server)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_numbers()
    jwks = {'keys': [{'kid': 'test', 'kty': 'RSA', 'n': b64(public.n.to_bytes(256, 'big')),
                      'e': b64(public.e.to_bytes(3, 'big'))}]}
    def identity():
        claims = {'iss': auth.ISSUER, 'aud': 'issued-client', 'sub': 'test-subject',
                  'exp': 2000, 'nonce': flow['params']['nonce'], **flow['identity_changes']}
        value = b64(json.dumps({'alg': 'RS256', 'kid': 'test'}).encode()) + '.' + b64(json.dumps(claims).encode())
        return value + '.' + b64(key.sign(value.encode(), padding.PKCS1v15(), hashes.SHA256()))
    def http(request):
        flow['http'].append(request)
        if str(request.url) == auth.TOKEN:
            data = parse_qs(request.content.decode())
            assert data['code'] == ['callback-secret-code']
            assert data['client_id'] == ['issued-client']
            assert data['redirect_uri'] == [flow['params']['redirect_uri']]
            assert b64(hashlib.sha256(data['code_verifier'][0].encode()).digest()) == flow['params']['code_challenge']
            assert flow['params']['code_challenge_method'] == 'S256'
            return httpx.Response(200, json={'access_token': 'test-access-secret', 'refresh_token': 'test-refresh-secret',
                                            'id_token': identity(), 'scope': auth.PLAN_SCOPE,
                                            'token_type': 'Bearer', 'expires_in': 3600})
        if request.url.path == '/.well-known/openid-configuration':
            return httpx.Response(200, json={'issuer': auth.ISSUER, 'jwks_uri': auth.ISSUER + '/jwks'})
        assert str(request.url) == auth.ISSUER + '/jwks'
        return httpx.Response(200, json=jwks)
    client = httpx.Client(transport=httpx.MockTransport(http))
    monkeypatch.setattr(auth.httpx, 'Client', lambda **kwargs: client)
    return flow


@pytest.mark.parametrize('manual', [True, False])
def test_login_keeps_pkce_oidc_and_loopback_with_manual_or_desktop(login_flow, capsys, manual):
    auth.login(no_browser=manual, callback_port=8123 if manual else None)
    assert login_flow['address'] == ('127.0.0.1', 8123 if manual else 0)
    assert auth.load()['access_token'] == 'test-access-secret'
    assert auth.load()['subject'] == 'test-subject'
    assert len(login_flow['http']) == 3
    output = capsys.readouterr().out
    for secret in ('test-access-secret', 'test-refresh-secret', 'callback-secret-code'):
        assert secret not in output
    if manual:
        assert not login_flow['browser']
        assert len(output.splitlines()) == 1
        assert output.startswith(auth.AUTHORIZE + '?')
        assert 'code=' not in output
    else:
        assert len(login_flow['browser']) == 1
        assert 'terverifikasi' in output


def test_wrong_state_is_ignored_before_correct_callback(login_flow):
    login_flow['states'] = ['wrong', 'correct']
    auth.login()
    assert login_flow['responses'] == [400, 200]
    assert auth.load()['subject'] == 'test-subject'


@pytest.mark.parametrize('states', [[], ['wrong']])
def test_timeout_and_wrong_state_never_exchange_tokens(login_flow, capsys, states):
    login_flow['states'] = states
    with pytest.raises(RuntimeError, match='batas waktu'):
        auth.login(timeout=2, no_browser=True)
    assert not login_flow['http']
    assert not auth.load().get('access_token')
    assert 'callback-secret-code' not in capsys.readouterr().out


@pytest.mark.parametrize('claims', [{'nonce': 'wrong'}, {'aud': 'wrong'},
                                    {'iss': 'https://wrong.example'}, {'exp': 0}])
def test_login_never_activates_identity_that_fails_oidc(login_flow, claims):
    login_flow['identity_changes'] = claims
    with pytest.raises(ValueError): auth.login(no_browser=True)
    assert not auth.load().get('access_token')


def test_desktop_browser_failure_never_exchanges_tokens(login_flow, monkeypatch):
    monkeypatch.setattr(auth.webbrowser, 'open', lambda url: False)
    with pytest.raises(RuntimeError, match='Browser'): auth.login()
    assert not login_flow['http']


@pytest.mark.parametrize('port', [0, -1, 65536, 'localhost:8000', True])
def test_invalid_callback_ports_rejected_before_store_access(monkeypatch, port):
    monkeypatch.setattr(auth, 'auth_path', lambda: pytest.fail('No store access for invalid flags'))
    with pytest.raises(argparse.ArgumentTypeError): auth.login(callback_port=port)


@pytest.mark.parametrize('port', [1, 65535])
def test_callback_port_range_endpoints(login_flow, port):
    auth.login(no_browser=True, callback_port=port)
    assert login_flow['address'] == ('127.0.0.1', port)


def test_linux_store_uses_xdg_location_without_reading_credentials(monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.setattr(auth, 'os', SimpleNamespace(name='posix', environ={'XDG_DATA_HOME': str(tmp_path)}))
    assert auth.auth_path() == tmp_path / 'RAGSalon' / 'chatgpt-plan.credentials'


def test_cli_passes_manual_flags_without_auth(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, 'argv', ['auth', 'login', '--no-browser', '--callback-port', '8123'])
    monkeypatch.setattr(auth, 'login', lambda **kwargs: calls.append(kwargs))
    auth.main()
    assert calls == [{'no_browser': True, 'callback_port': 8123}]


@pytest.mark.parametrize('port', ['0', '-1', '65536', 'not-a-port'])
def test_cli_rejects_invalid_callback_port_before_login(monkeypatch, port):
    monkeypatch.setattr(sys, 'argv', ['auth', 'login', '--callback-port', port])
    monkeypatch.setattr(auth, 'login', lambda **kwargs: pytest.fail('Invalid port reached login'))
    with pytest.raises(SystemExit) as result: auth.main()
    assert result.value.code == 2
