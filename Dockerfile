# Base Infrastructure Trading Platform Docker Image
# Ubuntu 22.04 LTS with Python 3.11, VS Code Server, and IBKR TWS API

FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Python and build essentials
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    build-essential \
    # System utilities
    curl \
    wget \
    git \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    # Database clients (alternative to SSMS)
    mssql-tools18 \
    unixodbc-dev \
    # GUI support for IBKR TWS
    xvfb \
    x11vnc \
    fluxbox \
    x11-apps \
    # Java runtime for IBKR TWS
    openjdk-17-jre \
    # Additional tools
    supervisor \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Add mssql-tools to PATH
ENV PATH="$PATH:/opt/mssql-tools18/bin"

# Install code-server (VS Code in browser)
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Create application user
RUN useradd -m -s /bin/bash trader && \
    echo 'trader ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Set up Python environment
USER trader
WORKDIR /home/trader/app

# Copy requirements and install Python dependencies
COPY --chown=trader:trader requirements.txt .
RUN python3.11 -m pip install --user --upgrade pip setuptools wheel && \
    python3.11 -m pip install --user -r requirements.txt

# Create necessary directories
RUN mkdir -p /home/trader/{.config/code-server,tws-api,vnc,logs}

# Download and install IBKR TWS API
RUN cd /home/trader/tws-api && \
    wget -O tws-api.zip "https://interactivebrokers.github.io/downloads/twsapi_macunix.1019.01.zip" && \
    unzip -q tws-api.zip && \
    rm tws-api.zip

# Copy application code
COPY --chown=trader:trader . .

# Create configuration files
RUN echo 'bind-addr: 0.0.0.0:8080\n\
auth: password\n\
password: trader123\n\
cert: false' > /home/trader/.config/code-server/config.yaml

# Set up environment variables
ENV PYTHONPATH=/home/trader/app/src
ENV PATH="/home/trader/.local/bin:$PATH"
ENV DISPLAY=:1
ENV VNC_RESOLUTION=1920x1080
ENV VNC_DEPTH=24

# Switch back to root for system configuration
USER root

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/sites-available/default

# Copy startup scripts
COPY docker/start-vnc.sh /usr/local/bin/
COPY docker/start-app.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-vnc.sh /usr/local/bin/start-app.sh

# Create log directories
RUN mkdir -p /var/log/supervisor /home/trader/logs && \
    chown -R trader:trader /home/trader/logs

# Expose ports
EXPOSE 5000   # Flask application
EXPOSE 8080   # VS Code server
EXPOSE 5901   # VNC server
EXPOSE 80     # Nginx reverse proxy

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/api/entities/summary || exit 1

# Start supervisor to manage all services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]