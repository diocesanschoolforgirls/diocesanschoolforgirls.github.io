"""Rebuild index.html from index.template.html, listing every repo in the
organisation that has GitHub Pages enabled.

A repo is left off the list if it is archived, is this site's own repo, or
carries the topic "unlisted". The link text is the repo's entry in labels.json
if it has one, then the repo's description, then a tidied-up version of the
repo name.

Repos named in school-resources.json go in a separate "School resources"
list instead of the main one.
"""
import html
import json
import os
import urllib.request

ORG = os.environ["ORG"]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
SITE_REPO = f"{ORG}.github.io".lower()


def fetch_repos():
    repos, page = [], 1
    while True:
        req = urllib.request.Request(
            f"https://api.github.com/orgs/{ORG}/repos?per_page=100&page={page}",
            headers={
                "Accept": "application/vnd.github+json",
                **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
            },
        )
        with urllib.request.urlopen(req) as resp:
            batch = json.load(resp)
        repos += batch
        if len(batch) < 100:
            return repos
        page += 1


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


LABELS = load_json("labels.json", {})
SCHOOL_RESOURCES = set(load_json("school-resources.json", []))


def title_for(repo):
    if LABELS.get(repo["name"]):
        return LABELS[repo["name"]].strip()
    if repo.get("description"):
        return repo["description"].strip()
    words = repo["name"].replace("_", "-").split("-")
    return " ".join(words).capitalize()


def list_items(repos, empty):
    return "\n".join(
        f'    <li><a href="/{html.escape(r["name"])}/">{html.escape(title_for(r))}</a></li>'
        for r in repos
    ) or f"    <li>{empty}</li>"


def main():
    listed = [
        r for r in fetch_repos()
        if r.get("has_pages")
        and not r.get("archived")
        and r["name"].lower() != SITE_REPO
        and "unlisted" not in r.get("topics", [])
    ]
    listed.sort(key=lambda r: title_for(r).lower())

    teaching = [r for r in listed if r["name"] not in SCHOOL_RESOURCES]
    school = [r for r in listed if r["name"] in SCHOOL_RESOURCES]

    with open("index.template.html", encoding="utf-8") as f:
        page = (
            f.read()
            .replace("{{PAGES}}", list_items(teaching, "No interactives published yet."))
            .replace("{{SCHOOL_RESOURCES}}", list_items(school, "None yet."))
        )
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Listed {len(listed)} page(s).")


if __name__ == "__main__":
    main()
