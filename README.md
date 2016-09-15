# P5_Linux-Server-Configuration
This is the project 5 of the Udacity's Full Stack Web Developer Nanodegree Program.  

The project's task is a baseline installation of a Ubuntu Linux distribution on a virtual machine to host a Flask web application (project 3). This includes the installation of updates, securing the system from a number of attack vectors and installing/configuring web and database servers.

You can see the final project at https://fsnd-p3-conference.herokuapp.com/

Please read more information in **document.pdf** (database design and program implementation).

## Server info
IP address: 52.41.96.234, port:2200  
Complete URL: ec2-52-41-96-234.us-west-2.compute.amazonaws.com
## Configuration of server
Note: All WORD-IN-THIS-TYPE must be changed accordingly to the appropriate case.
### 1. Create a Development Environment:
* Download the private key from [Udacity](https://www.udacity.com/account#!/development_environment) and move it into the folder ~/.ssh:  
    ```
    $ mv ~/Downloads/udacity_key.rsa ~/.ssh/
    ```
* Set the file rights (only owner can write and read):  
    ```
    $ chmod 600 ~/.ssh/udacity_key.rsa
    ```
* SSH into the instance:  
    ```
    $ ssh -i ~/.ssh/udacity_key.rsa root@PUBLIC-IP-ADDRESS
    ```

### 2. Create a new user and give the user the permission to sudo:
Source: [DigitalOcean](https://www.digitalocean.com/community/tutorials/how-to-add-and-delete-users-on-an-ubuntu-14-04-vps)
* Create a new user:  
    ```
    $ adduser NEW-USER-NAME
    ```
* Give new user the permission to sudo:
	- Open the sudo configuration:  
        ```
        $ visudo
        ```
	- Add the following line below `root ALL...`:  
        ```
        NEW-USER-NAME ALL=(ALL:ALL) ALL
        ```
	- Verify the existence of the new user:  
        ```
        $ cat /etc/passwd 
        ```
        or
        ```
        $ cat /etc/shadow
        ```

### 3. Update and upgrade all currently installed packages
Source: [Ask Ubuntu](http://askubuntu.com/questions/94102/what-is-the-difference-between-apt-get-update-and-upgrade)
* Update the list of available packages and their versions:  
    ```
    $ sudo apt-get update
    ```
* Install newer vesions of packages:  
    ```
    $ sudo apt-get upgrade
    ```

### 4. Include cron scripts to automatically manage package updates
Source: [Ubuntu documentation](https://help.ubuntu.com/community/AutomaticSecurityUpdates)
* Install the unattended-upgrades package:  
    ```
    $ sudo apt-get install unattended-upgrades
    ```
* Enable the unattended-upgrades package:  
    ```
    $ sudo dpkg-reconfigure -plow unattended-upgrades
    ```

### 5. Configure the SSH access and login with the new user
Source: [Ask Ubuntu](http://askubuntu.com/questions/16650/create-a-new-ssh-user-on-ubuntu-server)
* Change ssh config file:
	- Open the config file:  
        ```
        $ sudo nano /etc/ssh/sshd_config
        ```
	-  Change to Port 2200.
	- Change `PermitRootLogin` from `without-password` to `no`.
	- Temporalily change `PasswordAuthentication` from `no` to `yes`.
	- Append `UseDNS no`.
	- Append `AllowUsers NEW-USER-NAME`.
* Restart SSH Service:  
    ```
    $ /etc/init.d/ssh restart
    ```
* Create SSH Keys:
Source: DigitalOcean
	- Generate a SSH key pair in .ssh folder on the local machine:  
        ```
        ~/.ssh$ ssh-keygen
        ```
	- Copy the content of the file id_rsa.pub from local to the file authorized_keys on server:  
        ```
        ~/.ssh$ sudo nano authorized_keys
        ```
    Copy the content of  id_rsa.pub.
* Login with the new user:  
    ```
    $ ssh -v NEW-USER-NAME@PUBLIC-IP-ADDRESS -p2200
    ```
* Change `PasswordAuthentication` back from `yes` to `no` in /etc/ssh/sshd_config.

### 6. Configure Firewall to monitor for repeated unsuccessful login attempts and ban attackers
Source: [DigitalOcean](https://www.digitalocean.com/community/tutorials/how-to-protect-ssh-with-fail2ban-on-ubuntu-14-04)
* Install Fail2ban:  
    ```
    $ sudo apt-get install fail2ban
    ```
* Copy the default config file:  
    ```
    $ sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
    ```
* Check and change the default parameters:
	- Open the local config file:  
        ```
        $ sudo nano /etc/fail2ban/jail.local
        ```
	- Set the following Parameters:  
        ```
        bantime  = 1800
        
        destemail = ADMIN-EMAIL-ADDRESS
        
        action = %(action_mwl)s  
        ```
        under [ssh] change:  
        ```
        port = 2200
        ```
* Install needed software for our configuration:  
    ```
    $ sudo apt-get install sendmail iptables-persistent
    ```
* Set up a basic firewall only allowing connections from the above ports:  
    ```
    $ sudo iptables -A INPUT -i lo -j ACCEPT
    
    $ sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    
    $ sudo iptables -A INPUT -p tcp --dport 2200 -j ACCEPT
    
    $ sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
    
    $ sudo iptables -A INPUT -p udp --dport 123 -j ACCEPT
    
    $ sudo iptables -A INPUT -j DROP
    ```
* Check the current firewall rules:  
    ```
    $ sudo iptables -S
    ```
* Stop the service:  
    ```
    $ sudo service fail2ban stop
    ```
* Start it again:  
    ```
    $ sudo service fail2ban start
    ```

### 7. Configure the local timezone to UTC
Source: [Ubuntu documentation](https://help.ubuntu.com/community/UbuntuTime#Using_the_Command_Line_.28terminal.29)
* Open the timezone selection dialog:  
    ```
    $ sudo dpkg-reconfigure tzdata
    ```
* Chose 'None of the above', then UTC.
* Setup the ntp daemon ntpd for regular and improving time sync:  
    ```
    $ sudo apt-get install ntp
    ```
* Chose closer NTP time servers:
	- Open the NTP configuration file:  
        ```
        $ sudo nano /etc/ntp.conf
        ```
    - Open http://www.pool.ntp.org/en/ and choose the pool zone closest to you and replace the given servers with the new server list.

### 8. Install and configure Apache to serve a Python mod_wsgi application
Source: [Udacity](http://blog.udacity.com/2015/03/step-by-step-guide-install-lamp-linux-apache-mysql-python-ubuntu.html)
* Install Apache web server:  
    ```
    $ sudo apt-get install apache2
    ```
* Verify if the installation is successful: open the public IP address http://52.27.229.250/ on some browser, it should say 'It works!' on the top of the page.
* Install mod_wsgi for serving Python apps from Apache and the helper package python-setuptools:  
    ```
    $ sudo apt-get install python-setuptools libapache2-mod-wsgi
    ```
* Restart the Apache server for mod_wsgi to load:  
    ```
    $ sudo service apache2 restart
    ```
* Get rid of the message "Could not reliably determine the servers's fully qualified domain name" after restart Source: [Ask Ubuntu](http://askubuntu.com/questions/256013/could-not-reliably-determine-the-servers-fully-qualified-domain-name)
    - Create an empty Apache config file with the hostname:  
        ```
        $ echo "ServerName HOSTNAME" | sudo tee /etc/apache2/conf-available/fqdn.conf
        ```
    - Enable the new config file:  
        ```
        $ sudo a2enconf fqdn
        ```

### 9. Install git, clone the project 3 (p3_Conference_App)
* Install and configure git
Source: [GitHub](https://help.github.com/articles/set-up-git/#platform-linux)
	- Install Git:  
        ```
        $ sudo apt-get install git
        ```
	- Set the user name and the user email address for the commits:  
        ```
        $ git config --global user.name “USERNAME”

        $ git config --global user.email “USER-EMAIL-ADDRESS”
        ```
* Clone the p3_Conference_App from git to some temporary place:  
    ```
    <temporary place>$git clone https://github.com/mimi149/p3_Conference_App.git
    ```
* Make some necessary changes in order to use PostgreSQL instead of sqlite3:  
    Change in `database_setup.py` and `project.py`:  
    ```
    engine = create_engine('postgresql://conference:PW-FOR-DB@localhost/conference', echo=False)
    ```
    In my case, I change the DATETIME type to DATE and TIME types.

* Create a working director `/var/www/conference` and copy the necessary directories and files from the project 3, where the project.py is renamed to `__init__.py`:
    
    .  (/var/www)  
├── conference  
│    ├── conference  
│    │    ├── client_secrets.json  
│    │    ├── fb_client_secrets.json  
│    │    ├── database_setup.py  
│    │    ├── db_CRUD.py  
│    │    ├── `__init__.py`  
│    │    ├── templates (all file in this subdirectory)   
│    │    ├── static (all file in this subdirectory)   
│    │    │    ├── images (empty subdirectory)  
│    │    │    ├── download_folder (empty subdirectory)  
│    │    │    └── upload_folder (empty subdirectory)  
│    │    └── fonts (all file in this subdirectory)  

* Delete the temporary place.  

### 10. Setup a virtual private server (VPS) for deploying a Flask Application
Source: [DigitalOcean](https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps)
* Extend Python with additional packages that enable Apache to serve Flask applications:  
    ```
    $ sudo apt-get install python-dev
    ```
* Enable mod_wsgi:  
    ```
    $ sudo a2enmod wsgi
    ```
* Install pip installer:  
    ```
    $ sudo apt-get install python-pip
    ```
* Install virtualenv:  
    ```
    $ sudo pip install virtualenv
    ```
* Create a virtual environment named 'venv':  
    ```
    $ sudo virtualenv venv
    ```
* Enable all permissions for the new virtual environment (no sudo should be used within):  
Source: [Stackoverflow](http://stackoverflow.com/questions/14695278/python-packages-not-installing-in-virtualenv-using-pip)  
    ```
    $ sudo chmod -R 777 venv
    ```
* Activate the virtual environment:  
    ```
    $ source venv/bin/activate
    ```
* Install Flask inside the virtual environment:  
    ```
    $ pip install Flask
    ```
* Deactivate the environment:  
    ```
    $ deactivate
    ```
* Configure and Enable a New Virtual Host
    - Create a virtual host config file  
        ```
        $ sudo nano /etc/apache2/sites-available/conference.conf
        ```
    - Paste in the following lines of code and change names and addresses regarding the application:  
        ```
        <VirtualHost *:80>

        	ServerName PUBLIC-IP-ADDRESS

        	ServerAdmin admin@PUBLIC-IP-ADDRESS

        	WSGIScriptAlias / /var/www/conference/conference.wsgi

        	<Directory /var/www/conference/conference/>

        		Order allow, deny

        		Allow from all

        	</Directory>

        	Alias /static /var/www/conference/conference/static

        	<Directory /var/www/conference/conference/static/>

        		Order allow, deny

        		Allow from all

        	</Directory>

        	ErrorLog ${APACHE_LOG_DIR}/error.log

        	LogLevel warn

        	CustomLog ${APACHE_LOG_DIR}/access.log combined

        </VirtualHost>

        ```
    - Enable the virtual host:  
        ```
        $ sudo a2ensite conference
        ```
* Create the .wsgi File and Restart Apache
    - Create wsgi file:  
        ```
        $ sudo nano /var/www/conference/conference.wsgi
        ```
    - Paste in the following lines of code:  
        ```
        #!/usr/bin/python

        import sys

        import logging

        logging.basicConfig(stream=sys.stderr)

        sys.path.insert(0,"/var/www/conference/")

        from conference import app as application

        application.secret_key = 'Add your secret key'
        ```
* Restart Apache:  
    ```
    $ sudo service apache2 restart
    ```
* Make the conference directory web-inaccessible  
Source: [Stackoverflow](http://stackoverflow.com/questions/6142437/make-git-directory-web-inaccessible)
	- Create and open .htaccess file:  
        ```
        $ cd /var/www/conference/
        ```

        ```
        $ sudo nano .htaccess
        ```
	- Paste in the following:  
        ```
        RedirectMatch 404 /\.git
        ```

### 11. Install needed modules & packages

* Activate virtual environment:  
    ```
    $ source venv/bin/activate
    ```
* Install httplib2 module in venv:  
    ```
    $ pip install httplib2
    ```
* Install requests module in venv:  
    ```
    $ pip install requests
    ```
* Install flask.ext.seasurf:  
    ```
    $ sudo pip install flask-seasurf
    ```
* Install oauth2client.client:  
    ```
    $ sudo pip install --upgrade oauth2client
    ```
* Install SQLAlchemy:  
    ```
    $ sudo pip install sqlalchemy
    ```
* Install the Python PostgreSQL adapter psycopg:  
    ```
    $ sudo apt-get install python-psycopg2
    ```
    
### 12. Install and configure PostgreSQL
Source: [DigitalOcean](https://www.digitalocean.com/community/tutorials/how-to-secure-postgresql-on-an-ubuntu-vps)

* Install PostgreSQL:  
    ```
    $ sudo apt-get install postgresql postgresql-contrib
    ```
* Check that no remote connections are allowed (default):  
    ```
    $ sudo nano /etc/postgresql/9.3/main/pg_hba.conf
    ```
* Create needed linux user for psql:  
    ```
    $ sudo adduser conference (choose a password)
    ```
* Change to default user postgres:  
    ```
    $ sudo su - postgres
    ```
* Connect to the system:  
    ```
    $ psql
    ```
* Add a postgres user with password:  
Sources: [Trackets Blog](http://blog.trackets.com/2013/08/19/postgresql-basics-by-example.html) and [Super User](http://superuser.com/questions/769749/creating-user-with-password-or-changing-password-doesnt-work-in-postgresql)
    - Create user with LOGIN role and set a password:  
        ```
        # CREATE USER conference WITH PASSWORD 'PW-FOR-DB'; (# stands for the command prompt in psql)
        ```
    - Allow the user to create database tables:  
        ```    
        # ALTER USER conference CREATEDB;
        ```
    - List current roles and their attributes:  
        ```
        # \du
        ```
* Create database:  
    ```
    # CREATE DATABASE conference WITH OWNER conference;
    ```
* Connect to the database conference:  
    ```
    # \c conference
    ```
* Revoke all rights:  
    ```
    # REVOKE ALL ON SCHEMA public FROM public;
    ```
* Grant only access to the conference role:  
    ```
    # GRANT ALL ON SCHEMA public TO conference;
    ```
* Exit out of PostgreSQl and the postgres user:  
    ```
    # \q
    ```

    ```
    $ exit
    ```
* Create postgreSQL database schema:  
    ```
    $ python database_setup.py
    ```

### 13. Run application

* Restart Apache:  
    ```
    $ sudo service apache2 restart
    ```
* Open a browser with the public ip-address as url, e.g. 52.41.96.234 - if everything works, the application should come up.
* If getting an internal server error, check the Apache error files:  
Source: [A2 Hosting](https://www.a2hosting.com/kb/developer-corner/apache-web-server/viewing-apache-log-files)  
View the last 20 lines in the error log:   
    ```
    $ sudo tail -20 /var/log/apache2/error.log
    ```

### 14. Get OAuth-Logins Working

Source: [Udacity](https://discussions.udacity.com/t/oauth-provider-callback-uris/20460) and [Apache](http://httpd.apache.org/docs/2.2/en/vhosts/name-based.html)

* Open http://www.hcidata.info/host2ip.cgi
    - Put the public IP address: 52.41.96.234.
    - Receive the hostname: ec2-52-41-96-234.us-west-2.compute.amazonaws.com
* Open the Apache configuration files for the web app:  
    ```
    $ sudo nano /etc/apache2/sites-available/conference.conf
    ```
* Paste in the following line below ServerAdmin:  
    ```
    ServerAlias HOST-NAME
    ```
* Enable the virtual host:  
    ```
    $ sudo a2ensite conference
    ```
* To get the Google+ authorization working:  
    - Go to the project on the Google Developer Console https://console.developers.google.com/project
    - Navigate to APIs & auth > Credentials > Edit Settings
    - Add to the Authorized JavaScript origins:  
    http://ec2-52-41-96-234.us-west-2.compute.amazonaws.com  
    http://52-41-96-234
    - Add to the Authorized redirect URIs:  
    https://ec2-52-41-96-234.us-west-2.compute.amazonaws.com/oauth2callback
* To get the Facebook authorization working:
    - Go to the app in My Apps on the Facebook Developers Site  
    https://developers.facebook.com/apps/
    - Go to Settings and fill in the Site URL field:  
    http://52-41-96-234
- To leave the development mode, so others can login as well, also fill in a contact email address in the respective field, "Save Changes", click on 'Status & Review'

### 15.Install Monitor application Glances

Sources: [Glances](http://glances.readthedocs.org/en/latest/glances-doc.html#introduction) and [Web Host Bug](http://article.webhostbug.com/install-use-glances-ubuntudebian/)
* Install Glances:  
    ```
    $ sudo apt-get install python-pip build-essential python-dev
    
    $ sudo pip install Glances
    ```
