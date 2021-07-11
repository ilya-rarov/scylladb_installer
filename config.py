from configparser import ConfigParser
from os import path


class ConfigObject:
    def __init__(self, config_path):
        config = ConfigParser()
        if not path.exists(config_path):
            raise FileNotFoundError(f"File '{config_path}' not found!")
        config.read(config_path)
        db_params = {}
        log_params = {}
        for k, v in config['db'].items():
            db_params[k] = v.replace('"', '')
        for k, v in config['log'].items():
            log_params[k] = v.replace('"', '')
        self._db_config = db_params
        self._log_config = log_params

    @property
    def db_config(self):
        return self._db_config

    @property
    def log_config(self):
        return self._log_config
