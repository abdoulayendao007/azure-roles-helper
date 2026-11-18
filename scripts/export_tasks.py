#!/usr/bin/env python3
"""Exporte la page Microsoft « Least privileged roles by task in Microsoft Entra ID »
vers data/entra-tasks.json.

Source : dépôt public MicrosoftDocs/entra-docs (la même source que Microsoft Learn).
Aucune authentification nécessaire. Le fichier n'est réécrit que si le contenu a changé.
"""
import datetime
import json
import os
import posixpath
import re
import sys
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/MicrosoftDocs/entra-docs/main/docs/identity/role-based-access-control/delegate-by-task.md"
DOC_DIR = "identity/role-based-access-control"
LEARN = "https://learn.microsoft.com/fr-fr/"
PAGE = LEARN + "entra/" + DOC_DIR + "/delegate-by-task"
OUT = Path(__file__).resolve().parent.parent / "data" / "entra-tasks.json"

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def learn_url(href):
    """Convertit un lien relatif de la doc en URL Microsoft Learn absolue."""
    if href.startswith("http"):
        return href
    path, _, anchor = href.partition("#")
    if path.startswith("/"):
        url = LEARN + path.lstrip("/")
    elif path:
        url = LEARN + "entra/" + posixpath.normpath(posixpath.join(DOC_DIR, path))
    else:
        url = PAGE
    url = re.sub(r"\.(md|yml)$", "", url)
    return url + ("#" + anchor if anchor else "")


def plain(text):
    return re.sub(r"\s+", " ", LINK.sub(r"\1", text)).strip()


def parse_roles(cell):
    """Une cellule contient une ou plusieurs entrées séparées par <br/>."""
    items = []
    for part in re.split(r"<br\s*/?>", cell):
        part = part.strip()
        if not part:
            continue
        m = LINK.fullmatch(part)
        if m:
            name, href = m.group(1).strip(), m.group(2).strip()
            items.append({"name": name, "url": learn_url(href), "role": "permissions-reference" in href})
        else:
            links = LINK.findall(part)
            if links and "permissions-reference" in links[0][1] and part.startswith("["):
                # Rôle suivi d'une précision : « [Rôle](...). Vous devez aussi... »
                items.append({"name": links[0][0].strip(), "url": learn_url(links[0][1]),
                              "role": True, "note": plain(part)})
                continue
            item = {"name": plain(part), "role": False}
            if links:
                item["url"] = learn_url(links[0][1])
            items.append(item)
    return items


def anchor(title):
    a = re.sub(r"[^\w\s-]", "", title.lower())
    return re.sub(r"\s+", "-", a.strip())


def parse(md):
    date = re.search(r"^ms\.date:\s*(\S+)", md, re.M)
    areas, current = [], None
    for line in md.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            if title.lower().startswith("next steps"):
                current = None
                continue
            current = {
                "area": re.sub(r"\s+least privileged roles?$", "", title, flags=re.I),
                "url": PAGE + "#" + anchor(title),
                "tasks": [],
            }
            areas.append(current)
            continue
        if current is None or not line.startswith("> |"):
            continue
        cells = [c.strip() for c in line[1:].strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in ("task", "----") or set(cells[0]) <= set("- "):
            continue
        task_links = LINK.findall(cells[0])
        task = {
            "task": plain(cells[0]),
            "least": parse_roles(cells[1]),
            "additional": parse_roles(cells[2]) if len(cells) > 2 else [],
        }
        if task_links:
            task["doc"] = learn_url(task_links[0][1])
        current["tasks"].append(task)
    areas = [a for a in areas if a["tasks"]]
    return (date.group(1) if date else None), areas


def main():
    with urllib.request.urlopen(RAW, timeout=60) as resp:
        md = resp.read().decode("utf-8")
    ms_date, areas = parse(md)
    if not areas:
        print("::error::Aucune tâche trouvée : la structure de la page a peut-être changé.")
        sys.exit(1)
    count = sum(len(a["tasks"]) for a in areas)
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    lines = ["## Tâches Microsoft (moindre privilège Entra ID)"]
    if old.get("areas") == areas:
        lines.append(f"- {len(areas)} domaines, {count} tâches, aucun changement")
    else:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps({
            "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "source": PAGE,
            "sourceDate": ms_date,
            "count": count,
            "areas": areas,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        lines.append(f"- {len(areas)} domaines, {count} tâches, mis à jour (page Microsoft du {ms_date})")
    text = "\n".join(lines)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
