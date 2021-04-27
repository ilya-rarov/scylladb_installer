import mysql.connector
from base64 import b64decode


class MySQLDatabase:
    def __init__(self, user, password, database, host, port):
        self._user = user
        self._password = b64decode(password).decode('utf-8')
        self._database = database
        self._host = host
        self._port = port

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

    def insert_data(self, table, values):
        query = f"insert into {table} values {values}".replace("'null'", 'null')
        self.execute(query=query)

    def update_data(self, table, condition, **kwargs):
        values = ", ".join([f"{k} = '{v}'" for k, v in kwargs.items()])
        query = f"update {table} set {values} where {condition}".replace("'null'", 'null')
        self.execute(query=query)

    def select_data(self, query, columns):
        result = []
        data = self.execute(query=query)
        for record in data:
            result.append(dict(zip(columns, record)))
        return result


if __name__ == '__main__':
    pass
