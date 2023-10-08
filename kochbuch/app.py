from shiny import ui, render, App, reactive
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from shinywidgets import output_widget, register_widget
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
            ui.navset_pill_list(
                ui.nav(
                    "Neues Rezept",
                    ui.input_text("new_title", label="", placeholder="Rezepttitel"),
                    ui.row(
                        ui.column(
                            4,
                            ui.input_text_area(
                                "new_ingredients",
                                label="",
                                placeholder="Zutaten",
                                height="400px",
                            ),
                        ),
                        ui.column(
                            8,
                            ui.input_text_area(
                                "new_preparation",
                                label="",
                                placeholder="Zubereitung",
                                height="400px",
                            ),
                        ),
                    ),
                    ui.input_checkbox(
                        "new_sweet",
                        label="süß",
                    ),
                    ui.input_checkbox(
                        "new_salty",
                        label="salzig",
                    ),
                    ui.input_checkbox(
                        "new_liquid",
                        label="flüssig",
                    ),
                    ui.input_action_button("import_recipe", "Import"),
                ),
                ui.nav(
                    "Rezept verändern",
                    output_widget("database"),
                ),
                ui.nav(
                    "Import von chefkoch.de",
                    ui.row(
                        ui.column(
                            5,
                            ui.input_text(
                                "chefkoch_url", label="", placeholder="Chefkoch-URL"
                            ),
                        ),
                        ui.column(
                            2,
                            ui.input_action_button("import_chefkoch", "Import"),
                        ),
                    ),
                ),
            ),
        ),
    ),
)


def server(input, output, session):
    # db_conn = create_engine(
    #     f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@kochbuch_postgres:5432/{os.getenv('POSTGRES_DB')}"
    # ).connect()

    db_conn = create_engine(
        f"postgresql://postgres:postgres@192.168.64.2:5432/kochbuch", echo=True
    )

    @reactive.Calc
    def recipe_data():
        return pd.read_sql(
            "SELECT * FROM kochbuch;",
            db_conn,
        )

    # # INSERT #############

    # insert_statement = """
    #     INSERT INTO kochbuch (title, ingredients, preparation, sweet, salty, liquid, img_name)
    #     VALUES
    #         ('Rezept A', 'Zucchini, Tomaten', 'cook', True, False, False, 'food.png'),
    #         ('Rezept B', 'Banane', 'boil', False, True, False, 'food2.jpg'),
    #         ('Rezept C', 'Chili', 'raw', False, True, True, 'food3.jpg');
    # """

    # with db_conn.connect() as connection:
    #     result = connection.execute(text(insert_statement))
    #     connection.commit()

    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

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
        return (
            recipe_data()
            .query(
                "|".join(
                    [
                        f"{taste} == True"
                        for taste in [
                            FILTER_MEAL_OPTIONS[meal] for meal in input.filter_meal()
                        ]
                    ]
                )
                or "index!=index"
            )
            .query(
                "|".join(
                    [
                        f"{scope}.str.contains('{'|'.join(input.search_txt().split())}', case=False)"
                        for scope in [
                            FILTER_SCOPE_OPTIONS[scope]
                            for scope in input.filter_scope()
                        ]
                    ]
                )
                or "index!=index"
            )
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
        return recipe_data().query(f"title == {input.recipe()}")

    # outputs

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

    # Code related to database updates

    cell_changes = reactive.Value()

    @reactive.Effect
    def create_datagrid():
        # sort_values according to recipe_id is important here, as cell_changes gives
        # us only the number of the row where a value has been changed. To make this row
        # number congruent with recipe_id, we have to order by recipe_id first.
        datagrid = DataGrid(
            recipe_data()
            .sort_values("recipe_id")
            .drop(["recipe_id", "img_name"], axis=1),
            editable=True,
        )
        register_widget("database", datagrid)

        def on_cell_changed(cell):
            cell_changes.set(str(cell))

        datagrid.on_cell_change(on_cell_changed)  # register callback

    @reactive.Effect
    def update_base_table():
        change = eval(cell_changes())

        query = text(
            f"""
                UPDATE kochbuch
                SET {change["column"]} = :value
                WHERE recipe_id = :row
            """
        )

        update_values = {
            "value": change["value"],
            "row": change["row"],
        }

        with db_conn.connect() as connection:
            connection.execute(query, parameters=update_values)
            connection.commit()

        ui.notification_show(
            "Note: Reload the app for changes to take effect.", duration=None
        )

    # Import from chefkoch
    # @reactive.Effect
    @reactive.event(input.import_chefkoch)
    def import_from_chefkoch():
        from bs4 import BeautifulSoup
        import requests
        import re

        html = requests.get(
            "https://www.chefkoch.de/rezepte/259781101566295/Kuerbissuppe-mit-Ingwer-und-Kokosmilch.html"
        ).text
        soup = BeautifulSoup(html, "html.parser")

        # Measures
        td_tags = soup.find_all(class_="td-left")
        measures = []

        for td in td_tags:
            span_tag = td.find("span")
            if span_tag:
                measures += [
                    re.sub(r"\s+", " ", re.sub(r"^\n\s*|\s*$", "", span_tag.text))
                ]
            else:
                measures += [""]

        td_tags = soup.find_all(class_="td-right")
        ingredients = []

        # Ingredients
        for td in td_tags:
            span_tag = td.find("span")
            if span_tag:
                ingredients += [
                    re.sub(r"\s+", " ", re.sub(r"^\n\s*|\s*$", "", span_tag.text))
                ]
            else:
                ingredients += [""]

        # Zubereitung
        preparation = soup.find(class_="rds-recipe-meta").find_next_siblings()[0].text

        # Image
        soup.find(class_="i-amphtml-fill-content").get("src")

    # Import new recipe
    @reactive.Effect
    @reactive.event(input.import_recipe, ignore_init=True)
    def import_recipe():
        insert_statement = """
            INSERT INTO kochbuch (title, ingredients, preparation, sweet, salty, liquid, img_name)
            VALUES (:title, :ingredients, :preparation, :sweet, :salty, :liquid, 'food.png');
        """

        print("HELLO")

        params = {
            "title": input.new_title(),
            "ingredients": input.new_ingredients(),
            "preparation": input.new_preparation(),
            "sweet": input.new_sweet(),
            "salty": input.new_salty(),
            "liquid": input.new_liquid(),
        }

        with db_conn.connect() as connection:
            connection.execute(text(insert_statement), parameters=params)
            connection.commit()

        # TODO Wenn Textfelder nicht ausgefüllt
        # TODO Wenn kein Button ausgewählt


app = App(app_ui, server, static_assets=Path(__file__).parent / "www")
