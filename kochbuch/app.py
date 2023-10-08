from shiny import ui, render, App, reactive
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from shinywidgets import output_widget, render_widget, reactive_read, register_widget
from ipydatagrid import DataGrid

load_dotenv("/app/.env")

FILTER_SCOPE_OPTIONS = {
    "Titel": "title",
    "Zutaten": "ingredients",
    "Zubereitung": "preparation",
}

FILTER_MEAL_OPTIONS = {"süß": "sweet", "salzig": "salty", "flüssig": "liquid"}

app_ui = ui.page_fluid(
    ui.navset_tab(
        ui.nav(
            "Kochbuch",
            # ui.panel_title("Kochbuch"),
            ui.layout_sidebar(
                ui.panel_sidebar(
                    ui.input_text(
                        id="search_txt",
                        label="Suche",
                        placeholder="zB. Lasagne, Zucchini...",
                    ),
                    ui.input_selectize(
                        id="filter_scope",
                        label="",
                        choices=list(FILTER_SCOPE_OPTIONS.keys()),
                        selected=list(FILTER_SCOPE_OPTIONS.keys()),
                        multiple=True,
                    ),
                    ui.input_selectize(
                        id="filter_meal",
                        label="",
                        choices=list(FILTER_MEAL_OPTIONS.keys()),
                        selected=list(FILTER_MEAL_OPTIONS.keys()),
                        multiple=True,
                    ),
                    ui.input_select("recipe", "Ergebnisse", [], multiple=True),
                ),
                ui.panel_main(
                    ui.output_ui("recipe_image"),
                    ui.input_slider(
                        "multiply_factor", "", value=1, min=0.5, max=5, step=0.5
                    ),
                    ui.row(
                        ui.column(
                            6,
                            ui.output_text("ingredients"),
                        ),
                        ui.column(
                            6,
                            ui.output_text("preparation"),
                        ),
                    ),
                ),
            ),
        ),
        ui.nav(
            "Datenbank",
            output_widget("database"),
        ),
    ),
)


def server(input, output, session):
    db_conn = create_engine(
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@kochbuch_postgres:5432/{os.getenv('POSTGRES_DB')}"
    ).connect()

    #!!!!!!!!!!!!!!!!!!!!!!
    create_statement = """
        CREATE TABLE kochbuch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            ingredients TEXT,
            preparation TEXT,
            sweet BOOLEAN,
            salty BOOLEAN,
            liquid BOOLEAN,
            img_name TEXT
        );
    """
    db_conn.execute(create_statement)

    insert_statement = """
        INSERT INTO kochbuch (title, ingredients, preparation, sweet, salty, liquid, img_name)
        VALUES 
            ('Rezept A', 'Zucchini, Tomaten', 'cook', 1, 0, 0, 'food.png'),
            ('Rezept B', 'Banane', 'boil', 0, 1, 0, 'food2.jpg'),
            ('Rezept C', 'Chili', 'raw', 0, 1, 1, 'food3.jpg');
    """

    db_conn.execute(insert_statement)

    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    recipe_data = pd.read_sql("SELECT * FROM kochbuch;", db_conn)

    # recipe_data = pd.DataFrame(
    #     {
    #         "title": ["Rezept A", "Rezept B", "Rezept C"],
    #         "ingredients": ["Zucchini, Tomaten", "Banane", "Chili"],
    #         "preparation": ["cook", "boil", "raw"],
    #         "sweet": [True, False, False],
    #         "salty": [False, True, True],
    #         "liquid": [False, False, True],
    #         "img_name": ["food.png", "food2.jpg", "food3.jpg"],
    #     }
    # )

    @reactive.Calc
    def filtered_recipes():
        return recipe_data.query(
            "|".join(
                [
                    f"{taste} == True"
                    for taste in [
                        FILTER_MEAL_OPTIONS[meal] for meal in input.filter_meal()
                    ]
                ]
            )
            or "index!=index"
        ).query(
            "|".join(
                [
                    f"{scope}.str.contains('{'|'.join(input.search_txt().split())}', case=False)"
                    for scope in [
                        FILTER_SCOPE_OPTIONS[scope] for scope in input.filter_scope()
                    ]
                ]
            )
            or "index!=index"
        )

    @reactive.Effect()
    def update_displayed_recipes():
        ui.update_select(
            id="recipe",
            choices=filtered_recipes()["title"].tolist(),
            selected=None,
        )

    @reactive.Calc
    def selected_recipe():
        return recipe_data.query(f"title == {input.recipe()}")

    @output
    @render.ui
    def recipe_image():
        img = selected_recipe()["img_name"]
        return ui.tags.img(src="food.png") if img.empty else ui.tags.img(src=img.item())

    @output
    @render.text
    def ingredients():
        ingredients = selected_recipe()["ingredients"]
        return "" if ingredients.empty else ingredients.item()

    @output
    @render.text
    def preparation():
        preparation = selected_recipe()["preparation"]
        return "" if preparation.empty else preparation.item()

    #!################################################

    datagrid = DataGrid(recipe_data, editable=True)
    register_widget("database", datagrid)

    cell_changes = reactive.Value()

    def on_cell_changed(cell):
        cell_changes.set(str(cell))

    # register callback
    datagrid.on_cell_change(on_cell_changed)

    @reactive.Effect
    def create_sql():
        change = eval(cell_changes())
        sql = f"""
            UPDATE kochbuch
            SET cell_value = '{change["value"]}'
            WHERE row_number = {change["row"]}
            AND column_number = {change["column_index"]};
        """
        print(sql)

    #!################################################


app = App(app_ui, server, static_assets=Path(__file__).parent / "www")
