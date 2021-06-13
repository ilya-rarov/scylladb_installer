import paramiko
from base64 import b64decode


class MissingAuthInformation(Exception):
    pass


class MissingSudoPassword(Exception):
    pass


class SSHConnection:
    def __init__(self, host, port, user, password=None):
        self._host = host
        self._port = port
        self._user = user
        if password:
            self._password = b64decode(password).decode('utf-8')
        else:
            self._password = password
        if self._user == 'root':
            self._sudo_mode = False
        else:
            self._sudo_mode = True

    def execute_command(self, command):
        with paramiko.SSHClient() as client:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            if self._sudo_mode:
                if self._password:
                    command = f"echo {self._password} | sudo -S --prompt='' " + command
                else:
                    command = "sudo " + command
            client.connect(hostname=self._host,
                           port=self._port,
                           username=self._user,
                           password=self._password)
            # else:
            #     raise MissingAuthInformation('The private key or password must be provided for authentication!')
            standard_input, standard_output, standard_error = client.exec_command(command)
            stdout = standard_output.readlines()
            stderr = standard_error.readlines()
            exit_code = standard_output.channel.recv_exit_status()
        return stdout, stderr, exit_code
