"""
Add papers to Zotero by DOI/ISBN, organized into collections.
Goes through Zotero's proxy so paywalled PDFs work.
Requires Zotero desktop running with local API enabled.

Usage:
  python add_dois_to_zotero.py              # reads from dois.txt
  python add_dois_to_zotero.py my_list.txt  # reads from custom file

dois.txt format:
  Line 1: project name
  Then sections separated by blank lines:
    sub_project
    topic
    10.xxxx/yyyy  # optional comment
    10.xxxx/zzzz

  Creates: claude / <project> / <sub_project> / <topic>

  Prefix with isbn: for books.
"""

import json
import sys
import time
import os
import urllib.request
import urllib.error

ZOTERO_LOCAL = "http://localhost:23119"
DEFAULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dois.txt")
SLEEP = 3
ROOT_COLLECTION = "claude"


def api(method, path, data=None):
    url = f"{ZOTERO_LOCAL}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method,
                                headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.status, json.loads(resp.read().decode()) if resp.read else {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def ping():
    try:
        req = urllib.request.Request(f"{ZOTERO_LOCAL}/connector/ping")
        return urllib.request.urlopen(req, timeout=3).status == 200
    except Exception:
        return False


def get_collections():
    """Get all existing collections as {name: {key, parentKey}} map."""
    url = f"{ZOTERO_LOCAL}/api/users/0/collections?limit=100"
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        items = json.loads(resp.read().decode())
        result = {}
        for item in items:
            d = item.get("data", item)
            result[d["key"]] = {
                "name": d["name"],
                "key": d["key"],
                "parent": d.get("parentCollection", False),
            }
        return result
    except Exception:
        return {}


def find_collection(collections, name, parent_key=None):
    """Find a collection by name and parent."""
    for k, v in collections.items():
        parent = v["parent"] if v["parent"] else None
        if v["name"] == name and parent == parent_key:
            return v["key"]
    return None


def create_collection(name, parent_key=None):
    """Create a collection and return its key."""
    payload = [{"name": name}]
    if parent_key:
        payload[0]["parentCollection"] = parent_key
    url = f"{ZOTERO_LOCAL}/api/users/0/collections"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode())
        if "successful" in data:
            return list(data["successful"].values())[0]["data"]["key"]
        elif "success" in data:
            return list(data["success"].values())[0]
    except Exception as e:
        print(f"    Error creating collection '{name}': {e}")
    return None


def ensure_collection_path(names):
    """Ensure claude/project/sub/topic exists, return leaf key."""
    collections = get_collections()
    parent_key = None

    for name in names:
        existing = find_collection(collections, name, parent_key)
        if existing:
            parent_key = existing
        else:
            new_key = create_collection(name, parent_key)
            if new_key:
                parent_key = new_key
                collections[new_key] = {"name": name, "key": new_key, "parent": parent_key}
            else:
                print(f"    FAILED to create collection: {name}")
                return None
    return parent_key


