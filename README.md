# ScyllaDB Installer
ScyllaDB Installer allows user to install ScyllaDB cluster of several nodes. All the nodes of the cluster will be installed in parallel.

###### How to install and start this application
To install ScyllaDB installer on your Linux machine do following:
1. Clone repository to your local machine:

`git clone https://github.com/ilya-rarov/scylladb_installer.git`

2. Install the necessary Python libraries:

`pip3 install -r requirements.txt`

3. Install some additional packages. For example, in Ubuntu:

`apt-get install python3-dev default-libmysqlclient-dev build-essential`

4. Add execute permissions to the following files of the application:

`chmod +x init.py installer.py startup.py controller.py`

5. Perform initialization of config file and database. The command may look like this:

`./init.py Path_to_config_file -sh=Web_UI_Hostname_Or_IP -sp=Web_UI_Port -du=Your_database_user -ds=Your_database_password -db=Your_database_schema -dh=Your_database_host -dp=Your_database_port -dt=Your_database_type -ld=Your_log_directory -ll=Your_log_level`

6. Start the application. The command may look like this:

`./startup.py Path_to_config_file`

###### How to prepare nodes for installations
1. For the installation you can use root or any regular user with sudo privileges.

2. You may configure a pair of SSH keys, and they will be used by application during the installation process.
To configure the SSH keys on the ScyllaDB Installer machine run `ssh-keygen` (leave all the options by default, do not set up the password). 
   Then execute following command to copy public key to the remote server `ssh-copy-id -i ~/.ssh/id_rsa.pub remote_user@remote_host`.
   Put the generated public key to all the hosts you need.
   
3. The password in needed to access the node via SSH and to perform the command in sudo mode on this node. So it is possible not to provide password for user in Web UI only if you've already set up the SSH key to access the node, and your sudo mode doesn't require the password. In all other cases the password must be provided in Web UI.

4. If you are going to set up ScyllaDB CentOS set up the firewall or stop and disable it completely:
   
`systemctl stop firewalld`

`systemctl disable firewalld`

###### Known limitations of the application
