from shiny import ui, render, App, reactive, req
import shiny.experimental as x
from shiny.types import FileInfo
import shutil
import os
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from shinywidgets import output_widget, register_widget
from ipydatagrid import DataGrid, TextRenderer
from bs4 import BeautifulSoup
import requests
import re
from PIL import Image
from io import BytesIO
import logging
from dotenv import load_dotenv


FILTER_SCOPE_OPTIONS = {
    "Titel": "title",
    "Zutaten": "ingredients",
    "Zubereitung": "preparation",
}

FILTER_FLAVOR_OPTIONS = {"süß": "sweet", "salzig": "salty", "flüssig": "liquid"}

css_path = Path(__file__).parent / "www" / "styles.css"

load_dotenv("/app/.env")


### UI ###############################

app_ui = ui.page_fluid(
    ui.include_css(css_path),
    ui.div(
        {"class": "title"},
        ui.panel_title(
            title="Der Milberts-Ofen",
            window_title="Der Milberts-Ofen",
        ),
    ),
    ui.navset_tab(
        # KOCHBUCH ##
        ui.nav(
            "Kochbuch",
            x.ui.page_sidebar(
                ui.div(
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
                ),
                ui.output_ui("recipe_cards"),
            ),
        ),
        # DATENBANK ##
        ui.nav(
            "Datenbank",
            ui.navset_pill_list(
                # NEUES REZEPT ##
                ui.nav(
                    "Neues Rezept",
                    ui.panel_title("Neues Rezept"),
                    ui.row(
                        ui.column(
                            8,
                            ui.input_text(
                                "new_title",
                                label="",
                                placeholder="Rezepttitel",
                                width="100%",
                            ),
                        ),
                    ),
                    ui.row(
                        ui.column(
                            4,
                            ui.input_text_area(
                                "new_ingredients",
                                label="",
                                placeholder="Zutaten",
                                height="400px",
                                width="100%",
                            ),
                        ),
                        ui.column(
                            4,
                            ui.input_text_area(
                                "new_preparation",
                                label="",
                                placeholder="Zubereitung",
                                height="400px",
                                width="100%",
                            ),
                        ),
                    ),
                    ui.row(
                        ui.input_text_area(
                            "new_comment",
                            label="",
                            placeholder="Kommentar",
                        ),
                    ),
                    ui.row(
                        ui.div(
                            {"class": "checkbox-container"},
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
                        ),
                    ),
                    ui.row(
                        ui.input_file(
                            "new_image",
                            label="",
                            placeholder="Rezeptbild",
                            button_label="Durchsuchen...",
                            accept="image/*",
                        ),
                    ),
                    ui.row(
                        ui.panel_conditional(
                            "input.new_title && input.new_ingredients && input.new_preparation",
                            ui.input_action_button(
                                "import_recipe", "Import", class_="btn-success"
                            ),
                        ),
                    ),
                ),
                # REZEPT VERÄNDERN ##
                ui.nav(
                    "Rezept verändern",
                    ui.panel_title("Rezept verändern"),
                    ui.input_text(
                        "recipe_to_change", label="", placeholder="Rezepttitel"
                    ),
                    output_widget("database"),
                ),
                # IMPORT VON CHEFKOCH.DE ##
                ui.nav(
                    "Import von chefkoch.de",
                    ui.panel_title("Import von chefkoch.de"),
                    ui.row(
                        ui.column(
                            5,
                            ui.input_text(
                                "chefkoch_url", label="", placeholder="Chefkoch-URL"
                            ),
                        ),
                    ),
                    ui.row(
                        ui.input_text_area(
                            "chefkoch_new_comment",
                            label="",
                            placeholder="Kommentar",
                        ),
                    ),
                    ui.row(
                        ui.div(
                            {"class": "checkbox-container"},
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
                        ),
                    ),
                    ui.row(
                        ui.column(
                            2,
                            ui.panel_conditional(
                                "input.chefkoch_url",
                                ui.input_action_button("import_chefkoch", "Import"),
                            ),
                        ),
                    ),
                ),
                # REZEPT LÖSCHEN ##
                ui.nav(
                    "Rezept löschen",
                    ui.panel_title("Rezept löschen"),
                    ui.row(
                        ui.column(
                            12,
                            ui.input_text(
                                "delete_title",
                                label="",
                                placeholder="Titel des zu löschenden Rezepts",
                            ),
                        ),
                    ),
                    ui.panel_conditional(
                        "input.delete_title",
                        ui.input_action_button("delete_recipe", "Löschen"),
                    ),
                ),
                well=True,
                widths=tuple([2, 10]),
            ),
        ),
    ),
)


