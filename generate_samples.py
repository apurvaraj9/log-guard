"""
Generates a folder of edge-case sample log files for manually
stress-testing Log Guard. Run once with: python generate_samples.py
"""
import os

OUTPUT_DIR = "edge_case_samples"


def write_text(filename, content):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def write_bytes(filename, content):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    write_text("empty.log", "")

    write_text(
        "clean.log",
        "2024-01-15 09:00:00 INFO Server started successfully\n"
        "2024-01-15 09:00:05 INFO Health check passed\n"
    )

    write_text(
        "all_types.log",
        "Email: john.doe@example.com\n"
        "Phone: 555-123-4567\n"
        "API key: sk_live_51Hz8f92jak3ndlka9d\n"
        "IP address: 203.0.113.42\n"
        "Credit card: 4111 1111 1111 1111\n"
    )

    write_text("no_trailing_newline.log", "Contact john.doe@example.com for details")

    write_text(
        "unicode_emoji.log",
        "User \U0001F600 login from user@example.com successful \U0001F389\n"
        "\u56fd\u9645\u5316\u6d4b\u8bd5 with no secrets here\n"
    )

    write_bytes(
        "crlf_endings.log",
        b"Contact john.doe@example.com\r\nNo secrets on this line\r\n"
    )

    write_bytes(
        "bad_encoding.log",
        b"Normal line before\nBroken bytes: \xff\xfe\nNormal line after\n"
    )

    padding = "x" * 20000
    write_text("huge_line.log", f"{padding} contact john.doe@example.com {padding}\n")

    lines = [f"Line {i}: user{i}@example.com called 555-000-{1000 + i:04d}\n" for i in range(200)]
    write_text("many_lines.log", "".join(lines))

    write_text("custom_patterns_valid.json", '{"employee_id": "EMP-\\\\d{6}"}')
    write_text("custom_patterns_invalid_regex.json", '{"broken": "["}')
    write_text("custom_patterns_not_a_dict.json", '["email", "phone"]')

    print(f"Created edge-case sample files in ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()