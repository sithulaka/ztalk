"""Shared test fixtures for ZTalk tests."""
import os
import sys
import pytest
import secrets

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set API token before importing app
os.environ.setdefault('ZTALK_LOG_LEVEL', 'WARNING')


@pytest.fixture
def flask_app():
    """Create a Flask test app with a fresh ZTalk backend."""
    import app as app_module
    app_module.app.config['TESTING'] = True
    # Clear CSRF tokens between tests
    app_module.csrf_tokens.clear()
    return app_module


@pytest.fixture
def client(flask_app):
    """Flask test client."""
    return flask_app.app.test_client()


@pytest.fixture
def auth_header(flask_app):
    """Authorization header with valid Bearer token."""
    return {'Authorization': f'Bearer {flask_app.API_TOKEN}'}


@pytest.fixture
def csrf_token(client, auth_header):
    """Get a valid CSRF token."""
    resp = client.get('/api/csrf-token', headers=auth_header)
    return resp.get_json()['csrfToken']


@pytest.fixture
def auth_csrf_headers(auth_header, csrf_token):
    """Headers with both auth and CSRF tokens."""
    return {**auth_header, 'X-CSRF-Token': csrf_token, 'Content-Type': 'application/json'}
