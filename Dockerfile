FROM ubuntu:22.04

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY .env /app/.env

RUN apt update && \
    apt-get install -y wget gdebi-core python3-pip python3.10-venv libpq-dev curl
RUN wget https://download3.rstudio.org/ubuntu-18.04/x86_64/shiny-server-1.5.20.1002-amd64.deb
RUN gdebi -n shiny-server-1.5.20.1002-amd64.deb && \
    rm /srv/shiny-server/*
RUN python3 -m pip install poetry && \
    poetry config virtualenvs.in-project true && \
    poetry install && \
    sed -i '1s|^|# Use poetry python3 to run Shiny apps\npython /app/.venv/bin/python3;\n\n|' /etc/shiny-server/shiny-server.conf

CMD shiny-server
