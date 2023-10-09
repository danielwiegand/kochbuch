-- This sql query is executed whenever the docker compose pipeline is (re)build

CREATE SEQUENCE kochbuch_recipe_id_seq START 0 MINVALUE 0;

CREATE TABLE IF NOT EXISTS kochbuch (
    recipe_id INTEGER DEFAULT nextval('kochbuch_recipe_id_seq') PRIMARY KEY,
    title VARCHAR(255) UNIQUE,
    ingredients TEXT,
    preparation TEXT,
    comment TEXT,
    sweet BOOLEAN,
    salty BOOLEAN,
    liquid BOOLEAN,
    img_name VARCHAR(255)
);