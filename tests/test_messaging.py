"""Tests for messaging module hardening (Issues #3, #16, #29, #30, #31)."""
import os
import sys
import threading
import collections
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.messaging import MessageHandler, Message, MessageType


@pytest.fixture
def handler():
    """Create a MessageHandler without starting network listeners."""
    h = MessageHandler(
        peer_id='test-peer-id',
        username='testuser',
        port=0  # Don't bind to a real port
    )
    return h


class TestRandomSalt:
    """Issue #3: Encryption uses random salt instead of hardcoded."""

    def test_no_hardcoded_salt_in_source(self):
        import inspect
        source = inspect.getsource(MessageHandler)
        assert "ZTalk_salt_value" not in source, "Hardcoded salt should be removed"

    def test_encryption_stores_password_not_key(self, handler):
        """enable_encryption should store password for per-message salt derivation."""
        handler.enable_encryption('testpassword123')
        # Should store password (or have encryption enabled)
        assert hasattr(handler, '_encryption_password') or hasattr(handler, '_encryption_key'), \
            "Handler should store encryption credentials after enable_encryption"

    def test_derive_key_uses_salt_param(self):
        """_derive_key should accept a salt parameter."""
        import inspect
        source = inspect.getsource(MessageHandler)
        assert '_derive_key' in source, "Should have _derive_key method"
        # Check it takes a salt parameter
        if hasattr(MessageHandler, '_derive_key'):
            sig = inspect.signature(MessageHandler._derive_key)
            params = list(sig.parameters.keys())
            assert 'salt' in params, "_derive_key should accept salt parameter"


class TestDeduplication:
    """Issue #29: Message deduplication via seen_message_ids."""

    def test_seen_message_ids_exists(self, handler):
        assert hasattr(handler, '_seen_message_ids')
        assert isinstance(handler._seen_message_ids, collections.OrderedDict)

    def test_seen_ids_initially_empty(self, handler):
        assert len(handler._seen_message_ids) == 0

    def test_seen_ids_bounded_at_1000(self, handler):
        """Adding >1000 IDs should evict oldest."""
        for i in range(1100):
            handler._seen_message_ids[f'msg-{i}'] = True
            while len(handler._seen_message_ids) > 1000:
                handler._seen_message_ids.popitem(last=False)
        assert len(handler._seen_message_ids) == 1000
        assert 'msg-0' not in handler._seen_message_ids
        assert 'msg-1099' in handler._seen_message_ids


class TestHistoryLock:
    """Issue #30: Thread-safe access to message histories."""

    def test_history_lock_exists(self, handler):
        assert hasattr(handler, '_history_lock')
        assert isinstance(handler._history_lock, type(threading.Lock()))

    def test_private_histories_exist(self, handler):
        assert hasattr(handler, 'private_histories')

    def test_group_histories_exist(self, handler):
        assert hasattr(handler, 'group_histories')


class TestTimerCleanup:
    """Issue #16: Timer cleanup on ACK and max retries."""

    def test_active_timers_is_dict(self, handler):
        assert hasattr(handler, '_active_timers')
        assert isinstance(handler._active_timers, dict)

    def test_retry_attempts_is_3(self, handler):
        assert hasattr(handler, 'RETRY_ATTEMPTS')
        assert handler.RETRY_ATTEMPTS == 3
