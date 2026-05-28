#!/bin/bash
set -e

# Ensure MySQL runtime directory exists with correct permissions
mkdir -p /var/run/mysqld
chown -R mysql:mysql /var/run/mysqld /var/lib/mysql

# Start MySQL directly (no systemd needed)
mysqld_safe --user=mysql --skip-syslog &

# Wait up to 30s for MySQL to accept connections
echo "Waiting for MySQL..."
for i in $(seq 1 30); do
    if mysqladmin ping -h 127.0.0.1 --silent 2>/dev/null; then
        echo "MySQL is ready"
        break
    fi
    echo "  retrying... ($i/30)"
    sleep 1
done

# Start Flask app
exec python3 app.py
