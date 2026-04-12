# Documentation Build

This project builds its documentation site with `zensical`, which configures an MkDocs-based pipeline using the settings in `zensical.toml`.

The standard local build command is:

```shell
pixi run docs-build
```

That task runs:

```shell
python -m zensical build --clean
```

The result is a fully rendered static site under `site/`.

## Build Inputs

The documentation build combines several kinds of inputs:

- hand-written documentation pages under `docs/`
- project configuration from `zensical.toml`
- Python docstrings and module structure under `src/ranchovote/`
- theme assets and MkDocs plugin output managed by the docs toolchain

The docs build assumes the repository is being worked on through the Pixi-managed environment and normal repo folder layout.

Most pages in `docs/` are ordinary source files that should be edited directly. The main exceptions are the API reference pages, which are generated during the build.

## Build Configuration

The site configuration lives in `zensical.toml`.

That file defines:

- the site metadata, repository links, and top-level navigation
- the enabled MkDocs and Zensical plugins
- the `mkdocstrings` configuration for rendering Python API documentation
- the `gen-files` hook that generates API reference pages at build time

The current navigation includes this page as a hand-written guide, separate from the generated API reference.

## API Reference Generation

The API reference is not maintained by hand.

During the docs build, the `gen-files` plugin runs `scripts/gen_ref_pages.py`. That script walks `src/ranchovote/`, discovers packages and modules, and creates a matching set of Markdown stubs in the virtual `api/` docs tree.

Each generated page contains:

- a heading for the module or package
- optional links to direct child modules
- a `mkdocstrings` directive such as `::: ranchovote.contest`

After those stubs are generated, `mkdocstrings` imports the Python objects and renders their API documentation from docstrings and signatures.

In practice, that means the API reference is derived from the codebase in two steps:

1. `scripts/gen_ref_pages.py` generates the page scaffolding.
1. `mkdocstrings` fills those pages with rendered Python API content.

## Why `docs/api/` Is Ignored

The repository keeps `docs/api/.gitignore` so generated API stub files are not accidentally committed.

This matters because the API pages are build artifacts, not authoritative documentation sources. The real sources of truth are:

- the generator script in `scripts/gen_ref_pages.py`
- the `mkdocstrings` configuration in `zensical.toml`
- the Python package layout and docstrings under `src/ranchovote/`

If you see local files under `docs/api/`, treat them as disposable generated output.

## What To Edit

When changing the docs system, edit the source that actually controls the output:

- edit `docs/*.md` for hand-written documentation pages
- edit `zensical.toml` for site navigation or plugin configuration
- edit `scripts/gen_ref_pages.py` to change generated API page structure or messaging
- edit Python docstrings in `src/ranchovote/` to change rendered API documentation content

Do not hand-edit generated API stub pages under `docs/api/`.

## Typical Workflow

For ordinary documentation changes:

1. Edit the relevant hand-written page in `docs/`.
1. Run `pixi run docs-build`.
1. Inspect the rendered output in `site/` if needed.

For API documentation changes:

1. Update Python docstrings or module structure under `src/ranchovote/`.
1. If needed, update `scripts/gen_ref_pages.py`.
1. Run `pixi run docs-build`.
1. Verify the generated API section in `site/api/`.

## Output Directories

- `docs/`: hand-written documentation sources
- `docs/api/`: ignored local generated API stubs when present
- `site/`: rendered static site output

If the generated API pages ever look wrong, the fix should usually happen in the generator, configuration, or docstrings, not by patching files under `docs/api/`.
