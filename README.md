# kochbuch

## What it is
A cook book app where you can store, filter and access your recipes.
Features:
* Manage your recipes without relying on a proprietary website
* Filter recipes based on flavor ("sweet", "salty" etc) or on keywords (e.h. "zucchini")
* Multiply the given amount of ingredients according to your needs
* Direct recipe import from `chefkoch.de`

## Architecture
* Shiny-Python app (https://shiny.posit.co/py/)
* Runs inside docker containers
* Postgres database to store the recipes

## How to use
* create a .env file where you define POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB
* run `docker-compose up -d --build`
* The app should be available on http://localhost:3838

# Deployment
E.g. via Shiny-Server https://docs.posit.co/shiny-server/