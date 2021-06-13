import mysql.connector
from abc import ABC, abstractmethod
from base64 import b64decode
from jinja2 import FileSystemLoader, Environment, select_autoescape

env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape()
)


class SQLDataBase(ABC):

    @abstractmethod
    def execute(self, query):
        pass

    @abstractmethod
    def insert_data(self, table, columns, values):
        pass

    @abstractmethod
    def update_data(self, table, condition, **kwargs):
        pass

    @abstractmethod
    def select_data(self, query, columns):
        pass


class MySQLDatabase(SQLDataBase):
    def __init__(self, user, password, database, host, port, db_type):
        self._user = user
        self._password = b64decode(password).decode('utf-8')
        self._database = database
        self._host = host
        self._port = port
        self._db_type = db_type

    def execute(self, query):
        result = []
        with mysql.connector.connect(user=self._user,
                                     password=self._password,
                                     database=self._database,
                                     host=self._host,
                                     port=self._port,
                                     autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                for row in cursor:
                    result.append(row)
        return result

    def insert_data(self, table, columns, values):
        raw_query = f"insert into {table} " + f"{columns} ".replace("'", "") + f"values {values}"
        query = self.replace_string(query=raw_query)
        self.execute(query=query)

    def update_data(self, table, condition, **kwargs):
        values = ", ".join([f"{k} = '{v}'" for k, v in kwargs.items()])
        raw_query = f"update {table} set {values} where {condition}"
        query = self.replace_string(query=raw_query)
        self.execute(query=query)

    def select_data(self, query_params, columns):
        result = []
        for k, v in query_params.items():
            if 'join' in k:
                query_params[k] = v.replace('no', '--').replace('yes', '')
        template = env.get_template(f'./{self._db_type}/select_query.sql')
        query = template.render(query_params)
        data = self.execute(query=query)
        for record in data:
            result.append(dict(zip(columns, record)))
        return result

    @staticmethod
    def replace_string(query):
        replacement = {'\'null\'': 'null',
                       'get_system_timestamp': 'current_timestamp(6)'}
        for k, v in replacement.items():
            query = query.replace(k, v)
        return query
