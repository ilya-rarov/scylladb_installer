#!/usr/bin/env python3

from controller import ControllerDataBase, InstallationState
from concurrent.futures.thread import ThreadPoolExecutor
from enum import Enum, unique
import sys
from time import sleep
from datetime import datetime
from ssh_interface.ssh import SSHConnection
import logging
from config import ConfigObject
from jinja2 import FileSystemLoader, Environment, select_autoescape

env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape()
)


class CommandExecutionError(Exception):
    pass


class OSIdentificationError(Exception):
    pass


@unique
class Status(Enum):
    OS_IDENTIFIED = 'OS identified'
    SCYLLA_INSTALLED = 'Scylla installed'
    SCYLLA_YAML_CREATED = 'scylla.yaml created'
    SCYLLA_CONFIGURED = 'Scylla configured'
    SCYLLA_STARTED = 'Scylla started'
    SCYLLA_STRESSED = 'cassandra-stress completed'


@unique
class SupportedDistributions(Enum):
    UBUNTU_16 = {'ID': 'ubuntu', 'VERSION_ID': '16.04'}
    UBUNTU_18 = {'ID': 'ubuntu', 'VERSION_ID': '18.04'}
    UBUNTU_20 = {'ID': 'ubuntu', 'VERSION_ID': '20.04'}
    CENTOS_7 = {'ID': 'centos', 'VERSION_ID': '7'}
    CENTOS_8 = {'ID': 'centos', 'VERSION_ID': '8'}
    DEBIAN_9 = {'ID': 'debian', 'VERSION_ID': '9'}
    DEBIAN_10 = {'ID': 'debian', 'VERSION_ID': '10'}

    def get_name(self):
        return f"{self.value['ID'].capitalize()} {self.value['VERSION_ID']}"


class ParallelObject:
    def __init__(self, timeout=1800):
        self._timeout = timeout

    @property
    def timeout(self):
        return self._timeout

    def run(self, functions):
        futures = []
        with ThreadPoolExecutor(max_workers=len(functions)) as executor:
            for fn in functions:
                future = executor.submit(fn)
                futures.append(future)
            for future in futures:
                try:
                    future.result(timeout=self.timeout)
                except Exception:
                    raise


