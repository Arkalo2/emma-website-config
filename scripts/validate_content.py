#!/usr/bin/env python3
"""Valide content.json : JSON valide, structure attendue par le site, médias présents.

Reproduit les règles de validation du site.
Usage : python3 scripts/validate_content.py [content.json]
"""
import json
import re
import sys
from pathlib import Path

COLOR = re.compile(r"#[0-9a-fA-F]{3,8}")
FONT = re.compile(r"[A-Za-z0-9][A-Za-z0-9 \-]{0,39}")
URL_OR_PATH = re.compile(r"(https?://[^\s\"'<>]+|[A-Za-z0-9][\w./%\-]*)")
PAGES = {"home", "about", "experience", "formation", "cv", "contact"}
PLACEHOLDER = re.compile(r"^[X\s]+$")

errors = []


def err(path, msg):
    errors.append(f"{path} : {msg}")


def obj(data, path):
    if not isinstance(data, dict):
        err(path, "objet attendu")
        return {}
    return data


def strings(data, path, keys):
    data = obj(data, path)
    for k in keys:
        if not isinstance(data.get(k), str):
            err(f"{path}.{k}", "texte attendu")
    return data


def items(data, path, keys):
    if not isinstance(data, list):
        err(path, "liste attendue")
        return
    for i, item in enumerate(data):
        strings(item, f"{path}[{i}]", keys)


def match(value, pattern, path, what):
    if isinstance(value, str) and not pattern.fullmatch(value):
        err(path, f"{what} invalide : {value!r}")


def check(c, root):
    c = obj(c, "racine")
    if c.get("version") != 1 or isinstance(c.get("version"), bool):
        err("version", "doit valoir 1")

    strings(c.get("identity"), "identity", ["displayName", "firstName", "lastName", "subtitle", "badge"])
    footer = strings(c.get("footer"), "footer", ["text", "linkLabel", "linkUrl"])
    if isinstance(footer.get("linkUrl"), str) and not re.match(r"https?://", footer["linkUrl"]):
        err("footer.linkUrl", "doit commencer par http:// ou https://")
    for page in ("home", "about"):
        strings(c.get(page), page, ["pageTitle", "greeting", "intro", "text"])

    exp = strings(c.get("experiences"), "experiences", ["pageTitle", "title"])
    items(exp.get("items"), "experiences.items", ["position", "company", "place", "start", "end", "description"])
    form = strings(c.get("formations"), "formations", ["pageTitle", "title"])
    items(form.get("items"), "formations.items", ["school", "degree", "start", "end", "place", "description"])

    skills = obj(c.get("skills"), "skills")
    for k in ("knowHow", "softSkills", "it", "languages"):
        v = skills.get(k)
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            err(f"skills.{k}", "liste de textes attendue")

    if not isinstance(c.get("interests"), str):
        err("interests", "texte attendu")

    contact = strings(c.get("contact"), "contact", ["pageTitle", "title", "intro", "phone", "address", "email", "linkedin", "licenseLabel", "licenseValue"])

    cv = strings(c.get("cv"), "cv", ["pageTitle", "about"])
    items(cv.get("formations"), "cv.formations", ["date", "title", "detail"])
    items(cv.get("experiences"), "cv.experiences", ["date", "title", "description"])

    media = strings(c.get("media"), "media", ["homeImage", "aboutImage", "photo", "cv"])
    for k in ("homeImage", "aboutImage", "photo", "cv"):
        v = media.get(k)
        match(v, URL_OR_PATH, f"media.{k}", "chemin")
        # Un fichier local du dépôt doit exister.
        if isinstance(v, str) and URL_OR_PATH.fullmatch(v) and "://" not in v and not (root / v).is_file():
            err(f"media.{k}", f"fichier introuvable : {v}")

    app = strings(c.get("appearance"), "appearance", ["primaryColor", "lineColor", "textColor", "headingColor", "font"])
    for k in ("primaryColor", "lineColor", "textColor", "headingColor"):
        match(app.get(k), COLOR, f"appearance.{k}", "couleur")
    match(app.get("font"), FONT, "appearance.font", "police")

    menu = c.get("menu")
    if not isinstance(menu, list) or not menu:
        err("menu", "liste non vide attendue")
    else:
        for i, m in enumerate(menu):
            p = f"menu[{i}]"
            m = obj(m, p)
            if m.get("page") not in PAGES:
                err(f"{p}.page", f"page inconnue (attendu : {', '.join(sorted(PAGES))})")
            if not isinstance(m.get("label"), str) or not m.get("label"):
                err(f"{p}.label", "texte non vide attendu")
            if not isinstance(m.get("visible"), bool):
                err(f"{p}.visible", "booléen attendu")

    # Dépôt public : pas de numéro de téléphone réel.
    phone = contact.get("phone")
    if isinstance(phone, str) and phone and not PLACEHOLDER.match(phone):
        err("contact.phone", "ne doit pas contenir de numéro réel (dépôt public)")


def main():
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "content.json")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERREUR : {target} illisible ou JSON invalide : {e}")
        return 1
    check(data, target.resolve().parent)
    if errors:
        print(f"ERREUR : {target} ne respecte pas la structure attendue :")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK : {target} est valide.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
