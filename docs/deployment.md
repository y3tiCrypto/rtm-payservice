# Production Deployment Guide (deployment.md)

This document describes how to deploy RaptoreumPay in a production environment using **Python 3.13**, **Node 24** (optional, for frontend tasks), **MySQL 8.0+**, and **Nginx**.

---

## 1. System Prerequisites

Before deployment, ensure your Linux server (e.g., Ubuntu 22.04 LTS / 24.04 LTS) has the following:
* **Python**: Python 3.13 (or 3.10+)
* **MySQL**: MySQL 8.0 or newer
* **Node.js**: Node 24+ (required only if you are compiling, formatting, or testing frontend scripts)
* **Raptoreum Core**: A running `raptoreumd` node with RPC access enabled (either hosted locally or securely over a private network interface).

---

## 2. MySQL Database Setup

1. Connect to your MySQL server as root:
   ```bash
   mysql -u root -p
   ```

2. Create a dedicated database:
   ```sql
   CREATE DATABASE raptoreumpay CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. Create a restricted user and grant privileges:
   ```sql
   CREATE USER 'rtm_pay_user'@'localhost' IDENTIFIED BY 'your_super_secure_db_password_here';
   GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, ALTER ON raptoreumpay.* TO 'rtm_pay_user'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

---

## 3. Environment Variables Configuration

Clone the application code to `/var/www/rtm-payservice` and create a `.env` configuration file in the project root:

```env
# Database Credentials
DB_HOST=localhost
DB_PORT=3306
DB_USER=rtm_pay_user
DB_PASSWORD=your_super_secure_db_password_here
DB_NAME=raptoreumpay

# Raptoreum Node RPC Credentials
RPC_HOST=127.0.0.1
RPC_PORT=8766
RPC_USER=your_rtm_node_rpc_user
RPC_PASSWORD=your_rtm_node_rpc_password

# Admin Credentials (Basic Auth for backups)
ADMIN_USERNAME=your_custom_admin_username
ADMIN_PASSWORD=your_custom_admin_password_999!

# App Details
SECRET_KEY=generate_a_random_32_character_hex_string
BASE_URL=https://pay.yourdomain.com
```

---

## 4. Backend Service Integration (Systemd)

To ensure the FastAPI server runs continuously and recovers automatically after restarts, set up a Systemd service unit.

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/raptoreumpay.service
   ```

2. Add the following configuration:
   ```ini
   [Unit]
   Description=RaptoreumPay Payment Processor Daemon
   After=network.target mysql.service

   [Service]
   User=www-data
   WorkingDirectory=/var/www/rtm-payservice
   ExecStart=/var/www/rtm-payservice/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
   Restart=always
   Environment=PYTHONUNBUFFERED=1
   EnvironmentFile=/var/www/rtm-payservice/.env

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable raptoreumpay
   sudo systemctl start raptoreumpay
   ```

---

## 5. Nginx Reverse Proxy & SSL (HTTPS)

Configure Nginx to act as a reverse proxy, handling client requests and managing SSL certificates.

1. Create a virtual host configuration:
   ```bash
   sudo nano /etc/nginx/sites-available/pay.yourdomain.com
   ```

2. Add the configuration block:
   ```nginx
   server {
       listen 80;
       server_name pay.yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded-for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /static/ {
           alias /var/www/rtm-payservice/static/;
           expires 30d;
           add_header Cache-Control "public, no-transform";
       }
   }
   ```

3. Enable the site and restart Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/pay.yourdomain.com /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

4. Install Let's Encrypt SSL certificates via Certbot:
   ```bash
   sudo apt-get install certbot python3-certbot-nginx -y
   sudo certbot --nginx -d pay.yourdomain.com
   ```

---

## 6. DB Migrations Policy
For initial installations, FastAPI automatically executes `Base.metadata.create_all(bind=engine)` upon startup, which constructs the tables in the MySQL database.
For schema expansions, it is highly recommended to integrate **Alembic** (`pip install alembic`) to manage database schema updates. Do not modify models directly in production without running formal schema migration files.
