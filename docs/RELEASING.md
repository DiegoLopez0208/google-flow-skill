# Releasing

## GitHub package distribution

The package is distributed as a Python wheel and source archive in GitHub
Releases. GitHub's separate Packages sidebar is not used for this Python
distribution. PyPI is a separate destination and is not yet configured.

1. Update `pyproject.toml`, `google_flow_skill/__init__.py`, both Claude
   manifests, the smoke-check version and the install URLs in the manuals.
2. Add the changelog entry and `docs/releases/vX.Y.Z.md`.
3. Run wiring tests, build, `twine check`, artifact checks and installed-wheel
   smoke checks. Confirm all CI jobs pass.
4. Push a matching `vX.Y.Z` tag. `release.yml` builds the distributions, checks
   their contents, tests the wheel and creates a draft GitHub Release with
   SHA-256 checksums.
5. Upload any reviewed demo assets, verify the draft, then publish it.

The source archive and wheel exclude sessions, generated output and debug
captures. Source/plugin users keep their portable profile; installed package
users keep state in `~/.google-flow-skill` unless overridden.

## PyPI: account setup still required

The package name `google-flow-skill` is the intended PyPI name. Its availability
must be checked when registering; no name has been reserved by this repository.

The account owner must create a PyPI account and complete email and two-factor
authentication setup. Then create a pending Trusted Publisher in PyPI:

| Field | Value |
|---|---|
| Project name | `google-flow-skill` |
| GitHub owner | `DiegoLopez0208` |
| Repository | `google-flow-skill` |
| Workflow filename | `publish-pypi.yml` |
| Environment | `pypi` |

Configure the matching GitHub environment as appropriate. The publisher grants
this workflow permission to publish this project; it should be configured by
the account owner. No API token needs to be pasted into the repository.

After setup, run the `publish-pypi` workflow manually with tag `v2.3.0`.
It builds the tagged source, validates it and publishes through OIDC. Verify
the PyPI project and a fresh `python -m pip install google-flow-skill==2.3.0`
before changing the README to advertise that command.

Official setup: https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/