def save_via_connector(uri):
    """Tell Zotero to fetch and save a URI. Uses Zotero's proxy."""
    payload = json.dumps({"uri": uri, "html": "", "items": None}).encode()
    req = urllib.request.Request(
        f"{ZOTERO_LOCAL}/connector/save",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        return urllib.request.urlopen(req, timeout=30).status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def get_recent_items(limit=5):
    """Get most recently added items."""
    url = f"{ZOTERO_LOCAL}/api/users/0/items?limit={limit}&sort=dateAdded&direction=desc&itemType=-attachment"
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except Exception:
        return []


def add_item_to_collection(item_key, collection_key, version):
    """Add an existing item to a collection."""
    url = f"{ZOTERO_LOCAL}/api/users/0/items/{item_key}"
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        item = json.loads(resp.read().decode())
    except Exception:
        return False

    data = item.get("data", item)
    cols = data.get("collections", [])
    if collection_key not in cols:
        cols.append(collection_key)
    data["collections"] = cols

    patch_body = json.dumps(data).encode()
    patch_req = urllib.request.Request(
        url, data=patch_body, method="PATCH",
        headers={
            "Content-Type": "application/json",
            "If-Unmodified-Since-Version": str(data.get("version", version)),
        },
    )
    try:
        urllib.request.urlopen(patch_req, timeout=15)
        return True
    except Exception:
        return False


def parse_dois_file(lines):
    """Parse the dois.txt format into sections."""
    project = lines[0].strip()
    sections = []
    current_sub = None
    current_topic = None
    current_dois = []

    i = 1
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            # blank line — flush current section if we have DOIs
            if current_sub and current_topic and current_dois:
                sections.append((current_sub, current_topic, list(current_dois)))
                current_dois = []
                current_sub = None
                current_topic = None
            i += 1
            continue

        if line.startswith("#"):
            i += 1
            continue

        # if we don't have sub yet, this line is the sub-project
        if current_sub is None:
            current_sub = line
            i += 1
            continue

        # if we don't have topic yet, this line is the topic
        if current_topic is None:
            current_topic = line
            i += 1
            continue

        # otherwise it's a DOI/ISBN
        if "#" in line:
            id_part, comment = line.split("#", 1)
            id_part = id_part.strip()
            comment = comment.strip()
        else:
            id_part, comment = line, ""

        current_dois.append((id_part, comment))
        i += 1

    # flush last section
    if current_sub and current_topic and current_dois:
        sections.append((current_sub, current_topic, list(current_dois)))

    return project, sections


def main():
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        filepath = sys.argv[1]
    elif os.path.isfile(DEFAULT_FILE):
        filepath = DEFAULT_FILE
    else:
        print(f"No input. Create {DEFAULT_FILE} or pass a file as argument.")
        return

    with open(filepath) as f:
        lines = f.readlines()

    if not lines:
        print("Empty file.")
        return

    project, sections = parse_dois_file(lines)
    total = sum(len(dois) for _, _, dois in sections)
    print(f"Project: {project}")
    print(f"Sections: {len(sections)}, Total items: {total}\n")

    if not ping():
        print("ERROR: Zotero not reachable at localhost:23119")
        return

    failed = []
    count = 0

    for sub, topic, dois in sections:
        path = [ROOT_COLLECTION, project, sub, topic]
        print(f"\n--- {' / '.join(path)} ---")
        col_key = ensure_collection_path(path)
        if not col_key:
            print(f"  Skipping section (collection creation failed)")
            for id_, label in dois:
                failed.append((id_, label, "/".join(path)))
            continue

        for id_, label in dois:
            count += 1
            display = label or id_
            print(f"  [{count}/{total}] {display}")

            # snapshot items before save
            before = {item.get("data", item).get("key", item.get("key"))
                      for item in get_recent_items(3)}

            if id_.lower().startswith("isbn:"):
                isbn = id_[5:].strip()
                uri = f"https://www.worldcat.org/isbn/{isbn}"
            else:
                uri = f"https://doi.org/{id_}"

            status = save_via_connector(uri)

            if status in (200, 201):
                # find the newly added item
                time.sleep(1)
                after = get_recent_items(5)
                new_item = None
                for item in after:
                    d = item.get("data", item)
                    k = d.get("key", item.get("key"))
                    if k not in before:
                        new_item = d
                        break

                if new_item and col_key:
                    moved = add_item_to_collection(
                        new_item["key"], col_key, new_item.get("version", 0)
                    )
                    if moved:
                        print(f"    OK -> {'/'.join(path)}")
                    else:
                        print(f"    OK (saved but couldn't move to collection)")
                else:
                    print(f"    OK (couldn't identify new item for collection)")
            else:
                print(f"    FAILED ({status})")
                failed.append((id_, display, "/".join(path)))

            if count < total:
                time.sleep(SLEEP)

    if failed:
        print(f"\n{'='*50}")
        print(f"{len(failed)} failed — add manually:")
        for id_, label, path in failed:
            print(f"  {id_}  # {label} -> {path}")
    else:
        print(f"\nAll {total} items added!")


if __name__ == "__main__":
    main()
