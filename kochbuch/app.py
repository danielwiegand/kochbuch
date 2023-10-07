from shiny import ui, render, App, reactive
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv("/app/.env")

FILTER_SCOPE_OPTIONS = {
    "Titel": "title",
    "Zutaten": "ingredients",
    "Zubereitung": "preparation",
}

FILTER_MEAL_OPTIONS = {"süß": "sweet", "salzig": "salty", "flüssig": "liquid"}

DB_CONN = create_engine(
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@kochbuch_postgres:5432/{os.getenv('POSTGRES_DB')}"
).connect()

app_ui = ui.page_fluid(
    ui.panel_title("Kochbuch"),
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.input_text(
                id="search_txt", label="Suche", placeholder="zB. Lasagne, Zucchini..."
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
            ui.output_text(id="test"),
        ),
        ui.panel_main(
            ui.img(src="food.png"),
            ui.input_slider("multiply_factor", "", value=1, min=0.5, max=5, step=0.5),
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
)


def server(input, output, session):
    dummy = pd.DataFrame(
        {
            "title": ["Rezept A", "Rezept B", "Rezept C"],
            "ingredients": ["Zucchini, Tomaten", "Banane", "Chili"],
            "preparation": ["cook", "boil", "raw"],
            "type": [["sweet", "liquid"], "salty", "liquid"],
        }
    )

    @reactive.Calc
    def filtered_recipes():
        return dummy[
            dummy["type"].apply(
                lambda x: any(
                    tag in x
                    for tag in [
                        value
                        for key, value in FILTER_MEAL_OPTIONS.items()
                        if key in input.filter_meal()
                    ]
                )
            )
        ].query(
            "|".join(
                [
                    f"{scope}.str.contains('{'|'.join(input.search_txt().split())}', case=False)"
                    for scope in [
                        value
                        for key, value in FILTER_SCOPE_OPTIONS.items()
                        if key in input.filter_scope()
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

    @output
    @render.text
    def ingredients():
        recipe = dummy.query(f"title == {input.recipe()}")["ingredients"]
        return "" if recipe.empty else recipe.item()

    @output
    @render.text
    def preparation():
        recipe = dummy.query(f"title == {input.recipe()}")["preparation"]
        return "" if recipe.empty else recipe.item()


app = App(app_ui, server, static_assets=Path(__file__).parent / "www")
