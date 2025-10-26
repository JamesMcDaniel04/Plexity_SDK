# Releasing `plexity-sdk`

This workflow ensures the packaged artifacts published to PyPI match the repository state and pass validation across supported Python versions.

## 1. Prep a Release Pull Request

1. Update `pyproject.toml` with the new semantic version.
2. Set `__version__` in `plexity_sdk/__init__.py` to the same value.
3. Run the full test suite locally:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install .[dev]
   pytest
   python -m build
   ```

4. Merge the pull request once CI passes. The `CI` workflow builds wheels for Python 3.9–3.12 and attaches them as artifacts for inspection.

## 2. Tag & Publish

1. Create a signed tag following the `vX.Y.Z` convention (matching `pyproject.toml`):

   ```bash
   git tag -s v0.3.0 -m "Release v0.3.0"
   git push origin v0.3.0
   ```

2. The `Release` GitHub Action runs automatically on tag push:
   - Re-validates the version from `pyproject.toml`.
   - Builds sdist and wheel files.
   - Publishes to PyPI using the repository secret `PYPI_API_TOKEN`.

3. Optionally, trigger the workflow manually via **Actions → Release → Run workflow** to dry-run a build. When using workflow dispatch, supply the target version and download the `dist` artifact for smoke testing.

## 3. Post-Release Checklist

- Verify the package is live on PyPI: `pip install --upgrade plexity-sdk`.
- Update documentation or CHANGELOG if required.
- Create follow-up issues for any manual steps that surfaced during validation.
