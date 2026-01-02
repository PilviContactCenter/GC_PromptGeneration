# 📚 Prompt Studio - Server Deployment Manual

This manual provides step-by-step instructions for deploying the Prompt Studio Docker container on an existing server via SSH.

---

## 📋 Prerequisites

Before starting, ensure you have:

- **SSH access** to your target server
- **Docker** installed on the server (version 20.10+)
- **Docker Compose** installed on the server (version 2.0+ or docker-compose v1.29+)
- **Git** installed on the server
- Server has **ports 5001** available (or your preferred port)
- Your **.env** file ready with all required credentials

---

## 🔐 Required Environment Variables

Before deployment, prepare your `.env` file with these variables:

```bash
# Azure Text-to-Speech Configuration
AZURE_SPEECH_KEY=your-azure-speech-key
AZURE_SPEECH_REGION=westeurope

# Genesys Cloud API Credentials (Client Credentials Grant)
GENESYS_CLIENT_ID=your-client-credentials-client-id
GENESYS_CLIENT_SECRET=your-client-credentials-client-secret
GENESYS_REGION=mypurecloud.de

# Genesys Cloud OAuth Configuration (Authorization Code Grant)
OAUTH_CLIENT_ID=your-authorization-code-client-id
OAUTH_CLIENT_SECRET=your-authorization-code-client-secret
OAUTH_REDIRECT_URI=https://your-server-domain.com/oauth/callback
GENESYS_BASE_URL=mypurecloud.de

# Flask Secret Key (generate a random string!)
SECRET_KEY=your-super-secret-random-key-here
```

> ⚠️ **Important:** Update `OAUTH_REDIRECT_URI` to match your server's public URL!

---

## 🚀 Deployment Steps

### Step 1: Connect to Your Server

```bash
ssh user@your-server-ip
```

Replace `user` with your SSH username and `your-server-ip` with your server's IP address or hostname.

---

### Step 2: Create Application Directory

```bash
# Create the application directory
sudo mkdir -p /opt/prompt-studio
cd /opt/prompt-studio

# Set permissions (adjust user as needed)
sudo chown -R $USER:$USER /opt/prompt-studio
```

---

### Step 3: Clone the Repository

```bash
# Clone from GitHub
git clone https://github.com/YOUR_USERNAME/PromptGeneration.git .

# Or if you're updating an existing installation
git pull origin main
```

> 📝 Replace `YOUR_USERNAME` with your actual GitHub username.

---

### Step 4: Create Environment File

```bash
# Copy the example environment file
cp .env.example .env

# Edit the environment file with your credentials
nano .env
```

Fill in all the required values. Save and exit (`Ctrl+X`, then `Y`, then `Enter`).

---

### Step 5: Create Required Directories

```bash
# Create persistent data directories
mkdir -p uploads instance

# Set appropriate permissions
chmod 755 uploads instance
```

---

### Step 6: Build and Start the Container

```bash
# Build the Docker image
docker compose build

# Start the container in detached mode
docker compose up -d
```

> 📝 If using older Docker Compose, use `docker-compose` (with hyphen) instead.

---

### Step 7: Verify Deployment

```bash
# Check if container is running
docker compose ps

# View container logs
docker compose logs -f prompt-studio

# Test the health endpoint
curl -I http://localhost:5001/login
```

You should see the container status as "healthy" after a few seconds.

---

## 🔄 Common Operations

### Viewing Logs

```bash
# View real-time logs
docker compose logs -f

# View last 100 lines
docker compose logs --tail=100 prompt-studio
```

### Restarting the Container

```bash
docker compose restart
```

### Stopping the Container

```bash
docker compose down
```

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Checking Container Health

```bash
# View container status
docker compose ps

# Check resource usage
docker stats prompt-studio
```

---

## 🌐 Reverse Proxy Setup (Optional but Recommended)

For production, it's recommended to use Nginx as a reverse proxy to handle SSL/HTTPS.

### Install Nginx

```bash
sudo apt update
sudo apt install nginx
```

### Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/prompt-studio
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }
}
```

### Enable the Site

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/prompt-studio /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Add SSL with Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Certbot will automatically update your Nginx config
```

---

## 🔥 Firewall Configuration

If using UFW (Ubuntu Firewall):

```bash
# Allow SSH
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 'Nginx Full'

# Or allow direct access to port 5001 (not recommended for production)
# sudo ufw allow 5001

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## 🛠️ Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker compose logs prompt-studio

# Verify .env file exists and is readable
cat .env

# Check Docker service status
sudo systemctl status docker
```

### Permission Issues

```bash
# Fix ownership of data directories
sudo chown -R 1000:1000 uploads instance

# Fix permissions
chmod -R 755 uploads instance
```

### Port Already in Use

```bash
# Check what's using port 5001
sudo lsof -i :5001

# Or change the port in docker-compose.yml
# ports:
#   - "5002:5001"  # Map to different host port
```

### Database Issues

```bash
# The SQLite database is stored in ./instance/
# To reset (WARNING: destroys data):
rm -rf instance/*
docker compose restart
```

### Health Check Failing

```bash
# Check if the app is responding
docker compose exec prompt-studio wget -O- http://localhost:5001/login

# View detailed health status
docker inspect prompt-studio | grep -A 20 "Health"
```

---

## 📊 Monitoring

### Set Up Log Rotation

Create `/etc/logrotate.d/docker-prompt-studio`:

```bash
sudo nano /etc/logrotate.d/docker-prompt-studio
```

```
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    missingok
    delaycompress
    copytruncate
}
```

### Check Disk Usage

```bash
# Check Docker disk usage
docker system df

# Clean up unused images and containers
docker system prune -a
```

---

## 🔒 Security Best Practices

1. **Never commit `.env` to Git** - It contains sensitive credentials
2. **Use strong passwords** - Generate a secure `SECRET_KEY`
3. **Keep software updated** - Regularly update Docker and the application
4. **Use HTTPS** - Always use SSL in production
5. **Limit SSH access** - Use key-based authentication
6. **Regular backups** - Backup the `instance/` and `uploads/` directories

### Backup Script

Create a backup script at `/opt/prompt-studio/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/prompt-studio"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz instance/ uploads/

# Keep only last 7 backups
ls -t $BACKUP_DIR/backup_*.tar.gz | tail -n +8 | xargs -r rm
```

Make it executable and schedule with cron:

```bash
chmod +x /opt/prompt-studio/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/prompt-studio/backup.sh") | crontab -
```

---

## 📞 Quick Reference Commands

| Task | Command |
|------|---------|
| Start container | `docker compose up -d` |
| Stop container | `docker compose down` |
| View logs | `docker compose logs -f` |
| Restart | `docker compose restart` |
| Rebuild | `docker compose build --no-cache` |
| Update | `git pull && docker compose up -d --build` |
| Shell access | `docker compose exec prompt-studio bash` |
| Check status | `docker compose ps` |

---

## 📝 Notes

- The application runs on port **5001** by default
- Data is persisted in `./uploads` and `./instance` directories
- The container will automatically restart unless stopped manually
- Health checks run every 30 seconds

---

*Last updated: January 2026*
