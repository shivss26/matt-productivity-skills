"""Pin each GitHub-hosted plugin source in marketplace.json to its latest release.

For every plugin entry whose source is a github.com repo, look up the repo's
latest published release (drafts and pre-releases excluded). If it differs from
what is pinned, set the entry's ref, sha and version to that release. Repos with
no releases are left alone. Prints "changed=true|false" for the workflow.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

MARKETPLACE = ".claude-plugin/marketplace.json"
GITHUB_URL = re.compile(r"^(?:https://github\.com/)?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if token := os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def repo_of(source):
    if source.get("source") == "github":
        target = source.get("repo", "")
    elif source.get("source") in ("git-subdir", "url"):
        target = source.get("url", "")
    else:
        return None
    m = GITHUB_URL.match(target)
    return (m.group(1), m.group(2)) if m else None


def main():
    with open(MARKETPLACE) as f:
        data = json.load(f)

    changed = False
    for entry in data.get("plugins", []):
        source = entry.get("source")
        repo = repo_of(source) if isinstance(source, dict) else None
        if not repo:
            continue
        owner, name = repo
        release = api(f"/repos/{owner}/{name}/releases/latest")
        if not release:
            print(f"{entry['name']}: {owner}/{name} has no releases, leaving as is")
            continue
        tag = release["tag_name"]
        sha = api(f"/repos/{owner}/{name}/commits/{tag}")["sha"]
        if source.get("ref") == tag and source.get("sha") == sha:
            print(f"{entry['name']}: already pinned to {tag}")
            continue
        print(f"{entry['name']}: {source.get('ref', 'unpinned')} -> {tag} ({sha[:7]})")
        source["ref"] = tag
        source["sha"] = sha
        entry["version"] = tag.lstrip("v")
        changed = True

    if changed:
        with open(MARKETPLACE, "w") as f:
            f.write(json.dumps(data, indent=2) + "\n")
    print(f"changed={'true' if changed else 'false'}")
    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")


if __name__ == "__main__":
    sys.exit(main())
