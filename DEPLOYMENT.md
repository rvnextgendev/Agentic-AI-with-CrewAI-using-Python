# Streamlit setup and deployment

## Run locally

Use Python 3.11 and the existing virtual environment:

```powershell
.\run_streamlit.ps1 -InstallDependencies
```

This launcher checks Python 3.11, installs the shared requirements, and starts
the UI. Subsequent runs can use `.\run_streamlit.ps1` without reinstalling.
Install Python 3.11 first if it is unavailable. The launcher creates `venv`
only if it is missing and does not replace an existing environment.

The direct launch command remains:

```powershell
& ".\venv\Scripts\python.exe" -m streamlit run streamlit_app.py
```

Open http://localhost:8501. Your existing `.env` supplies the Groq and Serper
keys. Submit a topic, follow the five stages, review and edit the optimized
post, then download the report as text or JSON. Edited post text is included
in downloads. Results stay in your browser session across widget reruns;
refreshing or closing the session can discard them. Download anything you need
to keep. Nothing is published to LinkedIn automatically.

## Prepare the repository

The repository now excludes `.env` and logs from tracking. If you are using an
older checkout that still tracks `.env`, remove it from tracking while keeping
the local copy:

```powershell
git rm --cached -- .env
```

Review your staged changes before committing. `.gitignore` excludes `.env`,
`.streamlit/secrets.toml`, virtual environments, caches, and logs from new
additions. Rotate any key previously exposed in chat or committed to Git;
removing a file does not remove it from repository history.

## Deploy to Streamlit Community Cloud

**The supplied Cloud logs show Python 3.14.8. That runtime cannot install this
project's pinned CrewAI and ONNX dependencies.** Changing package versions one
at a time will not make the current stack compatible with Python 3.14.

For an existing failed deployment, first save its repository, branch,
entrypoint, custom URL, and secrets. Delete that deployment and recreate it
using Python 3.11 in step 4 below. Rebooting or pushing changes to GitHub does
not change an existing deployment's Python version. See
[Streamlit's runtime-change instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-python).

`.python-version` specifies 3.11 for local tools that honor it; it does **not**
override Streamlit Community Cloud's dashboard setting. Both environments
install the same root `requirements.txt`.

1. Push the application code and `requirements.txt` to your GitHub repository.
2. Open https://share.streamlit.io and choose **Create app**.
3. Select the repository and branch. Set the entrypoint to `streamlit_app.py`.
4. In **Advanced settings**, select **Python 3.11** for this dependency stack.
5. Paste the template below into **Secrets**, replacing placeholders. Use a
   strong `APP_PASSWORD` to restrict access to the deployment and API quota.
6. Deploy, review the build logs, sign in with your access password, and try a
   simple topic. Confirm the build log says `Using Python 3.11` before
   troubleshooting any other installation error.

For this repository, use:

- Repository: `rvnextgendev/Agentic-AI-with-CrewAI-using-Python`
- Branch: `main`
- Entrypoint: `streamlit_app.py`
- Python: **3.11**

```toml
LLM_PROVIDER = "groq"
GROQ_API_KEY = "your_replacement_groq_key"
LLM_MODEL = "qwen/qwen3.8-27b"
SERPER_API_KEY = "your_serper_key"
APP_PASSWORD = "your_strong_access_password"
```

The same template is in `.streamlit/secrets.example.toml`. Keep real secrets
in Cloud settings, never in a committed file. For local password testing,
add `APP_PASSWORD=your_password` to `.env` or use a local secrets file.

Cloud root-level secrets are exposed as environment variables before the
pipeline loads. The local `.env` supplies only missing environment values, so
Cloud credentials take priority. Cloud cannot read your local `.env`. Use the
same variable names in both locations, and update rotated credentials in each.

Free-tier limits can pause generation. One pipeline runs at a time per server
process; another visitor receives a busy message. Task results and errors are
kept in the current session only. This is a small shared workspace, not a
multi-user publishing service. The password is a shared access gate, not
individual user accounts. Review generated factual claims before publishing.

If Groq returns `model_permission_blocked_project`, a project admin must enable
`qwen/qwen3.8-27b` at https://console.groq.com/settings/project/limits. A valid
key alone does not grant model access. GPT-OSS is blocked by this app's
configuration check because it fails with the legacy text-tool protocol.
Provider `output_parse_failed` errors receive one retry with a clearer
formatting instruction. If the retry also fails, the error remains visible;
failed generations are never treated as valid tool actions.

See the [official deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
for current repository, Python version, and secrets settings.

## Verify changes without API calls

```powershell
& ".\venv\Scripts\python.exe" -m unittest discover -s tests -v
& ".\venv\Scripts\python.exe" -m pip check
```

UI tests mock generation and do not spend API quota. The CLI remains available
through `linkedin_content_manager_advanced.py`.

GitHub Actions checks installation, native-library imports, and tests on
Windows and Ubuntu with Python 3.11. Review the workflow result after pushing;
a successful local check alone does not verify a fresh Cloud installation.
