# Docker Setup for Base Infrastructure Trading Platform

## Overview

This Docker setup provides a complete containerized environment for the Base Infrastructure trading platform with:

- **Ubuntu 22.04** base system
- **Python 3.11** trading application
- **VS Code Server** (browser-based IDE)
- **SQL Server** with web-based management
- **IBKR TWS API** for trading
- **VNC Server** for GUI applications

## Quick Start

### 1. Build and Run with Docker Compose

```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f
```

### 2. Access the Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Trading App** | http://localhost:5000 | - |
| **VS Code** | http://localhost:8080 | Password: `trader123` |
| **SQL Admin** | http://localhost:8081 | Server: `sqlserver`, User: `sa`, Password: `YourStrongPassword123!` |
| **VNC (GUI)** | vnc://localhost:5901 | Password: `trader123` |

### 3. Trading Dashboard

Navigate to http://localhost:5000/dashboard for the comprehensive trading interface with:
- Algorithm management
- Portfolio overview
- Database explorer
- Backtest results
- Performance visualization

## Services Architecture

### Core Container (`trading-platform`)

**Ports:**
- `5000` - Flask trading application
- `8080` - VS Code server
- `5901` - VNC server for GUI access
- `80` - Nginx reverse proxy

**Key Features:**
- Complete Python trading environment
- Interactive development with VS Code
- GUI support for IBKR TWS
- Automated service management with Supervisor

### Database Container (`sqlserver`)

**Ports:**
- `1433` - SQL Server

**Features:**
- SQL Server 2022 Developer Edition
- Persistent data storage
- Ready for trading application connections

### Database Admin (`adminer`)

**Ports:**
- `8081` - Web-based SQL client

**Features:**
- Browser-based database management
- Alternative to SQL Server Management Studio (SSMS)
- Full SQL query and administration capabilities

## SSMS Alternative Solutions

Since SSMS is Windows-only, this setup provides these alternatives:

1. **Adminer** (http://localhost:8081) - Web-based SQL client
2. **sqlcmd** - Command-line SQL client (available in container)
3. **VS Code Extensions** - SQL Server extension for development

## IBKR TWS API Setup

The container includes Interactive Brokers TWS API setup:

### API Access
- **Paper Trading Port**: 7497
- **Live Trading Port**: 7496
- **GUI Access**: VNC to localhost:5901

### Configuration
The TWS configuration allows API connections with these settings:
- Trusted IPs: 127.0.0.1 (localhost)
- API access enabled
- Socket security disabled for development

### Starting TWS GUI
```bash
# Connect via VNC and run:
/home/trader/tws-api/start-tws.sh
```

## Development Workflow

### VS Code Development
1. Access http://localhost:8080
2. Open `/home/trader/app` workspace
3. Use integrated terminal for commands
4. Install Python extensions as needed

### Database Management
1. Access http://localhost:8081
2. Connect to `sqlserver` with credentials
3. Create/manage trading databases
4. Run SQL queries and procedures

### Application Testing
```bash
# Access container shell
docker-compose exec trading-platform bash

# Run tests
cd /home/trader/app
python -m unittest discover tests

# Start Flask manually
python -m src.interfaces.flask.flask
```

## Persistent Data

The following directories are persisted:
- `./data` - Trading data and CSV files
- `./reports` - Backtest and analysis reports  
- `./results` - Trading results
- `./mlruns` - MLflow experiment tracking
- VS Code settings and extensions
- SQL Server database files

## Environment Variables

Key environment variables for customization:

### Database
- `DB_HOST` - Database host (default: sqlserver)
- `DB_PORT` - Database port (default: 1433)
- `DB_USER` - Database username (default: sa)
- `DB_PASSWORD` - Database password

### IBKR TWS
- `TWS_HOST` - TWS host (default: localhost)
- `TWS_PORT` - TWS API port (default: 7497)
- `TWS_CLIENT_ID` - Client ID for API connections

### Security
- `VNC_PASSWORD` - VNC access password
- `CODE_SERVER_PASSWORD` - VS Code access password

## Troubleshooting

### Service Issues
```bash
# Check service status
docker-compose ps

# View specific service logs
docker-compose logs trading-platform
docker-compose logs sqlserver

# Restart services
docker-compose restart
```

### Network Issues
```bash
# Check network connectivity
docker-compose exec trading-platform curl -f http://localhost:5000/health
docker-compose exec trading-platform ping sqlserver
```

### Database Connection
```bash
# Test SQL Server connection
docker-compose exec trading-platform sqlcmd -S sqlserver -U sa -P 'YourStrongPassword123!'
```

### IBKR TWS Issues
1. Ensure VNC is accessible on port 5901
2. Check TWS configuration in ~/.config/IBJts/jts.ini
3. Verify API ports 7496/7497 are not blocked
4. Review TWS logs for connection issues

## Security Notes

**For Development Only:**
- Default passwords are used
- API security is relaxed
- Services run with elevated privileges

**For Production:**
- Change all default passwords
- Enable SSL/TLS encryption
- Configure proper firewall rules
- Use secure authentication methods
- Review and harden container security

## Custom Configuration

### Adding New Services
Add services to `docker-compose.yml`:
```yaml
  new-service:
    image: custom-image
    networks:
      - trading-network
```

### Environment Customization
Create `.env` file for environment variables:
```bash
DB_PASSWORD=YourSecurePassword
VNC_PASSWORD=YourVNCPassword
CODE_SERVER_PASSWORD=YourCodePassword
```

### Volume Mounts
Add custom volume mounts in docker-compose.yml:
```yaml
    volumes:
      - ./custom-config:/home/trader/config
```