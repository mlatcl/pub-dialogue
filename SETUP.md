# Setting up the project on your laptop

This guide is written for people who have not used Python or the command line
before. It walks you through every step from a fresh laptop to running the
analysis notebooks.

**Time**: about 20 minutes for a first-time setup.  
**Operating system**: macOS (primary). Windows and Linux steps are also shown
where they differ.

---

## Before you start

**What is Python?** Python is the programming language the analysis is written
in. It needs to be installed on your laptop before you can run anything.

**What is the terminal?** The terminal (also called the command line) is a text
window where you type instructions to your computer. It looks unfamiliar at
first, but you only need a handful of commands — all of them are given here,
ready to copy and paste.

**What are packages?** The analysis uses several add-on libraries (packages)
that extend what Python can do. You install them once; after that they are just
there.

---

## Step 1 — Open the terminal

Everything in this guide happens inside the terminal. Start here.

**macOS**: press `Cmd + Space` to open Spotlight, type `Terminal`, and press
Return. Alternatively: Finder → Applications → Utilities → Terminal.

**Windows**: *(instructions coming soon)*

A window appears with a prompt that ends in `$` (macOS) or `>` (Windows). That
prompt is waiting for you to type a command. Type a command and press Return to
run it. If something goes wrong mid-command, press `Ctrl + C` to cancel and
return to the prompt.

Leave this window open for the rest of the guide — every command below is
entered here.

---

## Step 2 — Install Python

Check whether Python 3.10 or newer is already on your machine. In the terminal:

```
python3 --version
```

If the output says `Python 3.10.x` or higher, you already have a usable Python
and can skip to Step 3.

If the command is not found, or the version is lower than 3.10:

