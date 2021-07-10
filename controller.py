#!/usr/bin/env python3

import cherrypy
import datetime
from db_interface.sql_database_interface import MySQLDatabase
from base64 import b64encode
from enum import Enum, unique
from config import ConfigObject
from time import sleep
from jinja2 import FileSystemLoader, Environment, select_autoescape

env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape(['html', 'xml'])
)


@unique
class InstallationState(Enum):
    NEW = 'new'
    IN_PROGRESS = 'in progress'
    FAILED = 'failed'
    SUCCEEDED = 'succeeded'


class UnknownDataBaseType(Exception):
    pass


class ControllerDataBase:
    def __init__(self):
        config = ConfigObject(config_path='./config/installer.conf')
        database_config = config.db_config
        if database_config['type'] == 'mysql':
            self._instance = MySQLDatabase(user=database_config['user'],
                                           password=database_config['password'],
                                           database=database_config['database'],
                                           host=database_config['host'],
                                           port=database_config['port'],
                                           db_type=database_config['type'])
        else:
            raise UnknownDataBaseType(f"{database_config['type']} is unknown type of database")

    @property
    def instance(self):
        return self._instance


class Controller(object):
    def __init__(self):
        self._database = ControllerDataBase().instance

    @cherrypy.expose
    def index(self):
        template = env.get_template('./html/installer.html')
        return template.render()

    @cherrypy.expose
    def statistics(self):
        template = env.get_template('./html/statistics.html')
        query_dictionary = {'host': 'nodes.host',
                            'cluster': 'nodes.cluster_name',
                            'user': 'nodes.username',
                            'db_version': 'nodes.db_version',
                            'os_version': 'nodes.os_version',
                            'seed_node': 'nodes.seed_node',
                            'status': 'installations.global_status'}
        option_dictionary = {}
        for key, value in query_dictionary.items():
            query_data = {'columns': f'distinct {value}', 'join_installations': 'yes', 'join_statuses': 'no',
                          'filter': f'installations.global_status in (\'{InstallationState.FAILED.value}\', \
                                                        \'{InstallationState.SUCCEEDED.value}\')'}
            query_result = self._database.select_data(query_params=query_data, columns=(f'{key}',))
            option_dictionary[key] = [x.get(key) for x in query_result]
            option_dictionary['today'] = datetime.datetime.now().strftime('%Y-%m-%d')
        return template.render(options=option_dictionary)

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def get_stat(self):
        data = cherrypy.request.json
        response = {}
        where_string = "installations.start_timestamp between " \
                       f"timestamp(\'{data.get('start_date_from')} {data.get('start_time_from')}\') " \
                       f"and timestamp(\'{data.get('start_date_to')} {data.get('start_time_to')}\')"
        if data.get('cluster') != 'all':
            where_string += f" and nodes.cluster_name = \'{data.get('cluster')}\'"
        if data.get('host') != 'all':
            where_string += f" and nodes.host = \'{data.get('host')}\'"
        if data.get('user') != 'all':
            where_string += f" and nodes.username = \'{data.get('user')}\'"
        if data.get('db_version') != 'all':
            where_string += f" and nodes.db_version = \'{data.get('db_version')}\'"
        if data.get('os_version') == 'None':
            where_string += f" and nodes.os_version is null"
        elif data.get('os_version') != 'all':
            where_string += f" and nodes.os_version = \'{data.get('os_version')}\'"
        if data.get('seed_node') != 'all':
            where_string += f" and nodes.seed_node = \'{data.get('seed_node')}\'"
        if data.get('status') != 'all':
            where_string += f" and installations.global_status = \'{data.get('status')}\'"
        else:
            where_string += f" and installations.global_status in (\'{InstallationState.FAILED.value}\', " \
                            f"\'{InstallationState.SUCCEEDED.value}\')"
        query_data = {'columns': 'nodes.cluster_name, nodes.host, nodes.username, nodes.db_version, nodes.os_version,'
                                 'nodes.seed_node, installations.start_timestamp, installations.finish_timestamp,'
                                 'installations.global_status', 'join_installations': 'yes', 'join_statuses': 'no',
                      'filter': where_string}
        statistics = self._database.select_data(query_params=query_data, columns=('cluster', 'host', 'user',
                                                                                  'db_version', 'os_version',
                                                                                  'seed_node', 'installation_start',
                                                                                  'installation_finish', 'status'))
        for record in statistics:
            if record['installation_start']:
                record['installation_start'] = record.get('installation_start').strftime('%d.%m.%Y %H:%M:%S.%f')
            if record['installation_finish']:
                record['installation_finish'] = record.get('installation_finish').strftime('%d.%m.%Y %H:%M:%S.%f')
            for key in record.keys():
                if not record[key]:
                    record[key] = ''
        response['message'] = [list(x.values()) for x in statistics]
        return response

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def status(self):
        data = cherrypy.request.json
        host = data.get('host')
        response = {}
        if host:
            sleep(1)
            query_data = {'columns': 'nodes.host, installations.global_status, statuses.status_name',
                          'join_installations': 'yes', 'join_statuses': 'yes', 'filter': f'nodes.host = \'{host}\''}
            available_statuses = self._database.select_data(query_params=query_data, columns=('host', 'global_status',
                                                                                              'status_name'))
            response['message'] = available_statuses
        else:
            sleep(3)
            query_data = {'columns': 'nodes.host', 'join_installations': 'yes', 'join_statuses': 'no',
                          'filter': f'installations.global_status = \'{InstallationState.IN_PROGRESS.value}\''}
            active_hosts = self._database.select_data(query_params=query_data, columns=('host',))
            response['message'] = active_hosts
        return response

    @cherrypy.expose
    @cherrypy.tools.json_in()
    def install(self):
        data = cherrypy.request.json
        query_data = {'columns': 'nodes.host', 'join_installations': 'yes', 'join_statuses': 'no',
                      'filter': f'installations.global_status in (\'{InstallationState.NEW.value}\', \
                      \'{InstallationState.IN_PROGRESS.value}\')'}
        active_hosts = self._database.select_data(query_params=query_data, columns=('host',))
        new_nodes = ''
        new_installations = ''
        nodes_to_install = []
        for node in data['nodes']:
            active_node = False
            for host in active_hosts:
                if node['host'] == host['host'] and not node.get('force_install'):
                    active_node = True
            if not active_node:
                if node.get('force_install'):
                    values_to_update = {'global_status': InstallationState.FAILED.value,
                                        'finish_timestamp': 'get_system_timestamp'}
                    self._database.update_data(table='installations',
                                               condition=f'host = \'{node["host"]}\' and global_status in '
                                                         f'(\'{InstallationState.NEW.value}\','
                                                         f'\'{InstallationState.IN_PROGRESS.value}\')',
                                               **values_to_update)
                node.pop('force_install', None)
                nodes_to_install.append(node)
        for node in nodes_to_install:
            if node['password'] != 'null':
                node['password'] = b64encode(node.get('password').encode('utf-8')).decode('utf-8')
            query_data = {'columns': 'nodes.host', 'join_installations': 'no', 'join_statuses': 'no',
                          'filter': f'host = \'{node["host"]}\''}
            existing_node = self._database.select_data(query_params=query_data, columns=('host',))
            if existing_node:
                node_to_update = {x: node[x] for x in list(node.keys())[1:]}
                self._database.update_data(table='nodes', condition=f'host = \'{node["host"]}\'', **node_to_update)
                new_installations += f'(\'new\', \'{node["host"]}\'),'
            else:
                new_nodes += f'{tuple(node.values())},'
                new_installations += f'(\'new\', \'{node["host"]}\'),'
        if new_nodes != '':
            columns_to_insert = tuple(nodes_to_install[0].keys())
            self._database.insert_data(table='nodes', columns=columns_to_insert, values=new_nodes[:-1])
        if new_installations != '':
            columns_to_insert = ('global_status', 'host')
            self._database.insert_data(table='installations', columns=columns_to_insert, values=new_installations[:-1])


if __name__ == '__main__':
    webapp = Controller()
    cherrypy.quickstart(webapp, '/', './config/installer.conf')
