from installer import ParallelObject, ScyllaInstaller, OSIdentificationError, CommandExecutionError
from ssh_interface.ssh import SSHConnection
import pytest
from time import sleep
import concurrent.futures


def long_running_thread():
    sleep(3)


@pytest.fixture()
def log_configuration():
    log_config = {'log_level': 'INFO', 'log_root_dir': ''}
    return log_config


@pytest.fixture()
def installer_object(log_configuration):
    installer_object = ScyllaInstaller(installer_db=None,
                                       log_config=log_configuration,
                                       host='my_test_host',
                                       port=3000,
                                       username='test_user',
                                       password='dGVzdF9wYXNzd29yZA==',
                                       db_version='4.4',
                                       cluster_name='test_cluster',
                                       seed_node='test_seed_node',
                                       os_version=None,
                                       installation_id=5)
    return installer_object


@pytest.fixture
def mocked_shell_command_supported_os(monkeypatch):
    monkeypatch.setattr(ScyllaInstaller, "_execute_shell_command",
                        lambda *args, **kwargs: [['ID=ubuntu', 'VERSION_ID="20.04"'], [], 0])


@pytest.fixture
def mocked_shell_command_unsupported_os(monkeypatch):
    monkeypatch.setattr(ScyllaInstaller, "_execute_shell_command",
                        lambda *args, **kwargs: [['ID=ubuntu', 'VERSION_ID="10.04"'], [], 0])


@pytest.fixture
def mocked_shell_command(monkeypatch):
    monkeypatch.setattr(SSHConnection, "execute_command",
                        lambda *args, **kwargs: [['Command executed successfully'], [], 0])


@pytest.fixture
def mocked_shell_command_with_error(monkeypatch):
    monkeypatch.setattr(SSHConnection, "execute_command",
                        lambda *args, **kwargs: [[], ['Critical error!!!'], 1])


def test_parallel_object_timeout_error():
    function_list = [long_running_thread]
    test_object = ParallelObject(timeout=2)
    with pytest.raises(expected_exception=concurrent.futures._base.TimeoutError):
        test_object.run(function_list)


def test_scylla_installer_constructor(installer_object):
    host_to_check = 'my_test_host'
    assert installer_object.host == host_to_check


def test_os_detection_positive(installer_object, mocked_shell_command_supported_os):
    os_version = installer_object.get_os_version()
    assert os_version == 'Ubuntu 20.04'


def test_os_detection_negative(installer_object, mocked_shell_command_unsupported_os):
    with pytest.raises(expected_exception=OSIdentificationError):
        installer_object.get_os_version()


def test_execute_shell_command_positive(installer_object, mocked_shell_command):
    stdout, stderr, exit_code = installer_object._execute_shell_command('echo "Hello world!"')
    assert stdout == ['Command executed successfully']
    assert exit_code == 0


def test_execute_shell_command_negative(installer_object, mocked_shell_command_with_error):
    with pytest.raises(expected_exception=CommandExecutionError):
        installer_object._execute_shell_command('rm -rf')
