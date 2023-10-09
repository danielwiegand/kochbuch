# kochbuch

# Architektur
* docker-compose mit Ubuntu + shiny server und postgres-Datenbank
* Die Shiny-App liegt als Datei im Docker-Container

# Shiny-Server
https://docs.posit.co/shiny-server/

# Features
* Zufälliges Rezept
* Exportmöglichkeit pdf
* Code in Module unterteilen

# Deployment
Siehe https://shiny.posit.co/py/docs/deploy-on-prem.html#open-source-options


INSERT INTO kochbuch (title, ingredients, preparation, sweet, salty, liquid, img_name)
VALUES
    ('Rezept A', 'Zucchini, Tomaten', 'cook', True, False, False, 'food.png'),
    ('Rezept B', 'Banane', 'boil', False, True, False, 'food2.jpg'),
    ('Rezept C', 'Chili', 'raw', False, True, True, 'food3.jpg');