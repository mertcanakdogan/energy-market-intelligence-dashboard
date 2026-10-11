# Deploying the dashboard

The Streamlit app can run locally or on Streamlit Community Cloud. No API keys, secrets, external
databases or paid services are needed: all data are synthetic and generated deterministically.

**Live demo:** not published yet. Once deployed, add the public app URL here and in the README.

## How the app finds its data

`dashboard_support.py` opens a DuckDB file read-only. Resolution order:

1. `EMID_DATABASE_PATH` environment variable, if set.
2. `data/energy_market.duckdb` in the repository (created by the pipeline).
3. If that file does not exist, the app builds it on first start by calling
   `energy_market_intelligence.pipeline.build_dataset` (about 10 to 30 seconds, shown as a
   spinner) and then reuses it. If the repository directory is read-only, the database is
   written to the system temp directory instead.

The first-start build does not touch `outputs/examples/`, so running the app locally never
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
5. Open **Advanced settings** and select **Python 3.12** (the version used by CI). No secrets are
   needed.
6. Deploy. Dependencies come from `requirements.txt`, which installs the project itself
   (`.`) and therefore everything declared in `pyproject.toml`. Kaleido and the other dev
   tools are not installed, because PNG export is only used by the pipeline.
7. The first page load builds the synthetic database, so allow up to a minute. Later visits reuse
   it until the app container is recycled.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Spinner never finishes | Check the app logs for the traceback; the pipeline needs about 1 GB of memory. |
| `Could not create the analytical database` | Neither the repository nor the temp directory is writable. Set `EMID_DATABASE_PATH` to a writable path. |
| Stale numbers after changing `config/default.yaml` | Delete `data/energy_market.duckdb` (and the temp copy) and clear the Streamlit cache. |
| `ModuleNotFoundError: energy_market_intelligence` | `requirements.txt` was not picked up; confirm it contains a single `.` line. |
