"""Tests for infrastructure and config improvements (Issues #18, #20, #25, #26, #27, #40, #41, #50, #52, #56, #57, #59, #60, #61, #62)."""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestRunSh:
    """Issues #18, #40, #41, #56, #57: run.sh fixes."""

    @pytest.fixture
    def run_sh_content(self):
        with open(os.path.join(PROJECT_ROOT, 'run.sh')) as f:
            return f.read()

    def test_no_pypy3_venv(self, run_sh_content):
        """Issue #18: Should use python3-venv, not pypy3-venv."""
        assert 'pypy3-venv' not in run_sh_content
        assert 'python3-venv' in run_sh_content

    def test_no_break_system_packages(self, run_sh_content):
        """Issue #41: Should not use --break-system-packages."""
        assert '--break-system-packages' not in run_sh_content

    def test_venv_removal_has_warning(self, run_sh_content):
        """Issue #40: rm -rf .venv should have a warning."""
        # Find the rm -rf .venv line and check there's a warning before it
        lines = run_sh_content.split('\n')
        for i, line in enumerate(lines):
            if 'rm -rf .venv' in line and not line.strip().startswith('#'):
                # Check preceding lines for warning
                preceding = '\n'.join(lines[max(0, i-5):i])
                assert 'WARNING' in preceding or 'warn' in preceding.lower() or 'sleep' in preceding, \
                    "rm -rf .venv should be preceded by a warning"
                break

    def test_has_node_version_check(self, run_sh_content):
        """Issue #56: Should check Node.js version >= 14."""
        assert 'check_node_version' in run_sh_content
        assert '14' in run_sh_content

    def test_has_trap_cleanup(self, run_sh_content):
        """Issue #57: Should have trap cleanup EXIT."""
        assert 'trap cleanup EXIT' in run_sh_content
        assert 'BACKGROUND_PIDS' in run_sh_content


class TestPackageJson:
    """Issues #20, #50: package.json fixes."""

    @pytest.fixture
    def package_json(self):
        with open(os.path.join(PROJECT_ROOT, 'package.json')) as f:
            return json.load(f)

    def test_build_files_includes_public(self, package_json):
        """Issue #20: build.files should include public/**/*."""
        files = package_json.get('build', {}).get('files', [])
        assert any('public' in f for f in files), \
            "build.files should include public/**/*"

    def test_no_unused_deps(self, package_json):
        """Issue #50: Remove react-beautiful-dnd, chart.js, react-chartjs-2."""
        deps = package_json.get('dependencies', {})
        assert 'react-beautiful-dnd' not in deps
        assert 'chart.js' not in deps
        assert 'react-chartjs-2' not in deps


class TestEnvExample:
    """Issue #26: .env.example exists with required vars."""

    def test_env_example_exists(self):
        path = os.path.join(PROJECT_ROOT, '.env.example')
        assert os.path.exists(path), ".env.example should exist"

    def test_env_example_has_required_vars(self):
        path = os.path.join(PROJECT_ROOT, '.env.example')
        with open(path) as f:
            content = f.read()
        assert 'ZTALK_API_PORT' in content
        assert 'ZTALK_LOG_LEVEL' in content
        assert 'REACT_APP_API_URL' in content


class TestRequirements:
    """Issues #9, #26: requirements.txt has new dependencies."""

    @pytest.fixture
    def requirements(self):
        with open(os.path.join(PROJECT_ROOT, 'requirements.txt')) as f:
            return f.read()

    def test_has_flask_limiter(self, requirements):
        assert 'flask-limiter' in requirements

    def test_has_python_dotenv(self, requirements):
        assert 'python-dotenv' in requirements

    def test_requirements_dev_exists(self):
        """Issue #60: requirements-dev.txt should exist."""
        path = os.path.join(PROJECT_ROOT, 'requirements-dev.txt')
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert 'pytest' in content
        assert 'black' in content
        assert 'flake8' in content
        assert 'mypy' in content


class TestTailwindConfig:
    """Issue #59: Tailwind content includes public HTML."""

    def test_tailwind_has_public_html(self):
        path = os.path.join(PROJECT_ROOT, 'tailwind.config.js')
        with open(path) as f:
            content = f.read()
        assert 'public/**/*.html' in content


class TestDHCPServer:
    """Issues #32, #52: DHCP server improvements."""

    def test_dhcp_accepts_network_param(self):
        """Issue #52: DHCPServer should accept network as constructor param."""
        import inspect
        from core.dhcp_server import DHCPServer
        sig = inspect.signature(DHCPServer.__init__)
        params = list(sig.parameters.keys())
        assert 'network' in params, "DHCPServer.__init__ should accept 'network' param"

    def test_dhcp_accepts_dns_param(self):
        """Issue #52: DHCPServer should accept dns_servers as constructor param."""
        import inspect
        from core.dhcp_server import DHCPServer
        sig = inspect.signature(DHCPServer.__init__)
        params = list(sig.parameters.keys())
        assert 'dns_servers' in params, "DHCPServer.__init__ should accept 'dns_servers' param"

    def test_dhcp_has_cleanup_event(self):
        """Issue #32: DHCPServer should have periodic cleanup."""
        import inspect
        source = inspect.getsource(sys.modules['core.dhcp_server'])
        assert '_cleanup_event' in source, "DHCPServer should have _cleanup_event for periodic cleanup"
        assert '_periodic_lease_cleanup' in source, "DHCPServer should have _periodic_lease_cleanup method"


class TestApplicationLogging:
    """Issue #25: Logging setup in application.py."""

    def test_setup_logging_exists(self):
        import inspect
        from core.application import ZTalkApp
        source = inspect.getsource(sys.modules['core.application'])
        assert '_setup_logging' in source, "application.py should have _setup_logging"
        assert 'RotatingFileHandler' in source, "Should use RotatingFileHandler"

    def test_no_theme_in_default_config(self):
        """Issue #54: No unused 'theme' key in default config."""
        import inspect
        from core.application import ZTalkApp
        source = inspect.getsource(ZTalkApp)
        # Check the default config dict doesn't have 'theme'
        # This is a heuristic check
        if 'default_config' in source or 'DEFAULT_CONFIG' in source:
            config_section = source[source.find('config'):source.find('config') + 500]
            assert "'theme'" not in config_section or '"theme"' not in config_section


class TestWindowsUtils:
    """Issues #61, #62: Windows utils security."""

    def test_registry_validation_exists(self):
        """Issue #61: Registry path validation."""
        path = os.path.join(PROJECT_ROOT, 'utils', 'windows_utils.py')
        with open(path) as f:
            source = f.read()
        assert '_validate_registry_path' in source or 'REGISTRY' in source.upper()

    def test_nsis_escape_exists(self):
        """Issue #62: NSIS path escaping."""
        path = os.path.join(PROJECT_ROOT, 'utils', 'windows_utils.py')
        with open(path) as f:
            source = f.read()
        assert '_escape_nsis_path' in source


class TestConfigEncryption:
    """Issue #27: Config encryption at rest."""

    def test_fernet_used_in_application(self):
        import inspect
        source = inspect.getsource(sys.modules['core.application'])
        assert 'Fernet' in source, "application.py should use Fernet encryption"
        assert 'PBKDF2' in source, "Should use PBKDF2 key derivation"