def server(input, output, session):
    db_conn = create_engine(
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@kochbuch_postgres:5432/{os.getenv('POSTGRES_DB')}"
    )

    # For running outside docker container (adapt IP address)
    # db_conn = create_engine(
    #     f"postgresql://postgres:postgres@172.18.0.3:5432/kochbuch", echo=True
    # )

    ### FUNCTIONS ################

    def multiply_ingredient_quantities(ingredients: str, multiply_factor: float) -> str:
        pattern = re.compile(r"([\d,]+)\s*(.*)")
        lines = [line.strip() for line in ingredients.split("<br />")] 
        for i, line in enumerate(lines):
            match = pattern.match(line)
            if match:
                quantity = re.sub(
                    r",0$",  # remove trailing zeros
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

    def insert_recipe_to_db(
        title: str,
        ingredients: str,
        preparation: str,
        comment: str,
        sweet: bool,
        salty: bool,
        liquid: bool,
        img_name: str,
    ) -> None:
        insert_statement = """
            INSERT INTO kochbuch (title, ingredients, preparation, comment, sweet, salty, liquid, img_name)
            VALUES (:title, :ingredients, :preparation, :comment, :sweet, :salty, :liquid, :img_name);
        """

        if title in recipe_data()["title"].tolist():
            ui.notification_show("The recipe seems to exist already!", duration=None)
        else:
            params = {
                "title": title,
                "ingredients": ingredients,
                "preparation": preparation,
                "comment": comment.replace("\n", "<br />"),
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
            save_path = f"www/{img_filename}"
            Image.open(BytesIO(response.content)).save(save_path)
            logging.info(f"Image saved to {save_path}")
        else:
            img_filename = "default.jpeg"
            logging.error(f"Failed to download image from {url}! Using default image.")
        return img_filename

    def save_image_from_tmp(img_path: str) -> str:
        img_filename = get_image_filename(img_path)
        save_path = f"www/{img_filename}"
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

    ### REACTIVE CALCS ###############

    @reactive.Calc
    def recipe_data():
        return pd.read_sql(
            "SELECT * FROM kochbuch;",
            db_conn,
        )

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

    @reactive.Calc
    def selected_recipe():
        return recipe_data().query(f"title == {input.recipe()}")

    @output
    @render.ui
    def recipe_cards():
        recipe_cards = []
        for recipe in filtered_recipes().itertuples():
            print(recipe)
            recipe_cards += [
                ui.div(
                    {"class": "recipe_card"},
                    x.ui.card(
                        x.ui.card_header(
                            ui.h4(
                                recipe.title,
                            ),
                        ),
                        x.ui.card_body(
                            x.ui.card_image(
                                file=None,
                                src=recipe.img_name,
                            ),
                            ui.row(
                                ui.column(
                                    5,
                                    {"class": "ingredients"},
                                    ui.HTML(
                                        multiply_ingredient_quantities(
                                            recipe.ingredients, input.quantity_factor()
                                        )
                                    ),
                                ),
                                ui.column(
                                    5,
                                    {"class": "preparation"},
                                    ui.HTML(recipe.preparation),
                                ),
                                ui.div(
                                    {"class": "recipe-comment"},
                                    ui.h5("Kommentar"),
                                    ui.HTML(
                                        recipe.comment
                                    ),
                                ),
                            ),
                            fillable=False,
                        ),
                        height="271px",
                        full_screen=True,
                    ),
                )
            ]
        return tuple(recipe_cards)


    ### EFFECTS AND EVENTS ##############

    cell_changes = reactive.Value()

    @reactive.Effect
    def create_datagrid():
        req(input.recipe_to_change())

        default_renderer = TextRenderer(
            text_wrap=True,
            vertical_alignment="top",
        )

        datagrid = DataGrid(
            recipe_data()
            .drop(["recipe_id", "img_name"], axis=1)
            .query(f"title == '{input.recipe_to_change()}'"),
            editable=True,
            base_column_size=200,
            base_row_size=300,
            base_column_header_size=35,
            default_renderer=default_renderer,
        )
        register_widget("database", datagrid)

        def on_cell_changed(cell):
            cell_changes.set(
                {
                    "title": input.recipe_to_change(),
                    "column": cell["column"],
                    "value": cell["value"],
                }
            )

        datagrid.on_cell_change(on_cell_changed)  # register callback

    @reactive.Effect
    def update_base_table():
        print(type(cell_changes()))
        query = text(
            f"""
                UPDATE kochbuch
                SET {cell_changes()["column"]} = :value
                WHERE title = :title
            """
        )

        update_values = {
            "value": cell_changes()["value"],
            "title": cell_changes()["title"],
        }

        with db_conn.connect() as connection:
            connection.execute(query, parameters=update_values)
            connection.commit()

        ui.notification_show(
            "Change registered. Reload the app for changes to take effect.",
            duration=None,
        )

    @reactive.Effect
    @reactive.event(input.delete_recipe)
    def delete_recipe():
        if input.delete_title() not in recipe_data()["title"].tolist():
            ui.notification_show("The recipe does not seem to exist!", duration=None)
        else:
            img_name_statement = "SELECT img_name FROM kochbuch WHERE title = :title;"
            delete_statement = "DELETE FROM kochbuch WHERE title = :title;"
            params = {"title": input.delete_title()}
            with db_conn.connect() as connection:
                img_name = connection.execute(
                    text(img_name_statement), parameters=params
                )
                if os.path.isfile(f"www/{img_name}"):
                    os.remove(f"www/{img_name}")
                connection.execute(text(delete_statement), parameters=params)
                connection.commit()
            ui.notification_show(
                "Recipe deleted! Reload the app for changes to take effect.",
                duration=None,
            )

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
                input.chefkoch_new_comment().replace("\n", "<br />"),
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
                img_name = "default.jpeg"

            insert_recipe_to_db(
                input.new_title(),
                input.new_ingredients().replace("\n", "<br />"),
                input.new_preparation().replace("\n", "<br />"),
                input.new_comment().replace("\n", "<br />"),
                input.new_sweet(),
                input.new_salty(),
                input.new_liquid(),
                img_name,
            )


app = App(app_ui, server, static_assets=Path(__file__).parent / "www")
