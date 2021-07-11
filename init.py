#!/usr/bin/env python3

import argparse
from os import path, makedirs
from jinja2 import FileSystemLoader, Environment, select_autoescape
from base64 import b64encode
from db_interface.sql_database_interface import MySQLDatabase

env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape()
)


def parse_args():
    supported_db = ['mysql']
    supported_log_level = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    parser = argparse.ArgumentParser(description='The script creates all the required database objects and config '
                                                 'file for ScyllaDB installer application')
    parser.add_argument('config_path', help='Path to config file', type=str)
    parser.add_argument('-sh', '--host', help='IP address or hostname of socket to connect to installer', type=str,
                        metavar='', required=True)
    parser.add_argument('-sp', '--port', help='Port of socket to connect to installer', type=int, metavar='',
                        required=True)
    parser.add_argument('-du', '--database_user', help='Username to connect to database', type=str, metavar='',
                        required=True)
    parser.add_argument('-ds', '--database_password', help='Password to connect to database', type=str, metavar='',
                        required=True)
    parser.add_argument('-db', '--database', help='Database or schema name', type=str, metavar='',
                        required=True)
    parser.add_argument('-dh', '--database_host', help='IP address or hostname of database server', type=str,
                        metavar='',
                        required=True)
    parser.add_argument('-dp', '--database_port', help='Port to connect to database', type=int, metavar='',
                        required=True)
    parser.add_argument('-dt', '--database_type', help=f"Type of database. Supported types: {', '.join(supported_db)}",
                        choices=supported_db, metavar='', required=True)
    parser.add_argument('-ld', '--log_dir', help='Directory to contain log files', type=str, metavar='', required=True)
    parser.add_argument('-ll', '--log_level',
                        help=f"Level of log files verbosity. Supported values: {', '.join(supported_log_level)}",
                        choices=supported_log_level, metavar='', required=True)
    return parser.parse_args()


def init_config(args):
    config_dir, config_filename = path.split(args['config_path'])
    log_dir = args['log_dir']
    if config_dir:
        if not path.exists(config_dir):
            makedirs(config_dir)
            print(f'Directory "{config_dir}" has been created successfully.')
    with open(args['config_path'], mode='w') as file:
        args.pop('config_path')
        args['database_password'] = b64encode(args['database_password'].encode('utf-8')).decode('utf-8')
        template = env.get_template('./config/generic.conf')
        config_content = template.render(args)
        file.write(config_content)
        print(f'Config file "{config_filename}" has been created successfully.')
    if log_dir != '':
        if not path.exists(log_dir):
            makedirs(log_dir)
            print(f'Directory "{log_dir}" has been created successfully.')


def init_database(args):
    database = MySQLDatabase(user=args['database_user'], password=args['database_password'],
                             database='', host=args['database_host'], port=args['database_port'],
                             db_type=args['database_type'])
    if args['database_type'] == 'mysql':
        database.execute(query=f"drop database if exists {args['database']}")
        database.execute(query=f"create database {args['database']}")
        for script in ['create_nodes.sql', 'create_installations.sql', 'create_statuses.sql']:
            template = env.get_template(f"./{args['database_type']}/{script}")
            database.execute(query=template.render(database=args['database']))
    print(f"The content of the database/schema \"{args['database']}\" has been created successfully.")


def main():
    cli_args = vars(parse_args())
    init_config(args=cli_args)
    init_database(cli_args)


if __name__ == '__main__':
    main()