class ScyllaInstaller:
    def __init__(self, installer_db, log_config, host, port, username, password, db_version, cluster_name, seed_node,
                 os_version, installation_id):
        self._installer_db = installer_db
        self._host = host
        self._port = port
        self._username = username
        self._db_version = db_version
        self._cluster_name = cluster_name
        self._seed_node = seed_node
        self._os_version = os_version
        self._installation_id = installation_id
        self._ssh_connection = SSHConnection(host=host, port=port, user=username, password=password)
        log_level = getattr(logging, log_config['log_level'].upper(), None)
        file_handler = logging.FileHandler(f"{log_config['log_root_dir']}/{host}_scylla_installation_"
                                           f"{datetime.now().strftime('%d%m%Y_%H%M%S')}.log")
        formatter = logging.Formatter("[%(asctime)s] - %(levelname)s: %(message)s")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        self._installation_logger = logging.getLogger(f'{host}_scylla_installation')
        self._installation_logger.addHandler(file_handler)
        self._installation_logger.setLevel(log_level)

    @property
    def host(self):
        return self._host

    def get_os_version(self):
        shell_command = 'cat /etc/os-release'
        os_release_dict = {}
        stdout, stderr, exit_code = self._execute_shell_command(command_to_execute=shell_command)
        for line in stdout:
            os_release_parameter = line.strip().split('=')
            os_release_dict[os_release_parameter[0]] = os_release_parameter[1].replace('"', '')
        for os_type in SupportedDistributions:
            if os_type.value['ID'] == os_release_dict['ID'] \
                    and os_type.value['VERSION_ID'] == os_release_dict['VERSION_ID']:
                linux_distribution = os_type.get_name()
                return linux_distribution
        raise OSIdentificationError(f"OS type of {os_release_dict['ID']} {os_release_dict['VERSION_ID']} "
                                    "has not been recognized")

    def install(self):
        self._set_global_status(global_status_value=InstallationState.IN_PROGRESS.value)
        self._installation_logger.info(msg=f'Installation on {self._host} started.')
        try:
            self._os_version = self.get_os_version()
        except Exception as e:
            self._set_global_status(global_status_value=InstallationState.FAILED.value)
            self._installation_logger.error(msg=f'Installation on {self._host} failed! Error message: {e}')
            raise e
        else:
            value_to_update = {'os_version': self._os_version}
            self._installer_db.update_data(table='nodes', condition=f'host = \'{self._host}\'', **value_to_update)
            self._add_new_status(status=Status.OS_IDENTIFIED.value)
            self._installation_logger.info(msg=f'Linux distribution on {self._host} is {self._os_version}.')
        try:
            self._install_on_node()
        except Exception as e:
            self._set_global_status(global_status_value=InstallationState.FAILED.value)
            self._installation_logger.error(msg=f'Installation on {self._host} failed! Error message: {e}')
            raise e
        else:
            self._add_new_status(status=Status.SCYLLA_INSTALLED.value)
            self._installation_logger.info(msg=f'Scylla binaries installed on {self._host}.')
        try:
            self._execute_post_install()
        except Exception as e:
            self._set_global_status(global_status_value=InstallationState.FAILED.value)
            self._installation_logger.error(msg=f'Installation on {self._host} failed! Error message: {e}')
            raise e
        self._set_global_status(global_status_value=InstallationState.SUCCEEDED.value)
        self._installation_logger.info(msg=f'Installation on {self._host} completed.')

    def _install_on_node(self):
        if 'UBUNTU' in self._os_version.upper():
            self._install_on_ubuntu()
        elif 'CENTOS' in self._os_version.upper():
            self._install_on_centos()
        elif 'DEBIAN' in self._os_version.upper():
            self._install_on_debian()

    def _install_on_ubuntu(self):
        if '16.04' in self._os_version:
            shell_command = 'apt-get install -y apt-transport-https'
            self._execute_shell_command(command_to_execute=shell_command)
        shell_command = 'apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 5e08fbd8b5d6ec9c'
        self._execute_shell_command(command_to_execute=shell_command)
        shell_command = ('curl -L --output /etc/apt/sources.list.d/scylla.list http://'
                         f'downloads.scylladb.com/deb/ubuntu/scylla-{self._db_version}-$(lsb_release -s -c).list')
        self._execute_shell_command(command_to_execute=shell_command)
        shell_command = 'apt-get update'
        self._execute_shell_command(command_to_execute=shell_command)
        shell_command = 'apt-get install -y scylla'
        self._execute_shell_command(command_to_execute=shell_command)
        if '18.04' in self._os_version or '20.04' in self._os_version:
            shell_command = 'apt-get install -y openjdk-8-jre-headless'
            self._execute_shell_command(command_to_execute=shell_command)
            shell_command = 'update-java-alternatives --jre-headless -s java-1.8.0-openjdk-amd64'
            self._execute_shell_command(command_to_execute=shell_command)

    def _install_on_centos(self):
        shell_command = 'yum remove -y abrt'
        self._execute_shell_command(command_to_execute=shell_command)
        shell_command = 'yum install -y epel-release'
        self._execute_shell_command(command_to_execute=shell_command)
        shell_command = ('curl -o /etc/yum.repos.d/scylla.repo -L http://repositories.scylladb.com/scylla/repo/'
                         f'a3df46bd-e48a-4a51-bef7-ccbdc819a9c5/centos/scylladb-{self._db_version}.repo')
        self._execute_shell_command(command_to_execute=shell_command)
        shell_command = 'yum install -y scylla'
        self._execute_shell_command(command_to_execute=shell_command)

    def _install_on_debian(self):
        shell_command = 'apt-get update'
        self._execute_shell_command(command_to_execute=shell_command)
        shell_command = 'apt-get install -y curl gnupg'
        self._execute_shell_command(command_to_execute=shell_command)
        if '9' in self._os_version:
            shell_command = 'apt-get install -y apt-transport-https dirmngr'
            self._execute_shell_command(command_to_execute=shell_command)
            shell_command = ('curl -L --output /etc/apt/sources.list.d/scylla.list http://repositories.scylladb.com/'
                             f'scylla/repo/deb/debian/scylladb-{self._db_version}-$(lsb_release -s -c).list')
            self._execute_shell_command(command_to_execute=shell_command)
        else:
            shell_command = ('curl -L --output /etc/apt/sources.list.d/scylla.list http://downloads.scylladb.com/deb/'
                             f'debian/scylla-{self._db_version}-$(lsb_release -c -s).list')
            self._execute_shell_command(command_to_execute=shell_command)
        shell_command = 'apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 5e08fbd8b5d6ec9c'
        self._execute_shell_command(command_to_execute=shell_command)
        shell_command = 'apt-get update'
        self._execute_shell_command(command_to_execute=shell_command)
        shell_command = 'apt-get install -y scylla'
        self._execute_shell_command(command_to_execute=shell_command)

    def _execute_post_install(self):
        # scylla.yaml generator
        scylla_params = {'cluster_name': self._cluster_name,
                         'seed_node': f'"{self._seed_node}"',
                         'listen_address': self._host,
                         'rpc_address': self._host}
        template = env.get_template('./scylla_yaml/scylla.yaml')
        scylla_yaml = template.render(scylla_params).replace('"', '\\"')
        shell_command = 'chmod o+w /etc/scylla/scylla.yaml'
        self._execute_shell_command(command_to_execute=shell_command)
        self._installation_logger.debug(msg='Granted write permission on "scylla.yaml" to other users '
                                            f'on {self._host}.')
        shell_command = f'echo "{scylla_yaml}" > /etc/scylla/scylla.yaml'
        self._execute_shell_command(command_to_execute=shell_command)
        self._add_new_status(status=Status.SCYLLA_YAML_CREATED.value)
        self._installation_logger.info(msg=f'File "scylla.yaml" successfully created on {self._host}.')
        shell_command = 'chmod o-w /etc/scylla/scylla.yaml'
        self._execute_shell_command(command_to_execute=shell_command)
        self._installation_logger.debug(msg='Revoked write permission on "scylla.yaml" from other users '
                                            f'on {self._host}.')
        # getting network interface name
        shell_command = 'ls /sys/class/net/ | grep -E \'eno|ens|enp|enx|wlo|wls|wnp|wnx\''
        stdout, stderr, exit_code = self._execute_shell_command(command_to_execute=shell_command)
        nic_name = stdout[0].strip()
        self._installation_logger.info(msg=f'Detected network interface: {nic_name}')
        # run of "scylla_setup"
        shell_command = f'scylla_setup --no-raid-setup --nic {nic_name} --io-setup 1 --no-rsyslog-setup'
        self._execute_shell_command(command_to_execute=shell_command)
        self._add_new_status(status=Status.SCYLLA_CONFIGURED.value)
        self._installation_logger.info(msg=f'Command "scylla_setup" completed successfully on {self._host}.')
        # starting up Scylla service
        if self._host != self._seed_node:
            sleep(120)
        shell_command = 'systemctl start scylla-server.service'
        self._execute_shell_command(command_to_execute=shell_command)
        self._add_new_status(status=Status.SCYLLA_STARTED.value)
        self._installation_logger.info(msg=f'Scylla service started successfully on {self._host}.')
        # nodetool status check
        sleep(120)
        shell_command = 'nodetool status'
        stdout, stderr, exit_code = self._execute_shell_command(command_to_execute=shell_command)
        nodetool_status = '\n'.join(stdout)
        self._installation_logger.debug(msg=f'Result of "nodetool status":\n{nodetool_status}')
        # run of "cassandra-stress"
        shell_command = f"cassandra-stress write -mode cql3 native -node {self._host} -rate 'threads=2 " \
                        f"throttle=500/s' -pop seq=1..10000 &> ~/cassandra-stress.log || true"
        self._execute_shell_command(command_to_execute=shell_command)
        self._add_new_status(status=Status.SCYLLA_STRESSED.value)
        self._installation_logger.info(msg='Command "cassandra-stress" completed. '
                                           'Check result in ~/cassandra-stress.log.')

    def _add_new_status(self, status):
        self._installer_db.insert_data(table='statuses', columns=('status_name', 'installation_id'),
                                       values=f'(\'{status}\', \'{self._installation_id}\')')

    def _execute_shell_command(self, command_to_execute):
        stdout, stderr, exit_code = self._ssh_connection.execute_command(command=command_to_execute)
        if exit_code != 0:
            if stderr:
                error_msg = '\n'.join(stderr)
            else:
                error_msg = '\n'.join(stdout)
            self._installation_logger.error(msg=(f'Execution of command "{command_to_execute}" failed! '
                                                 f'Error message:\n{error_msg}'))
            raise CommandExecutionError(f'Execution of command "{command_to_execute}" failed!')
        self._installation_logger.debug(msg=f'Execution of command "{command_to_execute}" succeeded!')
        return stdout, stderr, exit_code

    def _set_global_status(self, global_status_value):
        if global_status_value == InstallationState.FAILED.value or \
                global_status_value == InstallationState.SUCCEEDED.value:
            value_to_update = {'global_status': global_status_value,
                               'finish_timestamp': 'get_system_timestamp'}
        else:
            value_to_update = {'global_status': global_status_value}
        self._installer_db.update_data(table='installations', condition=f'id = {self._installation_id}',
                                       **value_to_update)


