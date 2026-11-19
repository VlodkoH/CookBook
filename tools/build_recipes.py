#!/usr/bin/env python3
"""Builds data/recipes.json from data/meta.json and data/recipes/<id>.json.

Usage:
    python tools/build_recipes.py          validate sources and write data/recipes.json
    python tools/build_recipes.py --check  validate sources only
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
META_FILE = DATA_DIR / "meta.json"
RECIPES_DIR = DATA_DIR / "recipes"
OUTPUT_FILE = DATA_DIR / "recipes.json"

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
LOCAL_IMAGE_RE = re.compile(r"^(?!/)(?![a-z][a-z0-9+.-]*:)(?!.*\.\.)[\w\-./]+\.(svg|png|jpe?g|webp|gif)$", re.IGNORECASE)
DIFFICULTIES = {None, "easy", "medium", "hard"}

RECIPE_KEYS = {
    "id", "title", "category", "description", "servings", "prepMinutes", "cookMinutes",
    "difficulty", "tags", "ingredients", "steps", "tips", "image",
}
INGREDIENT_KEYS = {"name", "amount", "amountMax", "unit", "note"}
STEP_KEYS = {
    "stage", "text", "mode", "temperature", "pressure", "minutes", "minutesMax",
    "valve", "note", "verified",
}
CATEGORY_KEYS = {"id", "name", "icon", "image", "subtitle"}

errors = []


def error(path, message):
    errors.append((path, message))


def rel(path):
    return path.relative_to(ROOT).as_posix()


def load_json(path):
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        error(path, f"cannot read JSON: {exc}")
        return None


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


def is_opt_str(value):
    return value is None or isinstance(value, str)


def is_opt_number(value):
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0)


def is_str_list(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def check_keys(path, obj, allowed, where):
    extra = sorted(set(obj) - allowed)
    if extra:
        error(path, f"{where}: unknown field(s) {', '.join(extra)}")


def check_image(path, value, where):
    if value is None:
        return
    if not isinstance(value, str) or not LOCAL_IMAGE_RE.match(value) or not (ROOT / value).is_file():
        error(path, f'{where}: "image" must be null or a relative path to an existing local image')


def check_meta(meta):
    if not isinstance(meta, dict):
        error(META_FILE, "must be a JSON object")
        return set()
    if not isinstance(meta.get("schemaVersion"), int):
        error(META_FILE, '"schemaVersion" must be an integer')
    if not is_opt_str(meta.get("device")):
        error(META_FILE, '"device" must be a string')
    categories = meta.get("categories")
    if not isinstance(categories, list) or not categories:
        error(META_FILE, '"categories" must be a non-empty array')
        return set()
    ids = set()
    for i, cat in enumerate(categories):
        where = f"categories[{i}]"
        if not isinstance(cat, dict):
            error(META_FILE, f"{where} must be an object")
            continue
        check_keys(META_FILE, cat, CATEGORY_KEYS, where)
        if not isinstance(cat.get("id"), str) or not ID_RE.match(cat["id"]):
            error(META_FILE, f'{where}: "id" must contain only a-z, 0-9 and "-"')
        elif cat["id"] in ids:
            error(META_FILE, f'{where}: duplicate id "{cat["id"]}"')
        else:
            ids.add(cat["id"])
        if not is_text(cat.get("name")):
            error(META_FILE, f'{where}: "name" is required')
        for key in ("icon", "subtitle"):
            if not is_opt_str(cat.get(key)):
                error(META_FILE, f'{where}: "{key}" must be a string')
        check_image(META_FILE, cat.get("image"), where)
    return ids


def check_recipe(path, recipe, category_ids):
    if not isinstance(recipe, dict):
        error(path, "recipe must be a JSON object")
        return
    check_keys(path, recipe, RECIPE_KEYS, "recipe")

    rid = recipe.get("id")
    if not isinstance(rid, str) or not ID_RE.match(rid):
        error(path, '"id" must contain only a-z, 0-9 and "-" (max 64 characters)')
    elif rid != path.stem:
        error(path, f'"id" ("{rid}") must match the file name ("{path.stem}")')

    if not is_text(recipe.get("title")):
        error(path, '"title" is required')
    if recipe.get("category") not in category_ids:
        error(path, f'"category" must be one of: {", ".join(sorted(category_ids))}')
    if not is_opt_str(recipe.get("description")):
        error(path, '"description" must be a string')
    for key in ("servings", "prepMinutes", "cookMinutes"):
        if not is_opt_number(recipe.get(key)):
            error(path, f'"{key}" must be a non-negative number or null')
    if recipe.get("difficulty") not in DIFFICULTIES:
        error(path, '"difficulty" must be "easy", "medium", "hard" or null')
    for key in ("tags", "tips"):
        if not is_str_list(recipe.get(key, [])):
            error(path, f'"{key}" must be an array of strings')
    check_image(path, recipe.get("image"), "recipe")

    ingredients = recipe.get("ingredients")
    if not isinstance(ingredients, list) or not ingredients:
        error(path, '"ingredients" must be a non-empty array')
        ingredients = []
    for i, ing in enumerate(ingredients):
        where = f"ingredients[{i}]"
        if not isinstance(ing, dict):
            error(path, f"{where} must be an object")
            continue
        check_keys(path, ing, INGREDIENT_KEYS, where)
        if not is_text(ing.get("name")):
            error(path, f'{where}: "name" is required')
        for key in ("amount", "amountMax"):
            if not is_opt_number(ing.get(key)):
                error(path, f'{where}: "{key}" must be a non-negative number or null')
        for key in ("unit", "note"):
            if not is_opt_str(ing.get(key)):
                error(path, f'{where}: "{key}" must be a string or null')

    steps = recipe.get("steps")
    if not isinstance(steps, list) or not steps:
        error(path, '"steps" must be a non-empty array')
        steps = []
    for i, step in enumerate(steps):
        where = f"steps[{i}]"
        if not isinstance(step, dict):
            error(path, f"{where} must be an object")
            continue
        check_keys(path, step, STEP_KEYS, where)
        if not is_text(step.get("text")):
            error(path, f'{where}: "text" is required')
        for key in ("stage", "mode", "valve", "note"):
            if not is_opt_str(step.get(key)):
                error(path, f'{where}: "{key}" must be a string or null')
        for key in ("temperature", "pressure"):
            value = step.get(key)
            if not (is_opt_str(value) or is_opt_number(value)):
                error(path, f'{where}: "{key}" must be a string, number or null')
        for key in ("minutes", "minutesMax"):
            if not is_opt_number(step.get(key)):
                error(path, f'{where}: "{key}" must be a non-negative number or null')
        if not isinstance(step.get("verified", True), bool):
            error(path, f'{where}: "verified" must be true or false')


def main():
    check_only = "--check" in sys.argv[1:]

    meta = load_json(META_FILE)
    category_ids = check_meta(meta) if meta is not None else set()

    recipes = []
    for path in sorted(RECIPES_DIR.glob("*.json")):
        recipe = load_json(path)
        if recipe is None:
            continue
        check_recipe(path, recipe, category_ids)
        recipes.append(recipe)
    if not recipes and not errors:
        error(RECIPES_DIR, "no recipes found")

    if errors:
        in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
        for path, message in errors:
            print(f"::error file={rel(path)}::{message}" if in_actions else f"{rel(path)}: {message}")
        print(f"{len(errors)} error(s).", file=sys.stderr)
        return 1

    if check_only:
        print(f"OK: {len(recipes)} recipe(s) are valid.")
        return 0

    book = {
        "schemaVersion": meta["schemaVersion"],
        "device": meta.get("device") or "",
        "categories": meta["categories"],
        "recipes": recipes,
    }
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(book, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {rel(OUTPUT_FILE)}: {len(recipes)} recipe(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
