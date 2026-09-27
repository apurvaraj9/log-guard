"""
Creates a small directory tree for exercising Log Guard's directory
scanning feature. Run once with: python generate_test_logs_dir.py
"""
import os

BASE_DIR = "test_logs"


def write_text(relative_path, content):
    full_path = os.path.join(BASE_DIR, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    write_text("app.log", "User login for john.doe@example.com\n")
    write_text("notes.txt", "Call support at 555-123-4567\n")
    write_text("archive/old.log", "Old API key: sk_live_51Hz8f92jak3ndlka9d\n")
    write_text("archive/deeper/very_old.log", "IP seen: 203.0.113.42\n")
    write_text("readme.md", "This file should never be scanned.\n")

    print(f"Created test directory tree in ./{BASE_DIR}/")


if __name__ == "__main__":
    main()