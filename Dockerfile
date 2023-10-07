FROM ubuntu:22.04

WORKDIR /app

COPY pyproject.toml /app

RUN apt update && \
    apt-get install -y wget gdebi-core python3-pip python3.10-venv libpq-dev curl && \
    wget https://download3.rstudio.org/ubuntu-18.04/x86_64/shiny-server-1.5.20.1002-amd64.deb && \
    gdebi -n shiny-server-1.5.20.1002-amd64.deb && \
    rm /srv/shiny-server/*
RUN python3 -m pip install poetry && \
    poetry install && \
    sed -i '1s|^|# Use system python3 to run Shiny apps\npython /app/.venv/bin/python3;\n\n|' /etc/shiny-server/shiny-server.conf

# run shiny as root; otherwise the app won't be able to see environment variables
# RUN sed -i 's/^run_as shiny;$/run_as root/' /etc/shiny-server/shiny-server.conf

CMD shiny-server
