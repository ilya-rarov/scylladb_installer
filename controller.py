#!/usr/bin/env python3

import cherrypy
from db_interface.sql_database_interface import MySQLDatabase
from base64 import b64encode
from enum import Enum, unique
from config import ConfigObject


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

    @property
    def database(self):
        return self._database

    @cherrypy.expose
    def index(self):
        return open('installer.html')

    @cherrypy.expose
    def status(self):
        pass
        # should return the state of the installation from the DB table
        return

    @cherrypy.expose
    @cherrypy.tools.json_in()
    def install(self):
        data = cherrypy.request.json
        query_data = {'columns': 'nodes.host', 'join_installations': 'yes', 'join_statuses': 'no',
                      'filter': f'installations.global_status in (\'{InstallationState.NEW.value}\', \
                      \'{InstallationState.IN_PROGRESS.value}\')'}
        active_hosts = self.database.select_data(query_params=query_data, columns=('host',))
        print(active_hosts)
        columns_to_insert = tuple(data['nodes'][0].keys())
        new_nodes = ''
        new_installations = ''
        nodes_to_install = []
        for node in data['nodes']:
            active_node = False
            for host in active_hosts:
                if node['host'] == host['host']:
                    active_node = True
            if not active_node:
                nodes_to_install.append(node)
        for node in nodes_to_install:
            if node['password'] != 'null':
                node['password'] = b64encode(node.get('password').encode('utf-8')).decode('utf-8')
            query_data = {'columns': 'nodes.host', 'join_installations': 'no', 'join_statuses': 'no',
                          'filter': f'host = \'{node["host"]}\''}
            existing_node = self.database.select_data(query_params=query_data, columns=('host',))
            if existing_node:
                node_to_update = {x: node[x] for x in list(node.keys())[1:]}
                self.database.update_data(table='nodes', condition=f'host = \'{node["host"]}\'', **node_to_update)
                new_installations += f'(\'new\', \'{node["host"]}\'),'
            else:
                new_nodes += f'{tuple(node.values())},'
                new_installations += f'(\'new\', \'{node["host"]}\'),'
        if new_nodes != '':
            self.database.insert_data(table='nodes', columns=columns_to_insert, values=new_nodes[:-1])
        if new_installations != '':
            columns_to_insert = ('global_status', 'host')
            self.database.insert_data(table='installations', columns=columns_to_insert, values=new_installations[:-1])


if __name__ == '__main__':
    webapp = Controller()
    cherrypy.quickstart(webapp, '/', './config/installer.conf')