# Releasing a new version of Log Guard

A step-by-step checklist for publishing a new version to PyPI.

All commands run in the VS Code terminal (PowerShell), from the `log-guard` project folder, unless a step says otherwise. Replace `X.Y.Z` with the new version number everywhere (for example `0.2.0`).

**Credentials:** PyPI and TestPyPI tokens live in KeePassXC (entries `PyPI` and `TestPyPI`, in the Notes field). Never put a token in any file in this project.

---

## 0. Choose the version number

| Change | Example | Bump |
|---|---|---|
| Bug fixes only | 0.1.0 → 0.1.1 | last number |
| New features (e.g. `.xlsx` support) | 0.1.0 → 0.2.0 | middle number, reset last to 0 |
| Big/breaking changes, or declaring it stable | 0.x → 1.0.0 | first number |

**A version number can only ever be uploaded once.** Even if you delete a release from PyPI, that number can never be reused.

## 1. Make sure everything is ready

```
pytest
git status
```

- `pytest` → all tests pass.
- `git status` → `nothing to commit, working tree clean`.
- On GitHub, the **Actions** tab shows the latest run on `main` as green.

## 2. Bump the version

1. In `pyproject.toml`, change `version = "..."` to `version = "X.Y.Z"`. This is the only place the version number lives.
2. In `README.md`, update the pre-commit example to `rev: vX.Y.Z`.
3. If this release adds features, update the README's **Features**, **Limitations** and **Roadmap** sections to match.

Then commit and push:

```
git add pyproject.toml README.md
git commit -m "Release vX.Y.Z"
git push
```

Wait for the GitHub Actions run to go green before continuing.

## 3. Build

```
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
python -m build
dir dist
python -m twine check dist/*
```

Expected:
- `python -m build` ends with `Successfully built logguard_cli-X.Y.Z.tar.gz and logguard_cli-X.Y.Z-py3-none-any.whl`
- `dir dist` shows exactly those two files, with the new version number.
- `twine check` shows `PASSED` for both.

## 4. Rehearse on TestPyPI (recommended for any release with new features or dependencies)

Upload (paste the **TestPyPI** token when asked; nothing appears on screen when pasting):

```
python -m twine upload --repository testpypi dist/*
```

Then test-install in a throwaway environment:

```
cd $HOME\Desktop
python -m venv logguard-test-env
.\logguard-test-env\Scripts\python.exe -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ logguard-cli==X.Y.Z
.\logguard-test-env\Scripts\python.exe -m pip show logguard-cli
.\logguard-test-env\Scripts\log-guard.exe log-guard\sample.log --check
$LASTEXITCODE
Remove-Item -Recurse -Force logguard-test-env
cd $HOME\Desktop\log-guard
```

Check:
- `pip show` → `Version: X.Y.Z`, Location inside `logguard-test-env`.
- The scan prints the usual report and `$LASTEXITCODE` prints `1` (sample.log contains fake secrets).

Why `--extra-index-url`: TestPyPI hosts our package, but dependencies like `openpyxl` must come from the real PyPI. (For a package with no dependencies, `--no-deps` instead of `--extra-index-url` also works.)

If the TestPyPI token was deleted, create a new one at test.pypi.org → Account settings → API tokens.

## 5. Upload to PyPI

Paste the **PyPI** token when asked:

```
python -m twine upload dist/*
```

Expected: ends with `View at: https://pypi.org/project/logguard-cli/X.Y.Z/`

## 6. Verify the real release

```
cd $HOME\Desktop
python -m venv logguard-test-env
.\logguard-test-env\Scripts\python.exe -m pip install logguard-cli==X.Y.Z
.\logguard-test-env\Scripts\python.exe -m pip show logguard-cli
.\logguard-test-env\Scripts\log-guard.exe log-guard\sample.log --check
$LASTEXITCODE
Remove-Item -Recurse -Force logguard-test-env
cd $HOME\Desktop\log-guard
```

Same checks as step 4. If pip says `No matching distribution found`, wait 2–3 minutes and retry.

Then refresh your own development install so its metadata shows the new version:

```
pip install -e .
pip show logguard-cli
```

Expected: `Version: X.Y.Z`.

## 7. Tag the release on GitHub

```
git tag -a vX.Y.Z -m "vX.Y.Z - short description of what changed"
git push origin vX.Y.Z
```

Expected: `* [new tag]         vX.Y.Z -> vX.Y.Z`

Optional: on GitHub, open the tag and choose **Create release from tag** to write release notes.

## 8. Final checks

- https://pypi.org/project/logguard-cli/ shows version X.Y.Z with the updated README.
- The **pypi** badge on the GitHub README shows `vX.Y.Z` (it can take a few minutes to update; refresh with Ctrl + F5).
- https://github.com/apurvaraj9/log-guard/tags lists `vX.Y.Z`.

---

## If something goes wrong

- **`400 Bad Request ... File already exists`:** this version number was already uploaded. Bump to the next version (step 2) and rebuild. Versions cannot be reused.
- **`403 Forbidden`:** wrong token. Check you pasted the PyPI token for PyPI and the TestPyPI token for TestPyPI, copied fully from KeePassXC.
- **A broken release got published:** you can't replace it. Fix the bug and release the next patch version (e.g. X.Y.Z+1). Optionally "yank" the broken one on pypi.org (Your projects → logguard-cli → Manage → Releases → Options → Yank), which stops pip from installing it by default.
- **Never** edit an existing tag to point at different code. If a tag is wrong, fix forward with a new version.