def setup_logging(log_root_dir, log_level):
    level_to_set = getattr(logging, log_level.upper(), None)
    file_handler = logging.FileHandler(f"{log_root_dir}/installer.log")
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    root_formatter = logging.Formatter("[%(asctime)s] - %(module)s - %(levelname)s: %(message)s")
    installer_formatter = logging.Formatter("[%(asctime)s] - %(levelname)s: %(message)s")
    file_handler.setFormatter(installer_formatter)
    file_handler.setLevel(level_to_set)
    stdout_handler.setFormatter(root_formatter)
    stdout_handler.setLevel(level_to_set)
    root_logger = logging.getLogger()
    root_logger.addHandler(stdout_handler)
    root_logger.setLevel(level_to_set)
    installer_logger = logging.getLogger('installer')
    installer_logger.addHandler(file_handler)
    installer_logger.setLevel(level_to_set)
    return installer_logger


if __name__ == '__main__':
    database = ControllerDataBase().instance
    config = ConfigObject(config_path='./config/installer.conf')
    log_configuration = config.log_config
    main_log = setup_logging(**log_configuration)
    while True:
        installation_list = []
        functions_list = []
        hosts_list = []
        main_log.debug(msg='Looking for new installations...')
        query_data = {'columns': 'nodes.host, nodes.port, nodes.username, nodes.password, nodes.db_version, \
                       nodes.cluster_name, nodes.seed_node, nodes.os_version, installations.id as installation_id',
                      'join_installations': 'yes', 'join_statuses': 'no',
                      'filter': f'installations.global_status = \'{InstallationState.NEW.value}\''}
        nodes_list = database.select_data(query_params=query_data, columns=('host', 'port', 'username', 'password',
                                                                            'db_version', 'cluster_name', 'seed_node',
                                                                            'os_version', 'installation_id'))
        main_log.debug(msg=f'Number of found installations: {len(nodes_list)}')
        if nodes_list:
            for node in nodes_list:
                installation_list.append(ScyllaInstaller(installer_db=database, log_config=log_configuration, **node))
            main_log.info(msg=f"Number of nodes to install: {len(installation_list)}")
            parallel_object = ParallelObject()
            for installation in installation_list:
                functions_list.append(installation.install)
                hosts_list.append(installation.host)
            main_log.info(msg=f"Parallel installation threads will be created for nodes: {', '.join(hosts_list)}")
            try:
                parallel_object.run(functions=functions_list)
            except Exception as ex:
                main_log.error(msg=f'Error in parallel execution: {ex}')
        sleep(3)
