# 🛡️ Log Guard

[![Tests](https://github.com/apurvaraj9/log-guard/actions/workflows/tests.yml/badge.svg)](https://github.com/apurvaraj9/log-guard/actions/workflows/tests.yml) [![PyPI version](https://img.shields.io/pypi/v/logguard-cli)](https://pypi.org/project/logguard-cli/)

**A local, offline tool that scans server log files — and Excel spreadsheets — and masks sensitive data before you share them for debugging.**

No uploads. No third-party servers. No enterprise pricing. Your data never leaves your machine.

---

## Why Log Guard?

When you're debugging with a teammate, posting to a forum, or filing a support ticket, you often need to share a log file or a spreadsheet export — but real data is full of things you *shouldn't* share: customer emails, phone numbers, API keys, IP addresses, credit card numbers.

- **Online masking tools** require uploading your private data to a third-party server — a privacy risk in itself.
- **Enterprise security tools** solve this, but are expensive, complex, and overkill for an individual developer or small team.

**Log Guard** runs 100% locally, does one job well, and stays simple.

## Features

- 🔍 **Detects and masks:** emails, phone numbers, API keys (Stripe/AWS/GitHub formats + a generic long-token fallback), IP addresses, and credit card numbers (Visa/Mastercard/Amex/Discover)
- 📗 **Excel spreadsheet support** — scans every cell of every sheet in `.xlsx` files (hidden sheets included) and writes a masked copy you can open in Excel
- 📁 **Scans whole directories**, recursively by default — point it at a `logs/` folder and it finds everything inside, spreadsheets included
- 🧩 **Custom patterns** via a simple JSON file — add your own detection rules with no code changes (they apply to spreadsheets too)
- ⚙️ **Config file support** (`.log-guard.json`) — set project-level defaults for extensions, recursion, custom patterns, and quiet mode; CLI flags always override it
- 🚦 **CI / pre-commit mode** (`--check`) — scans without writing files and exits with status code `1` if secrets are found, so it can block a commit or fail a build. Ships with a ready-to-use `.pre-commit-hooks.yaml`
- 📄 **Non-destructive** — writes a new `*.masked.log` / `*.masked.xlsx` file (or a path you choose with `-o`); your original is never touched, and a clean file with nothing to mask doesn't get a redundant copy
- 📊 **Summary report** — see exactly how many of each type were found
- 🧪 **Fully tested** — 65+ automated tests covering detection, masking, spreadsheets, directory scanning, config parsing, and a wide range of edge cases, run automatically on every push via GitHub Actions across Python 3.9–3.12
- 💻 **Handles edge cases** — empty files, huge log files (streamed line-by-line), unusual encodings, mixed line endings, corrupt or password-protected spreadsheets, and directories with zero matching files
- 🚫 **Smart defaults for directories** — automatically skips `.git`, `node_modules`, `venv`, `.venv`, and `__pycache__` while recursing (use `--ext all` to scan every file if you really want to)
- ⚡ **Zero network calls, ever**

## Installation

```bash
pip install logguard-cli
```

That's it — this installs the `log-guard` command. (The package is named `logguard-cli` on PyPI because the name `log-guard` was already taken, but the command you run is still `log-guard`.)

It also automatically installs two small libraries used for `.xlsx` support: `openpyxl` (reads and writes spreadsheets) and `defusedxml` (protects against maliciously crafted files). Both work fully offline.

Requires Python 3.9 or newer.

> **Note:** if `log-guard` isn't recognized as a command right after installing, your Python Scripts folder probably isn't on your system PATH. Either add it to PATH, or run the tool with `python -m log_guard` instead — both work identically.

### Installing from source (for development)

```bash
git clone https://github.com/apurvaraj9/log-guard.git
cd log-guard
pip install -e .
```

This installs Log Guard as an editable package, so any changes you make to the code take effect immediately.

## Usage

**Scan a single file:**

```bash
log-guard your.log
```

Creates `your.masked.log` alongside the original (unless nothing was found — then no output file is created, to avoid clutter).

**Scan an Excel spreadsheet (`.xlsx`):**

```bash
log-guard data.xlsx
```

```
Scanned 29 cells across 4 sheet(s) in data.xlsx
Masked spreadsheet written to data.masked.xlsx
```

Creates `data.masked.xlsx` — a real spreadsheet you can open in Excel. Every cell on every sheet is checked, including hidden sheets. Text cells and whole numbers (like a phone number typed as `5551234567`) are scanned; formulas, dates, and decimals are left untouched. `--check`, `--quiet`, `-o`, custom patterns, and the config file all work exactly as they do for text files.

Old `.xls` files (Excel 97–2003) aren't supported — open them in Excel and use **File > Save As** to save them as `.xlsx` first.

**Scan an entire directory (recursive by default):**

```bash
log-guard logs/
```

By default this scans `.log`, `.txt`, `.csv`, `.json`, `.out`, `.err`, and `.xlsx` files, skipping `.git`/`node_modules`/`venv`/`__pycache__` automatically.

```bash
log-guard logs/ --ext log,txt --no-recursive   # only .log/.txt, top level only
log-guard logs/ --ext all                       # scan every file, any extension
```

**Choose a specific output path:**

```bash
log-guard your.log -o cleaned.log
```

(Only valid for a single input file.)

**CI / pre-commit mode** — scans without writing files, exits `1` if anything is found:

```bash
log-guard logs/*.log --check
```

Add `--quiet` for a condensed summary suited to CI logs. To use Log Guard as an actual [pre-commit](https://pre-commit.com) hook in any repo (it checks staged `.log` and `.xlsx` files):

```yaml
repos:
  - repo: https://github.com/apurvaraj9/log-guard
    rev: v0.1.0
    hooks:
      - id: log-guard
```

**Custom detection patterns:**

```json
// custom_patterns.json
{
  "employee_id": "EMP-\\d{6}"
}
```

```bash
log-guard your.log --patterns custom_patterns.json
```

**Project-level config file** — create `.log-guard.json` in your project root to set defaults (CLI flags always override these):

```json
{
  "extensions": ["log", "txt"],
  "recursive": false,
  "patterns": "custom_patterns.json",
  "quiet": false
}
```

An example is included as `.log-guard.json.example` — copy it to `.log-guard.json` and adjust as needed.

### Example

**Before:**
```
2024-01-15 10:22:31 INFO User login successful for john.doe@example.com
2024-01-15 10:23:02 DEBUG API request with key sk_live_51Hz8f92jak3ndlka9d
```

**After:**
```
2024-01-15 10:22:31 INFO User login successful for [EMAIL_REDACTED]
2024-01-15 10:23:02 DEBUG API request with key [API_KEY_REDACTED]
```

## Running the tests

From a source checkout (see "Installing from source" above):

```bash
pip install pytest
pytest
```

## Project structure

```
log-guard/
├── .github/workflows/tests.yml # GitHub Actions: runs the test suite on every push
├── log_guard.py               # Core tool: detection, masking, spreadsheets, CLI, config, directory scanning
├── test_log_guard.py          # Automated test suite (pytest)
├── pyproject.toml             # Packaging config (PyPI metadata, dependencies + the `log-guard` command)
├── .pre-commit-hooks.yaml     # Lets others use Log Guard as a pre-commit hook
├── .log-guard.json.example    # Example project config file
├── sample.log                 # Example log file for testing
├── generate_samples.py        # Generates edge-case sample files for manual testing
├── generate_test_logs_dir.py  # Generates a sample directory tree for directory-scanning tests
├── generate_xlsx_sample.py    # Generates a sample .xlsx workbook (and can print any .xlsx file's contents)
├── RELEASING.md               # Step-by-step checklist for publishing a new version
└── README.md
```

## Limitations

- Detection is regex-based, so like any pattern-matching approach it can occasionally miss unusual formats (false negatives) or flag something that isn't actually sensitive (false positives) — especially the generic long-token API key fallback, which can flag any long run of random-looking characters.
- Currently focused on common US-style phone number and card formats.
- **Supported file types:** plain-text files and `.xlsx` spreadsheets. Old `.xls` files are not supported (re-save them as `.xlsx`), and other binary formats such as PDF or Word documents are not read.
- **Spreadsheet scanning covers cell values only.** Formulas are deliberately left untouched (masking text inside a formula could break it), and cell comments, headers/footers, sheet names, and text inside charts or images are not scanned.
- **Masked spreadsheets may lose some extras.** The masked copy keeps every sheet, all cell values, and basic formatting, but charts, images, and some advanced Excel features may not survive — a limitation of the `openpyxl` library used to read and write them. Your original file is never changed.
- **Spreadsheets are loaded into memory in full**, so very large workbooks need correspondingly more RAM. (Text logs are streamed line by line and don't have this limit.)
- This tool reduces the risk of accidentally sharing sensitive data, but it isn't a substitute for careful review of anything genuinely high-stakes before sharing.

## Roadmap

- [x] `.xlsx` spreadsheet support (via `openpyxl`)
- [x] PyPI packaging (`pip install logguard-cli`)

## License

MIT — see [LICENSE](https://github.com/apurvaraj9/log-guard/blob/main/LICENSE).

## Author

Built by [Apurva Raj](https://github.com/apurvaraj9).