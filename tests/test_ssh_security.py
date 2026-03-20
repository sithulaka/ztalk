"""Tests for SSH security improvements (Issues #4, #5, #53)."""
import os
import sys
import logging
import inspect
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHostKeyPolicy:
    """Issue #4: Custom ZTalkHostKeyPolicy replaces AutoAddPolicy."""

    def test_ztalk_host_key_policy_exists(self):
        from core.ssh_manager import ZTalkHostKeyPolicy
        policy = ZTalkHostKeyPolicy()
        assert hasattr(policy, 'known_hosts_path')
        assert '.ztalk/known_hosts' in policy.known_hosts_path

    def test_known_hosts_path_is_in_ztalk_dir(self):
        from core.ssh_manager import ZTalkHostKeyPolicy
        policy = ZTalkHostKeyPolicy()
        assert os.path.expanduser('~') in policy.known_hosts_path

    def test_no_auto_add_policy_in_ssh_manager(self):
        from core import ssh_manager
        source = inspect.getsource(ssh_manager)
        # AutoAddPolicy should not be used (except in comments/strings)
        code_lines = [l for l in source.split('\n')
                      if 'AutoAddPolicy' in l
                      and not l.strip().startswith('#')
                      and not l.strip().startswith('"')
                      and not l.strip().startswith("'")]
        assert len(code_lines) == 0, \
            f"AutoAddPolicy still used in ssh_manager.py: {code_lines}"

    def test_no_auto_add_policy_in_ssh_utils(self):
        from utils import ssh_utils
        source = inspect.getsource(ssh_utils)
        code_lines = [l for l in source.split('\n')
                      if 'AutoAddPolicy' in l
                      and not l.strip().startswith('#')
                      and not l.strip().startswith('"')
                      and not l.strip().startswith("'")]
        assert len(code_lines) == 0, \
            f"AutoAddPolicy still used in ssh_utils.py: {code_lines}"

    def test_policy_has_missing_host_key_method(self):
        from core.ssh_manager import ZTalkHostKeyPolicy
        policy = ZTalkHostKeyPolicy()
        assert hasattr(policy, 'missing_host_key')
        assert callable(policy.missing_host_key)


class TestPasswordClearing:
    """Issue #5: SSH passwords cleared after connection."""

    def test_password_cleared_in_connect(self):
        """The connect() method should set self.password = None after success."""
        from core.ssh_manager import SSHConnection
        source = inspect.getsource(SSHConnection.connect)
        assert 'self.password = None' in source, \
            "connect() should clear password after successful connection"

    def test_to_dict_omits_password(self):
        from core.ssh_manager import SSHConnection
        conn = SSHConnection(
            connection_id='test-id',
            host='example.com',
            port=22,
            username='user',
            password='secret123'
        )
        d = conn.to_dict()
        assert 'password' not in d, "to_dict() should not include password"
        assert d['host'] == 'example.com'
        assert d['username'] == 'user'


class TestSSHAuditLogging:
    """Issue #53: Audit logging for SSH operations."""

    def test_connect_has_logging(self):
        from core.ssh_manager import SSHConnection
        source = inspect.getsource(SSHConnection.connect)
        assert 'logger.info' in source, "connect() should have audit logging"
        # Should not log password
        assert 'password' not in source.split('logger.info')[1].split('\n')[0].lower() or \
               'self.password' not in source.split('logger.info')[1].split('\n')[0], \
            "Audit log should not contain password"

    def test_disconnect_has_logging(self):
        from core.ssh_manager import SSHConnection
        source = inspect.getsource(SSHConnection.disconnect)
        assert 'logger.info' in source, "disconnect() should have audit logging"
