from controller import ControllerDataBase, InstallationState
from concurrent.futures.thread import ThreadPoolExecutor
from enum import Enum, unique
from time import sleep
from ssh_interface.ssh import SSHConnection


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
    def __init__(self, items, timeout=10, ignore_exceptions=False):
        self._items = items
        self._timeout = timeout
        self._ignore_exceptions = ignore_exceptions

    @property
    def items(self):
        return self._items

    @property
    def timeout(self):
        return self._timeout

    @property
    def ignore_exceptions(self):
        return self._ignore_exceptions

    def run(self, fn):
        futures = []
        results = []
        with ThreadPoolExecutor(max_workers=len(self.items)) as executor:
            for parameter in self.items:
                future = executor.submit(fn, parameter)
                futures.append(future)
            for future in futures:
                try:
                    results.append(future.result(timeout=self.timeout))
                except Exception:
                    if self.ignore_exceptions:
                        pass
                    else:
                        raise
        return results


class ScyllaInstaller:
    def __init__(self, installer_db, host, port, username, password, db_version, cluster_name, seed_node, os_version,
                 installation_id):
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

    @property
    def host(self):
        return self._host

    def get_os_version(self):
        shell_command = 'cat /etc/os-release'
        stdout, stderr, exit_code = self._ssh_connection.execute_command(command=shell_command)
        os_release_dict = {}
        linux_distribution = ''
        if exit_code == 0:
            for line in stdout:
                os_release_parameter = line.strip().split('=')
                os_release_dict[os_release_parameter[0]] = os_release_parameter[1].replace('"', '')
            for os_type in SupportedDistributions:
                if os_type.value['ID'] == os_release_dict['ID'] \
                        and os_type.value['VERSION_ID'] == os_release_dict['VERSION_ID']:
                    linux_distribution = os_type.get_name()
                    break
                else:
                    pass
        else:
            pass
        return linux_distribution

    def install(self):
        value_to_update = {'global_status': InstallationState.IN_PROGRESS.value}
        self._installer_db.update_data(table='installations', condition=f'id = {self._installation_id}',
                                       **value_to_update)
        self._os_version = self.get_os_version()
        value_to_update = {'os_version': self._os_version}
        self._installer_db.update_data(table='nodes', condition=f'host = \'{self._host}\'',
                                       **value_to_update)
        self.set_status(status='OS identified')

    def set_status(self, status):
        self._installer_db.insert_data(table='statuses', columns=('status_name', 'installation_id'),
                                       values=f'(\'{status}\', \'{self._installation_id}\')')


if __name__ == '__main__':
    database = ControllerDataBase().instance
    installation_list = []
    query_data = {'columns': 'nodes.host, nodes.port, nodes.username, nodes.password, nodes.db_version, \
                   nodes.cluster_name, nodes.seed_node, nodes.os_version, installations.id as installation_id',
                  'join_installations': 'yes', 'join_statuses': 'no',
                  'filter': f'installations.global_status = \'{InstallationState.NEW.value}\''}
    nodes_list = database.select_data(query_params=query_data, columns=('host', 'port', 'username', 'password',
                                                                        'db_version', 'cluster_name', 'seed_node',
                                                                        'os_version', 'installation_id'))
    if nodes_list:
        for node in nodes_list:
            installation_list.append(ScyllaInstaller(installer_db=database, **node))
        for inst in installation_list:
            inst.install()
