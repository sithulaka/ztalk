"""Tests for API authentication, CSRF protection, and rate limiting (Issues #1, #2, #9, #49)."""
import json
import pytest


class TestAuth:
    """Issue #1: JWT-style Bearer token auth on all endpoints."""

    def test_health_endpoint_no_auth_required(self, client):
        resp = client.get('/api')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['name'] == 'ZTalk API'
        assert data['status'] in ('running', 'initializing')

    def test_protected_endpoint_returns_401_without_token(self, client):
        resp = client.get('/api/peers/active')
        assert resp.status_code == 401
        assert resp.get_json()['error'] == 'Unauthorized'

    def test_protected_endpoint_returns_401_with_bad_token(self, client):
        resp = client.get('/api/peers/active', headers={'Authorization': 'Bearer bad-token'})
        assert resp.status_code == 401

    def test_protected_endpoint_returns_401_with_wrong_scheme(self, client):
        resp = client.get('/api/peers/active', headers={'Authorization': 'Basic abc123'})
        assert resp.status_code == 401

    def test_protected_endpoint_succeeds_with_valid_token(self, client, auth_header):
        resp = client.get('/api/user/username', headers=auth_header)
        # 200 or 500 (if app not initialized), but NOT 401
        assert resp.status_code != 401

    def test_all_get_endpoints_require_auth(self, client):
        protected_gets = [
            '/api/peers/active',
            '/api/peers/all',
            '/api/user/username',
            '/api/messages/history',
            '/api/ssh/connections',
            '/api/ssh/profiles',
            '/api/network/interfaces',
            '/api/dhcp/status',
            '/api/dhcp/leases',
            '/api/csrf-token',
        ]
        for path in protected_gets:
            resp = client.get(path)
            assert resp.status_code == 401, f"{path} should require auth"

    def test_api_token_is_random_and_long(self, flask_app):
        token = flask_app.API_TOKEN
        assert len(token) >= 32
        # Should be URL-safe base64 characters
        assert all(c.isalnum() or c in '-_' for c in token)


class TestCSRF:
    """Issue #49: CSRF token protection on state-changing endpoints."""

    def test_csrf_token_endpoint_returns_token(self, client, auth_header):
        resp = client.get('/api/csrf-token', headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'csrfToken' in data
        assert len(data['csrfToken']) >= 32

    def test_post_without_csrf_returns_403(self, client, auth_header):
        resp = client.post('/api/messages/broadcast',
                           headers={**auth_header, 'Content-Type': 'application/json'},
                           data=json.dumps({'content': 'test'}))
        assert resp.status_code == 403
        assert 'CSRF' in resp.get_json()['error']

    def test_post_with_invalid_csrf_returns_403(self, client, auth_header):
        resp = client.post('/api/messages/broadcast',
                           headers={**auth_header, 'X-CSRF-Token': 'bad-token', 'Content-Type': 'application/json'},
                           data=json.dumps({'content': 'test'}))
        assert resp.status_code == 403

    def test_post_with_valid_csrf_passes_csrf_check(self, client, auth_csrf_headers):
        resp = client.post('/api/messages/broadcast',
                           headers=auth_csrf_headers,
                           data=json.dumps({'content': 'test'}))
        # Should get past CSRF (may fail on app logic with 400/500, but NOT 403)
        assert resp.status_code != 403

    def test_get_requests_dont_need_csrf(self, client, auth_header):
        resp = client.get('/api/user/username', headers=auth_header)
        assert resp.status_code != 403

    def test_delete_requires_csrf(self, client, auth_header):
        resp = client.delete('/api/messages/clear', headers=auth_header)
        assert resp.status_code == 403


class TestCORS:
    """Issue #2: Socket.IO CORS restricted to localhost:3000."""

    def test_socketio_cors_not_wildcard(self, flask_app):
        # Verify the SocketIO was created with restricted origins by checking source
        import inspect
        source = inspect.getsource(flask_app)
        assert 'cors_allowed_origins=["http://localhost:3000"]' in source
        assert 'cors_allowed_origins="*"' not in source
