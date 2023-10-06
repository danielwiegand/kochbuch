FROM ubuntu:22.04

RUN apt update && \
    apt-get install -y wget gdebi-core python3-pip && \
    wget https://download3.rstudio.org/ubuntu-18.04/x86_64/shiny-server-1.5.20.1002-amd64.deb
RUN gdebi -n shiny-server-1.5.20.1002-amd64.deb && \
    rm /srv/shiny-server/* && \
    sed -i '1s|^|# Use system python3 to run Shiny apps\n python /usr/bin/python3;\n\n|' /etc/shiny-server/shiny-server.conf && \
    pip install shiny
RUN shiny-server &