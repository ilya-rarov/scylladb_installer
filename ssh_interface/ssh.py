import paramiko


class MissingAuthInformation(Exception):
    pass


class MissingSudoPassword(Exception):
    pass


class SSHConnection:
    def __init__(self, host, port, user, password=None, sudo_mode=True, key_file=None):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        if self._user == 'root':
            self._sudo_mode = False
        else:
            self._sudo_mode = sudo_mode
        self._key_file = key_file

    def execute_command(self, command):
        with paramiko.SSHClient() as client:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            if self._sudo_mode:
                if self._password:
                    command = f"echo {self._password} | sudo -S --prompt='' " + command
                else:
                    raise MissingSudoPassword('The password for sudo must be provided!')
            if self._key_file or self._password:
                client.connect(hostname=self._host,
                               port=self._port,
                               username=self._user,
                               key_filename=self._key_file,
                               password=self._password)
            else:
                raise MissingAuthInformation('The private key or password must be provided for authentication!')
            standard_input, standard_output, standard_error = client.exec_command(command)
            stdout = standard_output.readlines()
            stderr = standard_error.readlines()
        return stdout, stderr
