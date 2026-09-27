# 🛡️ Log Guard

**A local, offline tool that scans server log files and masks sensitive data before you share them for debugging.**

No uploads. No third-party servers. No enterprise pricing. Your logs never leave your machine.

---

## Why Log Guard?

When you're debugging with a teammate, posting to a forum, or filing a support ticket, you often need to share a log file — but real logs are full of things you *shouldn't* share: customer emails, phone numbers, API keys, IP addresses, credit card numbers.

- **Online masking tools** require uploading your private logs to a third-party server — a privacy risk in itself.
- **Enterprise security tools** solve this, but are expensive, complex, and overkill for an individual developer or small team.

**Log Guard** runs 100% locally, does one job well, and stays simple.

## Features

- 🔍 **Detects and masks:** emails, phone numbers, API keys (Stripe/AWS/GitHub formats + a generic long-token fallback), IP addresses, and credit card numbers (Visa/Mastercard/Amex/Discover)
- 📁 **Scans whole directories**, recursively by default — point it at a `logs/` folder and it finds everything inside
- 🧩 **Custom patterns** via a simple JSON file — add your own detection rules with no code changes
- ⚙️ **Config file support** (`.log-guard.json`) — set project-level defaults for extensions, recursion, custom patterns, and quiet mode; CLI flags always override it
- 🚦 **CI / pre-commit mode** (`--check`) — scans without writing files and exits with status code `1` if secrets are found, so it can block a commit or fail a build. Ships with a ready-to-use `.pre-commit-hooks.yaml`
- 📄 **Non-destructive** — writes a new `*.masked.log` file (or a path you choose with `-o`); your original is never touched, and a clean file with nothing to mask doesn't get a redundant copy
- 📊 **Summary report** — see exactly how many of each type were found
- 🧪 **Fully tested** — 50+ automated tests covering detection, masking, directory scanning, config parsing, and a wide range of edge cases
- 💻 **Handles edge cases** — empty files, huge files (streamed line-by-line), unusual encodings, mixed line endings, and directories with zero matching files
- 🚫 **Smart defaults for directories** — automatically skips `.git`, `node_modules`, `venv`, `.venv`, and `__pycache__` while recursing (use `--ext all` to scan every file if you really want to)
- ⚡ **Zero network calls, ever**

## Installation

```bash
git clone https://github.com/apurvaraj9/log-guard.git
cd log-guard
pip install -e .
```

This installs Log Guard as an editable package and makes the `log-guard` command available in your terminal.

> **Note:** if `log-guard` isn't recognized as a command right after installing, your Python Scripts folder probably isn't on your system PATH. Either add it to PATH, or run the tool with `python -m log_guard` instead — both work identically.

## Usage

**Scan a single file:**

```bash
log-guard your.log
```

Creates `your.masked.log` alongside the original (unless nothing was found — then no output file is created, to avoid clutter).

**Scan an entire directory (recursive by default):**

```bash
log-guard logs/
```

By default this scans `.log`, `.txt`, `.csv`, `.json`, `.out`, and `.err` files, skipping `.git`/`node_modules`/`venv`/`__pycache__` automatically.

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

Add `--quiet` for a condensed summary suited to CI logs. To use Log Guard as an actual [pre-commit](https://pre-commit.com) hook in any repo:

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

```bash
pip install pytest
pytest
```

## Project structure

```
log-guard/
├── log_guard.py              # Core tool: detection, masking, CLI, config, directory scanning
├── test_log_guard.py         # Automated test suite (pytest)
├── pyproject.toml            # Packaging config (enables the `log-guard` command)
├── .pre-commit-hooks.yaml    # Lets others use Log Guard as a pre-commit hook
├── .log-guard.json.example   # Example project config file
├── sample.log                # Example log file for testing
├── generate_samples.py       # Generates edge-case sample files for manual testing
├── generate_test_logs_dir.py # Generates a sample directory tree for directory-scanning tests
└── README.md
```

## Limitations

- Detection is regex-based, so like any pattern-matching approach it can occasionally miss unusual formats (false negatives) or flag something that isn't actually sensitive (false positives) — especially the generic long-token API key fallback, which can flag any long run of random-looking characters.
- Currently focused on common US-style phone number and card formats.
- **Only plain-text files are read correctly.** Binary formats — notably `.xlsx`/`.xls` Excel spreadsheets — are not yet supported; pointing Log Guard at one won't crash, but it also won't reliably find anything inside, since it isn't plain text under the hood. Proper spreadsheet support (reading actual cell contents) is a planned future feature.
- This tool reduces the risk of accidentally sharing sensitive data, but it isn't a substitute for careful review of anything genuinely high-stakes before sharing.

## Roadmap

- [ ] `.xlsx`/`.xls` support (via `openpyxl`)
- [ ] GitHub Actions CI
- [ ] PyPI packaging (`pip install log-guard`)

## License

MIT — see [LICENSE](LICENSE).

## Author

Built by [Apurva Raj](https://github.com/apurvaraj9).
