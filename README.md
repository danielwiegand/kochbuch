# kochbuch

# Architektur
* docker-compose mit Ubuntu + shiny server und postgres-Datenbank
* Die Shiny-App liegt als Datei im Docker-Container

# Shiny-Server
https://docs.posit.co/shiny-server/

# Features
* Zufälliges Rezept
* Exportmöglichkeit pdf
* Neues Rezept einfügen / bearbeiten / Import von Chefkoch

# Deployment
Siehe https://shiny.posit.co/py/docs/deploy-on-prem.html#open-source-options


CREATE TABLE kochbuch (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) UNIQUE,
    ingredients TEXT,
    preparation TEXT,
    sweet BOOLEAN,
    salty BOOLEAN,
    liquid BOOLEAN,
    img_name VARCHAR(255)
);
