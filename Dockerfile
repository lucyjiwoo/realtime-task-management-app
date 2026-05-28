FROM ubuntu:20.04

RUN apt-get update -qq

ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install MySQL and initialize database
RUN apt-get install -y mysql-server
RUN service mysql start && \
    mysql -e "CREATE USER 'master'@'localhost' IDENTIFIED BY 'master'; \
              CREATE DATABASE db; \
              GRANT ALL PRIVILEGES ON db.* TO 'master'@'localhost';"

# Install Python dependencies
RUN apt-get install -y python3-pip
RUN mkdir /app
COPY . /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080
ENV PORT=8080

# Start MySQL without systemd, then launch the app
COPY start.sh /start.sh
RUN chmod +x /start.sh
CMD ["/start.sh"]
