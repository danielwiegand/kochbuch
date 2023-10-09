from shiny import ui, render, App, reactive
import shiny.experimental as x
from shiny.types import FileInfo
import shutil
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from shinywidgets import output_widget, register_widget
from ipydatagrid import DataGrid
from bs4 import BeautifulSoup
import requests
import re
from PIL import Image
from io import BytesIO
import logging
import locale

FILTER_SCOPE_OPTIONS = {
    "Titel": "title",
    "Zutaten": "ingredients",
    "Zubereitung": "preparation",
}

FILTER_FLAVOR_OPTIONS = {"süß": "sweet", "salzig": "salty", "flüssig": "liquid"}

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
                        id="filter_flavor",
                        label="",
                        choices=list(FILTER_FLAVOR_OPTIONS.keys()),
                        selected=list(FILTER_FLAVOR_OPTIONS.keys()),
                        multiple=True,
                    ),
                    ui.input_slider(
                        "quantity_factor", "", value=1, min=0.5, max=5, step=0.5
                    ),
                    # ui.input_select("recipe", "Ergebnisse", [], multiple=True),
                ),
                ui.panel_main(
                    ui.output_ui("recipe_cards"),
                    # ui.output_ui("recipe_image"),
                    # ui.output_ui("recipe_title"),
                    # ui.input_slider(
                    #     "quantity_factor", "", value=1, min=0.5, max=5, step=0.5
                    # ),
                    # ui.row(
                    #     ui.column(
                    #         6,
                    #         ui.output_ui("ingredients"),
                    #     ),
                    #     ui.column(
                    #         6,
                    #         ui.output_ui("preparation"),
                    #     ),
                    # ),
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
                    ui.input_file("new_image", label="", accept="image/*"),
                    ui.panel_conditional(
                        "input.new_title && input.new_ingredients && input.new_preparation",
                        ui.input_action_button("import_recipe", "Import"),
                    ),
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
                        ui.input_checkbox(
                            "chefkoch_new_sweet",
                            label="süß",
                        ),
                        ui.input_checkbox(
                            "chefkoch_new_salty",
                            label="salzig",
                        ),
                        ui.input_checkbox(
                            "chefkoch_new_liquid",
                            label="flüssig",
                        ),
                        ui.column(
                            2,
                            ui.panel_conditional(
                                "input.chefkoch_url",
                                ui.input_action_button("import_chefkoch", "Import"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)


# TODO Rezepte als card: https://shiny.posit.co/py/api/ExCard.html


def server(input, output, session):
    # db_conn = create_engine(
    #     f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@kochbuch_postgres:5432/{os.getenv('POSTGRES_DB')}"
    # ).connect()

    db_conn = create_engine(
        f"postgresql://postgres:postgres@192.168.64.3:5432/kochbuch", echo=True
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
                            FILTER_FLAVOR_OPTIONS[flavor]
                            for flavor in input.filter_flavor()
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

    # @reactive.Effect()
    # def update_displayed_recipes():
    #     ui.update_select(
    #         id="recipe",
    #         choices=filtered_recipes()["title"].tolist(),
    #         selected=None,
    #     )

    @output
    @render.ui
    def recipe_cards():
        recipe_cards = []
        for recipe in filtered_recipes().itertuples():
            print(recipe)
            recipe_cards += [
                ui.div(
                    {"style": "width: 300px; float:left;margin:10px; height:300px;"},
                    x.ui.card(
                        x.ui.card_header(recipe.title),
                        x.ui.card_body(
                            x.ui.card_image(
                                file=None,
                                src=recipe.img_name,
                                style="max-width: 1000px;margin-left:auto; margin-right:auto;",
                            ),
                            # ui.input_slider(
                            #     "quantity_factor", "", value=1, min=0.5, max=5, step=0.5
                            # ),
                            ui.row(
                                ui.column(
                                    5,
                                    ui.HTML(
                                        multiply_ingredient_quantities(
                                            recipe.ingredients, input.quantity_factor()
                                        )
                                    ),
                                    {
                                        "style": "max-width:500px; margin-left:auto; margin-right:4.16%;"
                                    },
                                ),
                                ui.column(
                                    5,
                                    ui.HTML(recipe.preparation),
                                    {
                                        "style": "max-width:500px; margin-left:4.16%; margin-right:auto;"
                                    },
                                ),
                            ),
                            fillable=False,
                            padding="10px",
                        ),
                        height="300px",
                        full_screen=True,
                        style="max-width:1100px; margin-left:auto; margin-right:auto;",
                    ),
                )
            ]
        # return x.ui.layout_column_wrap("350px", tuple(recipe_cards)
        return tuple(recipe_cards)

    @reactive.Calc
    def selected_recipe():
        return recipe_data().query(f"title == {input.recipe()}")

    # outputs

    @output
    @render.ui
    def recipe_image():
        img = selected_recipe()["img_name"]
        return (
            ui.tags.img(src="default.png") if img.empty else ui.tags.img(src=img.item())
        )

    @output
    @render.ui
    def recipe_title():
        return (
            ""
            if selected_recipe()["title"].empty
            else ui.h1(selected_recipe()["title"].item())
        )

    def multiply_ingredient_quantities(ingredients: str, multiply_factor: float) -> str:
        pattern = re.compile(r"([\d,]+)\s*(.*)")
        lines = ingredients.strip().split("<br />")
        for i, line in enumerate(lines):
            match = pattern.match(line)
            if match:
                quantity = re.sub(
                    r",0$",  # remove training zeros
                    "",
                    "{:,.1f}".format(  # format to one decimal place, add thousands sep
                        round(
                            float(match.group(1).replace(",", ".")) * multiply_factor, 1
                        )
                    )
                    .replace(",", "temp")  # exchange "," and "." (german way)
                    .replace(".", ",")
                    .replace("temp", "."),
                )
                rest_of_line = match.group(2).strip()
                lines[i] = quantity + " " + rest_of_line
        return "<br />".join(lines)

    @output
    @render.ui
    def ingredients():
        ingredients = selected_recipe()["ingredients"]
        if ingredients.empty:
            return ""
        else:
            print(ingredients.item())
            return ui.HTML(
                multiply_ingredient_quantities(
                    ingredients.item(), input.quantity_factor()
                )
            )

    @output
    @render.ui
    def preparation():
        preparation = selected_recipe()["preparation"]
        return "" if preparation.empty else ui.HTML(preparation.item())

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

    # Imports

    def insert_recipe_to_db(
        title: str,
        ingredients: str,
        preparation: str,
        sweet: bool,
        salty: bool,
        liquid: bool,
        img_name: str,
    ) -> None:
        insert_statement = """
            INSERT INTO kochbuch (title, ingredients, preparation, sweet, salty, liquid, img_name)
            VALUES (:title, :ingredients, :preparation, :sweet, :salty, :liquid, :img_name);
        """

        if title in recipe_data()["title"].tolist():
            ui.notification_show("The recipe seems to exist already!", duration=None)
        else:
            params = {
                "title": title,
                "ingredients": ingredients,
                "preparation": preparation,
                "sweet": sweet,
                "salty": salty,
                "liquid": liquid,
                "img_name": img_name,
            }

            with db_conn.connect() as connection:
                connection.execute(text(insert_statement), parameters=params)
                connection.commit()

            ui.notification_show(
                "Recipe inserted! Reload the app for changes to take effect.",
                duration=None,
            )

    def get_image_filename(img_path: str) -> int:
        img_id = pd.read_sql(
            "SELECT COUNT(*) FROM kochbuch;",
            db_conn,
        ).iloc[0, 0]
        return str(img_id) + "." + re.findall(r"\.(\w+)$", img_path)[0]

    def save_image_from_url(url: str) -> None:
        response = requests.get(url)
        if response.status_code == 200:
            img_filename = get_image_filename(url)
            save_path = f"kochbuch/www/{img_filename}"
            Image.open(BytesIO(response.content)).save(save_path)
            logging.info(f"Image saved to {save_path}")
        else:
            img_filename = "default.png"
            logging.error(f"Failed to download image from {url}! Using default image.")
        return img_filename

    def save_image_from_tmp(img_path: str) -> str:
        img_filename = get_image_filename(img_path)
        save_path = f"kochbuch/www/{img_filename}"
        shutil.move(img_path, save_path)
        return img_filename

    def extract_ingredients(soup: BeautifulSoup, type_: str) -> list:
        type_class_ = {"ingredients": "td-right", "measures": "td-left"}
        result = []
        for td in soup.find_all(class_=type_class_.get(type_)):
            span_tag = td.find("span")
            if span_tag:
                result += [
                    re.sub(r"\s+", " ", re.sub(r"^\n\s*|\s*$", "", span_tag.text))
                ]
            else:
                result += [""]
        return result

    def validate_flavor_checkboxes(sweet: reactive, salty: reactive, liquid: reactive):
        return sweet() + salty() + liquid() > 0

    # Import from chefkoch
    @reactive.Effect
    @reactive.event(input.import_chefkoch)
    def import_from_chefkoch():
        if not bool(
            re.match(
                re.compile(r"https?://(w{3}\.)?chefkoch\.de/rezepte/\d+/\S+\.html"),
                input.chefkoch_url(),
            )
        ):
            ui.notification_show("Please provide a valid chefkoch URL!", duration=None)
        elif not validate_flavor_checkboxes(
            input.chefkoch_new_sweet,
            input.chefkoch_new_salty,
            input.chefkoch_new_liquid,
        ):
            ui.notification_show("Please select at least one flavor!", duration=None)
        else:
            html = requests.get(input.chefkoch_url()).text
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title = soup.h1.text

            # Extract ingredients
            ing_measures = extract_ingredients(soup, "measures")
            ing_materials = extract_ingredients(soup, "ingredients")
            ingredients = "<br />".join(
                [
                    re.sub(r"^\s", "", " ".join(item))
                    for item in zip(ing_measures, ing_materials)
                ]
            )

            # Extract preparation
            preparation = re.sub(
                r"^\n\s*",
                "",
                soup.find(class_="rds-recipe-meta").find_next_siblings()[0].text,
            ).replace("\n", "<br />")

            # Extract image path
            img_url = re.compile(r"https?://\S+").findall(
                soup.find(class_="i-amphtml-fill-content").get("srcset")
            )[-1]
            img_filename = save_image_from_url(img_url)

            # Insert into database
            insert_recipe_to_db(
                title,
                ingredients,
                preparation,
                input.chefkoch_new_sweet(),
                input.chefkoch_new_salty(),
                input.chefkoch_new_liquid(),
                img_filename,
            )

    # Import new recipe
    @reactive.Effect
    @reactive.event(input.import_recipe, ignore_init=True)
    def import_recipe() -> None:
        if not validate_flavor_checkboxes(
            input.new_sweet,
            input.new_salty,
            input.new_liquid,
        ):
            ui.notification_show("Please select at least one flavor!", duration=None)
        else:
            if input.new_image():
                f: list[FileInfo] = input.new_image()
                img_name = save_image_from_tmp(f[0]["datapath"])
            else:
                img_name = "default.png"

            insert_recipe_to_db(
                input.new_title(),
                input.new_ingredients(),
                input.new_preparation(),
                input.new_sweet(),
                input.new_salty(),
                input.new_liquid(),
                img_name,
            )


app = App(app_ui, server, static_assets=Path(__file__).parent / "www")
