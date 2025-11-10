# Apache Superset Production Deployment Guide

This guide provides a complete step-by-step setup of Apache Superset in a production-style environment using:

- A dedicated system user and group
- Python virtual environment
- Gunicorn as the WSGI server
- NGINX as a reverse proxy
- PostgreSQL as the metadata database
- Auto-start on system boot via `systemd`
- Logging for Superset and NGINX
- MySQL & PostgreSQL drivers

---

## Step 1: Create a Dedicated Group and User

```bash
sudo groupadd supersetgroup
sudo adduser supersetuser
sudo usermod -aG supersetgroup supersetuser
```

## Step 2: Setup Directory for Superset

```bash
sudo mkdir -p /home/supersetuser/superset
sudo chown -R supersetuser:supersetgroup /home/supersetuser/superset
sudo chmod -R 770 /home/supersetuser/superset
```

## Step 3: Grant Sudo Access to Superset User

```bash
sudo usermod -aG sudo supersetuser
```

## Step 4: Switch to Superset User and Install Dependencies

```bash
su - supersetuser
cd /home/supersetuser/superset

sudo apt update
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev python3-pip libsasl2-dev libldap2-dev libpq-dev software-properties-common pkg-config default-libmysqlclient-dev

sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install -y python3.10-dev python3.10-venv
```

## Step 5: Create Python Virtual Environment and Install Superset

```bash
python3.10 -m venv superset-venv
source superset-venv/bin/activate
```

Install Superset and necessary drivers:

```bash
pip install --upgrade pip setuptools wheel
pip install apache-superset psycopg2-binary gunicorn mysqlclient 
pip install marshmallow==3.20.1
pip install marshmallow-sqlalchemy==0.28.1
```

Set environment variables:

```bash
export FLASK_APP=superset
export SUPERSET_CONFIG_PATH=/home/supersetuser/superset_config/superset_config.py
echo 'export FLASK_APP=superset' >> ~/.bashrc
source ~/.bashrc
```
Set Database:

```bash
sudo -u postgres psql
```
now create db and give access
```sql
CREATE DATABASE superset_db;
CREATE USER superset_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE superset_db TO superset_user;
ALTER ROLE superset_user SET client_encoding TO 'utf8';
ALTER ROLE superset_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE superset_user SET timezone TO 'UTC';

```
Exit the shell:
```bash
\q
```
Find PostgreSQL Connection Details:
```bash
sudo nano /etc/postgresql/14/main/postgresql.conf

```
Ensure this setting is correct:
```bash
listen_addresses = '*'
```
If needed, restart PostgreSQL:
```bash
sudo systemctl restart postgresql
````
Open pg_hba.conf and Edit:
```bash
sudo nano /etc/postgresql/14/main/pg_hba.conf
```
Add this one under **ipv4**
```bash
host    all             all             0.0.0.0/0               md5
```
## Step 6: Create Configuration File

```bash
mkdir -p /home/supersetuser/superset_config
```

Edit `superset_config.py`:

```python
SECRET_KEY = 'nBEN2sg8FbqC8mPl6/0HjqBAGrH7kBAZm5CUhKPMZKxfdKiWrJb0rDfK'
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://superset_user:plc-db@192.168.0.16:5432/superset_db'

FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "EMBEDDED_SUPERSET": True,
    "ALLOW_FILE_UPLOAD": True,
}

PUBLIC_ROLE_LIKE = "Gamma"
ENABLE_PROXY_FIX = True
HTTP_HEADERS = {'X-Frame-Options': 'ALLOWALL'}
SUPERSET_WEBSERVER_DOMAINS = ['superset.test.local']
ENABLE_CORS = True
CORS_OPTIONS = {
    'supports_credentials': True,
    'allow_headers': ['*'],
    'resources': ['*'],
    'origins': ['*']
}

UPLOAD_FOLDER = '/home/supersetuser/superset/uploads/'
```

## Step 7: Initialize Superset


```bash
source superset-venv/bin/activate
superset db upgrade
superset fab create-admin
superset load_examples
superset init
```

## Step 8: Create a systemd Service

Create systemd file:

```bash
sudo nano /etc/systemd/system/superset.service
```

Content:

```ini
[Unit]
Description=Apache Superset
After=network.target

[Service]
User=supersetuser
Group=supersetgroup
WorkingDirectory=/home/supersetuser/superset
Environment="PATH=/home/supersetuser/superset/superset-venv/bin"
Environment="SUPERSET_CONFIG_PATH=/home/supersetuser/superset_config/superset_config.py"
Environment="FLASK_APP=superset"
ExecStart=/home/supersetuser/superset/superset-venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8088 "superset.app:create_app()"
Restart=always
StandardOutput=append:/var/log/superset/superset.log
StandardError=append:/var/log/superset/superset-error.log

[Install]
WantedBy=multi-user.target
```

Enable service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart superset
sudo systemctl enable superset
```

## Step 9: Install and Configure NGINX

```bash
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/superset
```

Content:

```nginx
server {
    listen 80;
    server_name <YOUR_DOMAIN>;

    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    client_max_body_size 200M;
}
```

Enable and test:

```bash
sudo ln -s /etc/nginx/sites-available/superset /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Step 10: Monitor Logs

```bash
# Superset logs
tail -f /var/log/superset/superset.log
tail -f /var/log/superset/superset-error.log

# NGINX logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# systemd journal
journalctl -u superset.service -b
```

---
---

> © Deployment by **Abu Bakkar Khan** — System Admin  
> Production-ready. Secure. Scalable.
