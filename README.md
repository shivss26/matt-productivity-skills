# matt-productivity-skills

A personal Claude plugin marketplace that installs **only** the productivity skills from
[mattpocock/skills](https://github.com/mattpocock/skills) (`skills/productivity`). It follows Matt's
**releases**, not his `main` branch, and a GitHub Action keeps it pinned to the latest one.

Skills you get: `grill-me`, `grilling`, `handoff`, `teach`, `to-questionnaire`, `wait-what`,
`writing-for-agents` (whatever is in `skills/productivity` at the pinned release).

## Install

1. Customize → Plugins → Add → **Add marketplace** → Add from a repository →
   `shivss26/matt-productivity-skills`.
2. Install **Matt productivity skills**.

## Updating the plugin in claude.ai (two manual steps)

When the Action pins a new release (see below), claude.ai does **not** pick it up on its own. Do both steps:

1. Desktop app, Chat/Cowork tab → **Settings → Plugins → Manage marketplaces** → `matt-productivity-skills` → **Check for updates**
2. **Settings → Plugins → Matt productivity skills** → **Check for updates** → **Update**

Step 1 makes claude.ai re-read this repo and see the new pinned release. Step 2 installs it.

## Why this setup exists

### Why not install Matt's marketplace directly?

Matt's repo publishes a single plugin, `mattpocock-skills`, whose `plugin.json` lists all ~27 skills
(engineering and productivity together). A plugin installs as a whole, so there's no way to take only part of it.

This repo is a one-entry marketplace whose plugin points at just the `skills/productivity` folder of
Matt's repo, using a `git-subdir` source. Nothing is forked or copied.

### Why pin to releases instead of tracking `main`?

Commits land on Matt's `main` between releases, and a commit can introduce a regression that later gets
reverted. Matt cuts a GitHub Release (`v1.3.1`, `v1.3.0`, …, via changesets) once a batch of changes is
stable, so pinning to releases means you only get changes he has signed off on.

Trade-off: skill fixes merged after the latest release don't reach you until the next one.

### Why a GitHub Action is needed at all

We tested this end to end on claude.ai with a throwaway probe plugin (2026-10-11). claude.ai keeps its
**own stored copy** of each plugin. It re-reads the upstream repo (Matt's) only when **this** marketplace repo
changes. Specifically:

| Change | Does claude.ai update? |
|---|---|
| New commits in the upstream repo (content only) | No, not even with Check for updates |
| Upstream version bump / new upstream commit, this repo unchanged | No, not even with Check for updates |
| Commit to **this** repo (pin changes), then the two manual steps above | **Yes** |
| Commit to this repo, no manual steps (even with "Sync automatically" on) | No (not within 10+ minutes) |
| Removing and re-adding the marketplace | Yes (fetches the current upstream state) |

So if this repo never changed, the plugin would stay frozen forever. The Action's job is to change this repo
exactly when Matt releases, so that **Check for updates** has something to find.

## How the GitHub Action works

[`.github/workflows/pin-releases.yml`](.github/workflows/pin-releases.yml) runs
[`.github/scripts/pin_releases.py`](.github/scripts/pin_releases.py):

1. **Daily at 06:17 UTC** (11:47 IST) it reads `.claude-plugin/marketplace.json`.
2. For each plugin whose source is a github.com repo, it asks the GitHub API for that repo's
   **latest published release** (drafts and pre-releases are skipped).
3. If that release differs from what's pinned, it updates the entry's `source.ref` (the tag),
   `source.sha` (the tag's exact commit) and `version`, then commits and pushes as `github-actions[bot]`.
4. If nothing changed, it does nothing. No commit, no noise.

Pinning `sha` as well as `ref` means claude.ai fetches exactly the released commit, even if the tag
were later moved.

You can also run it on demand: Actions tab → *Pin plugin sources to latest releases* → **Run workflow**,
or `gh workflow run pin-releases.yml`.

### Failsafe: the monthly heartbeat commit

GitHub **automatically disables scheduled workflows in public repos after 60 days without repository activity**
([GitHub docs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)).
This repo only changes when Matt releases, and his gaps between releases have been close to two months
(e.g. 2026-08-06 → 2026-09-29), so the daily check could silently switch itself off.

To prevent that, a second schedule runs **on the 1st of every month at 06:00 UTC** and writes the current
timestamp to [`.github/heartbeat`](.github/heartbeat), committing it. That counts as activity and keeps the
schedule alive. A heartbeat commit doesn't change any plugin, so Check for updates will find nothing new
after one.

## Things to know

- **Schedule delays.** GitHub can delay scheduled runs under load and occasionally drops them. A missed
  day is picked up the next day.
- **Upstream restructuring.** If Matt renames or moves `skills/productivity`, the fetch fails at the next
  update. claude.ai keeps the last version it synced successfully. Fix the `path` in `marketplace.json`.
- **Releases without productivity changes.** Most of Matt's releases touch engineering skills only. The pin
  still moves, and updating is harmless (same content).
- **Rolling back or holding a version.** Edit `ref`/`sha`/`version` in `marketplace.json` by hand.
  The Action will move it forward again at the next release, so disable the workflow (Actions tab → … →
  Disable workflow) if you want to hold.

## claude.ai quirks we hit (for future reference)

- Entries with no `plugin.json` in the source folder need `"strict": false`, or claude.ai rejects them
  (`marketplace_sync_plugin_missing_manifest`). Claude Code doesn't require this.
- `git-subdir` sources need a full `https://…git` URL. The `owner/repo` shorthand fails on claude.ai's server.
- The add dialog only says "Marketplace sync failed. Check the repository URL". The real reason is in the
  `sync_errors` field of the `…/marketplaces/<id>/account-get` API response (visible in the browser's network tab).
