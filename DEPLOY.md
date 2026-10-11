# Deploying the dashboard

The Streamlit app can run locally or on Streamlit Community Cloud. No API keys, secrets, external
databases or paid services are needed: all data are synthetic and generated deterministically.

**Live demo:** <https://tavra-energy-pricing.streamlit.app> (deploys from branch `main`, main file `app.py`). The app text is in English. The subdomain `tavra-energy-pricing` is not part of the code: it is set in the app's settings on Streamlit Community Cloud (**Settings** > **General** > **App URL**), so change it there if the link above ever differs. From version 2.3.0 on, (re)deploy the app under this new subdomain; the old subdomain is no longer used.

## How the app finds its data

`dashboard_support.py` opens a DuckDB file read-only. Resolution order:

1. `EMID_DATABASE_PATH` environment variable, if set.
2. `data/energy_market.duckdb` in the repository (created by the pipeline).
3. If that file does not exist, the app builds it on first start by calling
   `energy_market_intelligence.pipeline.build_dataset` (about 10 to 30 seconds, shown as a
   spinner) and then reuses it. If the repository directory is read-only, the database is
   written to the system temp directory instead.

The app navigation (`st.navigation`) is defined in `app.py` and `dashboard_support.PAGE_SPECS`. The six pages live in `views/`. The first-start build does not touch `outputs/examples/`, so running the app locally never
modifies tracked files.

## Local run

```bash
python -m pip install -e ".[dev]"
python -m energy_market_intelligence.pipeline   # optional: also writes outputs/ and powerbi/data/
streamlit run app.py
```

## Streamlit Community Cloud

1. Push the repository to GitHub (a public repository is required on the free tier).
2. Sign in at <https://share.streamlit.io> with GitHub and choose **Create app** > **Deploy a
   public app from GitHub**.
3. Select the repository and branch `main`.
4. Set **Main file path** to `app.py`.
5. Open **Advanced settings** and select **Python 3.14** (the main version in CI; DuckDB has no Python 3.15 wheels yet). No secrets are
   needed.
6. Deploy. Dependencies come from `requirements.txt`, which installs the project itself in
   editable mode (`-e .`) and therefore everything declared in `pyproject.toml`. Editable matters:
   Streamlit Cloud pulls new commits without reinstalling, so a regular install would keep
   importing the package as it was at first deploy. Kaleido and the other dev
   tools are not installed, because PNG export is only used by the pipeline.
7. The first page load builds the synthetic database, so allow up to a minute. Later visits reuse
   it until the app container is recycled.

## Design notes

The look of the app (colour tokens, fonts, the bill block) is documented in [DESIGN.md](DESIGN.md). Two deployment-relevant points:

- The app uses two system fonts, Arial and Georgia, set through the native `font`, `headingFont` and `codeFont` options in `.streamlit/config.toml` and in the app's CSS. Nothing is downloaded or bundled. Where Arial is missing (some Linux phones and desktops), the browser uses Helvetica or the system sans-serif.
- The theme is light only; there is no dark-mode variant.
- The PNG charts in `outputs/examples/` are rendered by Kaleido, which only sees fonts installed on the machine. Arial and Georgia ship with Windows and macOS, so the charts match the app there without extra steps; on Linux, install them first (for example the `ttf-mscorefonts-installer` package).

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Spinner never finishes | Check the app logs for the traceback; the pipeline needs about 1 GB of memory. |
| `Could not create the analytical database` | Neither the repository nor the temp directory is writable. Set `EMID_DATABASE_PATH` to a writable path. |
| Old page names (`app`, `price waterfall`) in the sidebar | Browser cache of an older deployment; reload the page. Version 2.1.0 replaced the `pages/` directory with `st.navigation`. |
| Turkish names or more than six pages after updating to 2.3.0 | The app still serves an older build. The database rebuilds itself when `DATASET_VERSION` changes; if the old pages remain, reboot the app from **Manage app**. |
| `KeyError: 'energy_market_intelligence...'` in the logs, or new pages with old wording after a push | Streamlit reloaded the pages but kept the package modules it had already imported. Reboot the app from **Manage app**. |
| Stale numbers after changing `config/default.yaml` | Delete `data/energy_market.duckdb` (and the temp copy) and clear the Streamlit cache. |
| `ModuleNotFoundError: energy_market_intelligence` (or one of its modules) | `requirements.txt` was not picked up, or the package was installed non-editable before a module was added; confirm it contains `-e .`, then reboot the app from **Manage app**. |
