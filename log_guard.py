import re
import argparse
import os
import json
import sys


def read_log_file_lines(filepath):
    """
    A generator that yields one line at a time from the file.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as file:
        for line in file:
            yield line


def write_log_file(filepath, lines):
    """
    Writes a list of lines to a new file.
    """
    with open(filepath, "w", encoding="utf-8") as file:
        file.writelines(lines)


EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
PHONE_PATTERN = r"(?:\(\d{3}\)\s?|\d{3}[-.]?)\d{3}[-.]?\d{4}"
API_KEY_PATTERN = (
    r"\bsk_(?:live|test)_[A-Za-z0-9]{10,}\b"
    r"|\bpk_(?:live|test)_[A-Za-z0-9]{10,}\b"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\bgh[pousr]_[A-Za-z0-9]{20,}\b"
    r"|\b[A-Za-z0-9_-]{32,}\b"
)
IP_ADDRESS_PATTERN = (
    r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"
)
CREDIT_CARD_PATTERN = (
    r"\b4[0-9]{3}(?:[ -]?[0-9]{4}){3}\b"
    r"|\b5[1-5][0-9]{2}(?:[ -]?[0-9]{4}){3}\b"
    r"|\b3[47][0-9]{2}[ -]?[0-9]{6}[ -]?[0-9]{5}\b"
    r"|\b6(?:011|5[0-9]{2})(?:[ -]?[0-9]{4}){3}\b"
)

BUILTIN_PATTERNS = {
    "email": EMAIL_PATTERN,
    "phone": PHONE_PATTERN,
    "api_key": API_KEY_PATTERN,
    "ip_address": IP_ADDRESS_PATTERN,
    "credit_card": CREDIT_CARD_PATTERN,
}

DISPLAY_NAMES = {
    "email": "Emails",
    "phone": "Phone numbers",
    "api_key": "API keys",
    "ip_address": "IP addresses",
    "credit_card": "Credit card numbers",
}

# Default file extensions scanned when a directory is given and no
# --ext / config "extensions" override is present. Chosen because
# these are all genuinely plain-text formats our line-by-line reader
# can handle correctly (unlike, say, .xlsx, which is a binary ZIP
# archive under the hood and needs a dedicated reader — not supported
# yet).
DEFAULT_EXTENSIONS = ["log", "txt", "csv", "json", "out", "err"]

# Directories that are never worth recursing into automatically —
# their contents are tooling/dependency internals, not application
# logs, and scanning them would be slow and noisy. This only applies
# when *recursing into* a subfolder; if the user points directly at
# one of these as their input path, it's still scanned.
IGNORED_DIR_NAMES = {".git", "node_modules", "venv", ".venv", "__pycache__"}


def load_custom_patterns(filepath):
    """
    Loads a JSON file of custom patterns and returns whatever it parses
    to (validation happens in build_patterns, not here).
    """
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)


def build_patterns(custom_patterns_filepath=None):
    """
    Combines the built-in patterns with any custom patterns loaded from
    a JSON file. Validates custom patterns so a bad file produces one
    clear error message instead of crashing later during scanning.
    """
    patterns = dict(BUILTIN_PATTERNS)

    if custom_patterns_filepath:
        custom_patterns = load_custom_patterns(custom_patterns_filepath)

        if not isinstance(custom_patterns, dict):
            raise ValueError(
                "Custom patterns file must contain a JSON object mapping "
                "labels to regex strings, e.g. {\"employee_id\": \"EMP-\\\\d{6}\"}"
            )

        for label, pattern in custom_patterns.items():
            if not isinstance(pattern, str):
                raise ValueError(
                    f"Custom pattern '{label}' must be a string, "
                    f"got {type(pattern).__name__} instead."
                )
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex for custom pattern '{label}': {e}")

        patterns.update(custom_patterns)

    return patterns


def mask_line(line, patterns):
    """
    Takes a single log line and a dict of label -> regex string.
    Returns a tuple of: (masked_line, counts_dict)
    """
    counts = {}
    for label, pattern in patterns.items():
        placeholder = f"[{label.upper()}_REDACTED]"
        line, count = re.subn(pattern, placeholder, line)
        counts[label] = count
    return line, counts


def mask_log(lines, patterns):
    """
    Applies mask_line to every line in a log.
    Returns a tuple of: (masked_lines, total_counts, line_count)
    """
    masked_lines = []
    total_counts = {label: 0 for label in patterns}
    line_count = 0

    for line in lines:
        line_count += 1
        masked_line, counts = mask_line(line, patterns)
        masked_lines.append(masked_line)
        for label in total_counts:
            total_counts[label] += counts[label]

    return masked_lines, total_counts, line_count


def build_output_filepath(input_filepath):
    """
    Given "somelog.log", returns "somelog.masked.log" in the same folder.
    """
    base, ext = os.path.splitext(input_filepath)
    return f"{base}.masked{ext}"


def print_summary(total_counts, heading="--- Summary ---", verb="masked"):
    """
    Prints a summary report. verb is "masked" in normal mode or "found"
    in --check mode, since check mode doesn't actually mask anything.
    """
    total_items = sum(total_counts.values())
    print(heading)
    for label, count in total_counts.items():
        display_name = DISPLAY_NAMES.get(label, label.replace("_", " ").title())
        print(f"{display_name} {verb}: {count}")
    print(f"Total items {verb}: {total_items}")


def merge_counts(counts_a, counts_b):
    """
    Merges two label -> count dicts by summing shared keys.
    """
    merged = dict(counts_a)
    for label, count in counts_b.items():
        merged[label] = merged.get(label, 0) + count
    return merged


def _has_matching_extension(filename, pattern_exts):
    """
    Checks if filename's extension (lowercased, no dot) is in the
    pattern_exts set.
    """
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in pattern_exts


def expand_filepaths(filepaths, extensions, recursive):
    """
    Expands any directory paths in `filepaths` into the files they
    contain. `extensions` is either a list like ["log", "txt"]
    (case-insensitive, with or without a leading dot) to filter by,
    or None to match every file regardless of extension ("scan all"
    mode). Recurses into subfolders unless recursive is False, and
    automatically skips IGNORED_DIR_NAMES subfolders while recursing.
    Plain file paths are passed through unchanged.

    Returns a tuple: (expanded_filepaths, warnings), where warnings is
    a list of human-readable strings for any directory that matched
    zero files.
    """
    pattern_exts = None if extensions is None else {ext.lower().lstrip(".") for ext in extensions}
    expanded = []
    warnings = []

    for path in filepaths:
        if os.path.isdir(path):
            found = []
            if recursive:
                for root, dirs, files in os.walk(path):
                    dirs[:] = [d for d in dirs if d not in IGNORED_DIR_NAMES]
                    for filename in files:
                        if pattern_exts is None or _has_matching_extension(filename, pattern_exts):
                            found.append(os.path.join(root, filename))
            else:
                for filename in os.listdir(path):
                    full_path = os.path.join(path, filename)
                    if os.path.isfile(full_path) and (
                        pattern_exts is None or _has_matching_extension(filename, pattern_exts)
                    ):
                        found.append(full_path)

            if found:
                expanded.extend(sorted(found))
            elif pattern_exts is None:
                warnings.append(f"no files found in directory: {path}")
            else:
                ext_display = ", ".join(f".{e}" for e in sorted(pattern_exts))
                warnings.append(f"no files matching [{ext_display}] found in directory: {path}")
        else:
            expanded.append(path)

    return expanded, warnings


def load_config(config_path):
    """
    Loads and validates a JSON config file. Returns a dict containing
    only the keys that were present (extensions, recursive, patterns,
    quiet), so main() can layer command-line flags on top of it.
    """
    with open(config_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Config file must contain a JSON object.")

    allowed_keys = {"extensions", "recursive", "patterns", "quiet"}
    unknown_keys = set(data.keys()) - allowed_keys
    if unknown_keys:
        raise ValueError(
            f"Unknown config option(s): {', '.join(sorted(unknown_keys))}. "
            f"Allowed options: {', '.join(sorted(allowed_keys))}"
        )

    if "extensions" in data:
        if not isinstance(data["extensions"], list) or not all(isinstance(e, str) for e in data["extensions"]):
            raise ValueError("Config option 'extensions' must be a list of strings, e.g. [\"log\", \"txt\"]")

    if "recursive" in data and not isinstance(data["recursive"], bool):
        raise ValueError("Config option 'recursive' must be true or false.")

    if "patterns" in data and not isinstance(data["patterns"], str):
        raise ValueError("Config option 'patterns' must be a string file path.")

    if "quiet" in data and not isinstance(data["quiet"], bool):
        raise ValueError("Config option 'quiet' must be true or false.")

    return data


def process_file(filepath, patterns, check_mode, output_override=None):
    """
    Reads and scans a single file. In check_mode, never writes an output
    file. In normal mode, writes an output file UNLESS nothing was found
    AND no explicit output_override was given.
    """
    result = {
        "filepath": filepath,
        "error": None,
        "empty": False,
        "line_count": 0,
        "counts": {label: 0 for label in patterns},
        "output_filepath": None,
        "skipped_write": False,
    }

    if not os.path.isfile(filepath):
        result["error"] = f"file not found: {filepath}"
        return result

    try:
        lines = read_log_file_lines(filepath)
        masked_lines, total_counts, line_count = mask_log(lines, patterns)
    except FileNotFoundError:
        result["error"] = f"file not found (it may have been deleted or moved): {filepath}"
        return result
    except PermissionError:
        result["error"] = f"permission denied when trying to read: {filepath}"
        return result
    except OSError as e:
        result["error"] = f"could not read file: {filepath} ({e})"
        return result

    result["line_count"] = line_count
    result["counts"] = total_counts

    if line_count == 0:
        result["empty"] = True
        return result

    if not check_mode:
        total_found = sum(total_counts.values())

        if total_found == 0 and output_override is None:
            result["skipped_write"] = True
            return result

        output_filepath = output_override or build_output_filepath(filepath)
        try:
            write_log_file(output_filepath, masked_lines)
        except PermissionError:
            result["error"] = f"permission denied when trying to write: {output_filepath}"
            return result
        except OSError as e:
            result["error"] = f"could not write file: {output_filepath} ({e})"
            return result
        result["output_filepath"] = output_filepath

    return result


def parse_arguments():
    """
    Defines and parses command-line arguments for Log Guard.
    """
    parser = argparse.ArgumentParser(
        prog="log-guard",
        description=(
            "Scan log files (or entire directories) and mask sensitive data "
            "(emails, phone numbers, API keys, IP addresses, credit cards, "
            "and custom patterns)."
        ),
        epilog=(
            "Examples:\n"
            "  log-guard sample.log\n"
            "  log-guard sample.log -o cleaned.log\n"
            "  log-guard logs/                        # scans log/txt/csv/json/out/err in logs/, recursively\n"
            "  log-guard logs/ --ext log,txt --no-recursive\n"
            "  log-guard logs/ --ext all               # scan every file, any extension\n"
            "  log-guard sample.log --patterns custom_patterns.json\n"
            "  log-guard *.log --check   # CI/pre-commit mode: pass/fail, no output files\n"
            "\n"
            "A .log-guard.json file in the current directory (or passed via --config)\n"
            "can set default values for extensions, recursive, patterns, and quiet.\n"
            "Command-line flags always override the config file."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "filepaths",
        nargs="+",
        help="Path(s) to log file(s) and/or directories to scan"
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        default=None,
        help=(
            "Output file path. Only valid with a single input file, and not "
            "usable with --check. Defaults to <name>.masked<ext> if omitted."
        )
    )
    parser.add_argument(
        "--patterns",
        metavar="FILE",
        default=None,
        help="Path to a JSON file of custom patterns to add (label: regex). Overrides config's 'patterns'."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Check-only mode for CI/pre-commit hooks: scans files but does NOT "
            "write masked output files. Exits with status 1 if any sensitive "
            "data is found, 0 if clean."
        )
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file details; only print the final result. Overrides config's 'quiet' (can only force it ON)."
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        default=None,
        help="Path to a JSON config file (defaults to .log-guard.json in the current directory, if present)"
    )
    parser.add_argument(
        "--ext",
        metavar="EXT[,EXT...]|all",
        default=None,
        help=(
            "Comma-separated file extensions to scan inside a directory "
            f"(default: {','.join(DEFAULT_EXTENSIONS)}, or config's 'extensions'). "
            "Use --ext all to scan every file regardless of extension. Example: --ext log,txt"
        )
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into subfolders when a directory is given (this is the default; overrides config's 'recursive' to force it ON)."
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not recurse into subfolders when a directory is given (overrides config's 'recursive' to force it OFF)."
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.recursive and args.no_recursive:
        print("Error: cannot use both --recursive and --no-recursive.")
        sys.exit(2)

    # --- Resolve config file: explicit --config, or default .log-guard.json if present ---
    config = {}
    config_path = args.config
    if config_path is None and os.path.isfile(".log-guard.json"):
        config_path = ".log-guard.json"

    if config_path:
        if not os.path.isfile(config_path):
            print(f"Error: config file not found: {config_path}")
            sys.exit(2)
        try:
            config = load_config(config_path)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON in config file {config_path}: {e}")
            sys.exit(2)
        except ValueError as e:
            print(f"Error: invalid config file {config_path}: {e}")
            sys.exit(2)

    if args.ext:
        extensions = None if args.ext.strip().lower() == "all" else [
            ext.strip().lstrip(".") for ext in args.ext.split(",")
        ]
    else:
        extensions = config.get("extensions", DEFAULT_EXTENSIONS)

    if args.recursive:
        recursive = True
    elif args.no_recursive:
        recursive = False
    else:
        recursive = config.get("recursive", True)

    quiet = args.quiet or config.get("quiet", False)
    patterns_filepath = args.patterns or config.get("patterns")

    # --- Expand any directories into the files they contain ---
    expanded_filepaths, dir_warnings = expand_filepaths(args.filepaths, extensions, recursive)
    for warning in dir_warnings:
        print(f"Warning: {warning}")

    if not expanded_filepaths:
        print("Error: no files to scan.")
        sys.exit(2)

    # --- Validate -o/--output against the FINAL (post-expansion) file list ---
    if args.output and len(expanded_filepaths) > 1:
        print("Error: -o/--output can only be used with a single input file.")
        sys.exit(2)

    if args.output and args.check:
        print("Error: -o/--output cannot be used with --check (check mode does not write files).")
        sys.exit(2)

    if patterns_filepath and not os.path.isfile(patterns_filepath):
        print(f"Error: custom patterns file not found: {patterns_filepath}")
        sys.exit(2)

    try:
        patterns = build_patterns(patterns_filepath)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {patterns_filepath}: {e}")
        sys.exit(2)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(2)
    except OSError as e:
        print(f"Error: could not read custom patterns file {patterns_filepath}: {e}")
        sys.exit(2)

    combined_counts = {label: 0 for label in patterns}
    had_error = False
    verb = "found" if args.check else "masked"

    for filepath in expanded_filepaths:
        result = process_file(filepath, patterns, check_mode=args.check, output_override=args.output)

        if result["error"]:
            print(f"Error: {result['error']}")
            had_error = True
            continue

        if result["empty"]:
            if not quiet:
                print(f"Warning: {filepath} is empty. Nothing to scan.")
            continue

        if not quiet:
            print(f"Scanned {result['line_count']} lines in {filepath}")
            if result["output_filepath"]:
                print(f"Masked log written to {result['output_filepath']}")
            elif result["skipped_write"]:
                print(f"No sensitive data found in {filepath}; masked file not created.")
            print_summary(result["counts"], heading=f"--- Summary for {filepath} ---", verb=verb)
            print()

        combined_counts = merge_counts(combined_counts, result["counts"])

    if had_error:
        sys.exit(2)

    if args.check:
        total_found = sum(combined_counts.values())
        if total_found > 0:
            print(f"FAILED: found {total_found} potential secret(s) across {len(expanded_filepaths)} file(s).")
            if quiet:
                print_summary(combined_counts, verb="found")
            sys.exit(1)
        else:
            print(f"PASSED: no sensitive data found across {len(expanded_filepaths)} file(s).")
            sys.exit(0)
    else:
        if len(expanded_filepaths) > 1:
            print_summary(combined_counts, heading="--- Combined Summary (all files) ---")


if __name__ == "__main__":
    main()