**macOS**: go to [python.org/downloads](https://www.python.org/downloads/) and
download the macOS installer (a `.pkg` file). Open it and follow the install
wizard — it works like any other macOS application installer.

> macOS ships with an old Python 2 that cannot be used for this project. The
> installer from python.org adds a separate, up-to-date Python 3 alongside it
> without removing anything.

**Windows**: *(instructions coming soon)*

Run `python3 --version` again to confirm the install worked. It should now
print `3.10` or higher.

---

## Step 3 — Get the project files

This project is managed with **git**, a tool that tracks changes to files and
lets you download updates with a single command.

Check whether git is already installed:

```
git --version
```

**macOS**: git is usually pre-installed. If not, running `git --version` will
trigger a macOS prompt offering to install the Xcode Command Line Tools — accept
it and wait for it to finish, then re-run `git --version` to confirm.

**Windows**: *(instructions coming soon)*

Once git is available, **clone** (download) the project:

```
git clone https://github.com/mlatcl/pub-dialogue.git
```

This creates a `pub-dialogue` folder in your home directory. Move into it:

```
cd pub-dialogue
```

```
ls
```

You should see `README.md` listed in the output. If you do, you are in the
right place.

> **Pulling future updates**: when the project is updated, open the terminal,
> `cd pub-dialogue`, and run `git pull` to download the latest changes.

---

## Step 4 — Create a virtual environment

A virtual environment is a private, isolated copy of Python created just for
this project. Installing packages inside it will not affect anything else on
your laptop, and nothing installed elsewhere on your laptop can interfere with
this project.

Create one now (still in the project folder):

```
python3 -m venv .venv
```

This creates a hidden folder called `.venv` inside the project. It will not
be uploaded to GitHub (it is listed in `.gitignore`), so you only need to
create it once on your own machine.

---

## Step 5 — Activate the environment

Activating the environment tells your terminal to use the project's private
Python rather than the system one.

```
source .venv/bin/activate
```

> **Windows**: *(instructions coming soon)*

After activation, your terminal prompt will change to show `(.venv)` at the
start, like this:

```
(.venv) your-computer:pub-dialogue you$
```

That prefix is your confirmation that the environment is active. **You will
need to run the activate command every time you open a new terminal window**
before working on this project.

---

## Step 6 — Install the project packages

With the environment active, install all the Python libraries the project
needs:

```
pip install -e ".[dev]"
```

This command reads the list of required packages from `pyproject.toml` and
downloads them. It may take a few minutes and will print a lot of text —
that is normal. When it finishes you should see a line like
`Successfully installed pub-dialogue-0.1.0 ...`.

---

## Step 7 — Get an OpenAI API key

The analysis notebooks call OpenAI's API to extract concerns and benefits from
text. An API key is a private password that lets the software connect to
OpenAI on your behalf.

1. Go to [platform.openai.com](https://platform.openai.com) and sign in (or
   create a free account).
2. Click your name in the top-right corner, then choose **API keys**.
3. Click **Create new secret key**, give it a name (e.g. "pub-dialogue"), and
   click Create.
4. **Copy the key immediately** — OpenAI only shows it once. Paste it into a
   temporary note; you will move it to a file in the next step.

> **Billing**: running `01_processing.ipynb` (the notebook that calls the API)
> costs roughly $2–5 in API credits for the full corpus. Subsequent notebooks
> load pre-computed results and do not call the API at all.
> To add credit, go to **Settings → Billing** on platform.openai.com and add
> a small amount (e.g. $10) before running the processing notebook for the
> first time.

---

## Step 8 — Configure your API key

The project reads your API key from a file called `.env` in the project folder.
This file is intentionally excluded from git (it is in `.gitignore`) so your
key is never accidentally shared.

Create the file by copying the provided template:

```
cp .env.example .env
```

> **Windows**: *(instructions coming soon)*

Now open `.env` in a text editor. Run this in the terminal:

```
open -e .env
```

(If Finder hides the file because its name starts with a dot, press
`Cmd + Shift + .` in any Finder window to toggle hidden files.)

Find the line that reads:

```
OPENAI_API_KEY=sk-...
```

Replace `sk-...` with the key you copied in Step 7. Save and close the file.

> **Keep this file private.** Do not paste the contents into Slack, email, a
> chat window, or a notebook cell. If you accidentally share the key, go to
> platform.openai.com → API keys and delete it immediately, then create a
> new one.

---

## Step 9 — Launch Jupyter and run the notebooks

Make sure your virtual environment is still active (you should see `(.venv)`
in the prompt). Then start Jupyter:

```
jupyter notebook
```

A browser tab will open showing the project files. Click on a notebook to
open it — start with `01_processing.ipynb` to build the outputs that all
later notebooks depend on.

Inside the notebook, run a cell by clicking on it and pressing **Shift +
Enter**. To run all cells from top to bottom, use the menu:
**Cell → Run All** (classic Jupyter) or **Run → Run All Cells** (JupyterLab).

> **Alternative — VS Code**: if you prefer to use VS Code, open the project
> folder in VS Code. When you open a `.ipynb` file it will ask you to install
> the Jupyter extension — click Install. Select the `.venv` kernel when
> prompted (look for a "Select Kernel" button near the top-right of the
> notebook).

**Notebook order**:

| Notebook | What it does |
|---|---|
| `01_processing.ipynb` | Extracts concerns and benefits (calls the API — run first) |
| `01a_clustering.ipynb` | Clusters the extracted phrases |
| `02_shared_structure.ipynb` | Identifies cross-cutting themes |
| `03_ai_distinctiveness.ipynb` | AI-specific analysis |
| `04_temporal_dynamics.ipynb` | Trends over time |
| `05_robustness.ipynb` | Sensitivity checks |

Notebooks `02` through `05` load pre-computed files from `outputs/` and do
not call the API, so they run quickly.

---

## Troubleshooting

| What you see | Likely cause | What to do |
|---|---|---|
| `git: command not found` | Git not installed | Run `git --version` to trigger the Xcode Tools prompt; accept and wait |
| `python3: command not found` | Python not installed | Download and run the installer from python.org |
| No `(.venv)` in your prompt | Virtual environment not activated | Run `source .venv/bin/activate` from Step 5 again |
| `ModuleNotFoundError: No module named 'pub_dialogue'` | Packages not installed, or venv not active | Activate the venv (Step 5) then re-run `pip install -e ".[dev]"` |
| `AuthenticationError` from OpenAI | API key missing or incorrect | Open `.env` and check the key has no extra spaces or line breaks |
| `jupyter: command not found` | Packages not installed, or venv not active | Same fix as the `ModuleNotFoundError` row above |
| `.env` not visible in Finder | Finder hides files starting with `.` | Press `Cmd + Shift + .` to toggle hidden files |

---

If you get stuck, check that:

1. The terminal prompt shows `(.venv)` — if not, re-run the activate command.
2. You are in the project folder — run `ls` / `dir` and confirm `README.md` is listed.
3. The `.env` file exists and contains your key — run `cat .env` (macOS/Linux)
   or `type .env` (Windows) to view its contents.
