# Home Assistant Core contribution

This folder holds the changes being upstreamed to the official
[`pulseaudio_loopback`](https://www.home-assistant.io/integrations/pulseaudio_loopback/)
integration in [home-assistant/core](https://github.com/home-assistant/core).
The HACS package in `custom_components/` is not affected by anything in here.

The layout mirrors the core repository, so every file can be copied 1:1:

```
core/
├── BASE_COMMIT                 upstream commit the files were written against
├── sync.sh                     copies the files into a core checkout
├── homeassistant/components/pulseaudio_loopback/
├── tests/components/pulseaudio_loopback/
└── pull_requests/              descriptions for the pull requests
```

## Workflow

1. Update the fork (`seb5594/hass-core`) and create a branch from `dev`.
2. Copy the files: `core/sync.sh ../hass-core`.
   The script refuses to copy if upstream changed the integration since
   `BASE_COMMIT`; port those changes first.
3. Run the checks in the core checkout:
   `pytest tests/components/pulseaudio_loopback` and
   `prek run --all-files` (or `ruff check` + `ruff format`).
4. Commit, push, and open the pull request with the matching text from
   `pull_requests/`.

## Roadmap

Changes to the YAML configuration of this integration are no longer accepted
upstream ([ADR-0010](https://github.com/home-assistant/architecture/blob/master/adr/0010-integration-configuration.md);
an earlier attempt was turned down for exactly that reason in
home-assistant/core#35973). The extended options therefore reach core only
after the integration has a config flow, and each step is kept small enough to
review in one sitting.

| # | Pull request | Type | Status |
|---|--------------|------|--------|
| 1 | Match loopback modules by exact sink and source | Bugfix | ready |
| 2 | Add config flow with YAML import and code owner | New feature | planned |
| 3 | Options flow: latency and adjust time | New feature | planned |
| 4 | Options flow: `sink_dont_move` / `source_dont_move` | New feature | planned |
| 5 | Options flow: rate, channels, format, remix | New feature | planned |

Open the next pull request only after the previous one is merged.
