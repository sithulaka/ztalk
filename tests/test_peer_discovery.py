"""Tests for peer discovery thread safety (Issue #14) and network manager (Issues #10, #17)."""
import os
import sys
import threading
import re
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPeersLock:
    """Issue #14: Thread-safe access to peers dict."""

    def test_peers_lock_exists(self):
        from core.peer_discovery import PeerDiscovery
        # Verify the _peers_lock is defined in __init__
        import inspect
        source = inspect.getsource(PeerDiscovery.__init__)
        assert '_peers_lock' in source, "PeerDiscovery.__init__ should create _peers_lock"
        assert 'threading.Lock()' in source, "_peers_lock should be a threading.Lock()"

    def test_peers_access_uses_lock(self):
        """Key methods should use _peers_lock."""
        from core.peer_discovery import PeerDiscovery
        import inspect
        for method_name in ['get_all_peers', 'get_active_peers', 'get_peer']:
            method = getattr(PeerDiscovery, method_name, None)
            if method:
                source = inspect.getsource(method)
                assert '_peers_lock' in source, f"{method_name} should use _peers_lock"


class TestNetworkManagerValidation:
    """Issue #10: Interface name validation and no shell=True."""

    def test_no_shell_true_in_source(self):
        from core import network_manager
        import inspect
        source = inspect.getsource(network_manager)
        # shell=True should not appear (except possibly in comments)
        lines = [l for l in source.split('\n') if 'shell=True' in l and not l.strip().startswith('#')]
        assert len(lines) == 0, f"Found shell=True in network_manager.py: {lines}"

    def test_validate_interface_name_exists(self):
        from core.network_manager import NetworkManager
        assert hasattr(NetworkManager, '_validate_interface_name'), \
            "NetworkManager should have _validate_interface_name"

    def test_validate_interface_rejects_special_chars(self):
        from core.network_manager import NetworkManager
        with pytest.raises(ValueError):
            NetworkManager._validate_interface_name("eth0; rm -rf /")

    def test_validate_interface_rejects_spaces(self):
        from core.network_manager import NetworkManager
        with pytest.raises(ValueError):
            NetworkManager._validate_interface_name("eth 0")

    def test_validate_interface_accepts_valid_names(self):
        from core.network_manager import NetworkManager
        # Should not raise
        for name in ['eth0', 'wlan0', 'enp0s3', 'docker_bridge', 'veth-123']:
            NetworkManager._validate_interface_name(name)


class TestBareExcepts:
    """Issue #17: No bare except Exception blocks."""

    def test_no_bare_except_exception_in_network_manager(self):
        from core import network_manager
        import inspect
        source = inspect.getsource(network_manager)
        # Count lines with bare "except Exception:" or "except Exception as e:"
        # that don't have logger.exception nearby
        import re
        bare_excepts = re.findall(r'except\s+Exception[\s:]', source)
        # There should be zero bare Exception catches
        assert len(bare_excepts) == 0, \
            f"Found {len(bare_excepts)} bare 'except Exception' in network_manager.py"
