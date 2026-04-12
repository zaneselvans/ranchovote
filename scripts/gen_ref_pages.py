"""Generate API reference pages for MkDocs during the documentation build.

This script is part of the documentation build pipeline, not part of the runtime
application. Its job is to walk the Python package under `src/ranchovote`, discover
packages and modules, and create a parallel set of Markdown files under the virtual
`api/` docs tree. Those generated pages are intentionally small: each page provides a
heading, optional links to direct child modules, and a `mkdocstrings` directive that
tells the docs builder to render documentation for the corresponding Python object.

You generally do not run this script by hand. It is executed automatically as part of
the MkDocs and Zensical build process through `mkdocs-gen-files`, which imports this
module while the docs site is being assembled. In other words, this script is a build
step that manufactures the Markdown scaffolding the API reference needs right before
`mkdocstrings` expands it into rendered documentation.

The script is necessary because `mkdocstrings` renders API documentation from Python
objects, but it still needs Markdown pages to anchor that rendered content in the docs
navigation. Rather than hand-maintaining one page per module, this file generates those
pages from the package tree so the API reference stays aligned with the codebase as the
package grows or is reorganized.

If you are coming from the Sphinx and reStructuredText world, this plays a role similar
to a lightweight combination of `sphinx-apidoc` and `autosummary` stub generation.
`sphinx-apidoc` can generate `.rst` files for modules, and `autosummary` can create
template-backed stub pages that later pull in autodoc output. This script serves the
same structural purpose for the MkDocs stack: it creates the per-module pages that
allow the real API renderer to fill in the details. The main difference is that the
output here is Markdown with `mkdocstrings` directives instead of `.rst` files with
Sphinx directives such as `.. automodule::`.
"""

from dataclasses import dataclass
from os.path import relpath
from pathlib import Path

import mkdocs_gen_files

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
PACKAGE_ROOT: Path = PROJECT_ROOT / "src" / "ranchovote"


@dataclass(frozen=True, slots=True)
class ApiPage:
    """Describe one generated API reference page."""

    module_name: str
    doc_path: Path
    heading: str
    child_modules: tuple[str, ...] = ()


def main() -> None:
    """Generate virtual API reference pages from the package tree."""
    pages: tuple[ApiPage, ...] = discover_api_pages()
    for page in pages:
        with mkdocs_gen_files.open(page.doc_path, "w") as file_handle:
            file_handle.write(render_page(page))

        mkdocs_gen_files.set_edit_path(
            page.doc_path,
            source_path_for_module(page.module_name)
            .relative_to(PROJECT_ROOT)
            .as_posix(),
        )


def discover_api_pages() -> tuple[ApiPage, ...]:
    """Return a stable list of package and module reference pages."""
    package_pages: list[ApiPage] = []
    module_pages: list[ApiPage] = []

    for source_path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if source_path.name == "__init__.py":
            package_pages.append(package_page(source_path))
            continue
        module_pages.append(module_page(source_path))

    package_children = build_package_children(package_pages, module_pages)
    pages: list[ApiPage] = [
        ApiPage(
            module_name=page.module_name,
            doc_path=page.doc_path,
            heading=page.heading,
            child_modules=package_children.get(page.module_name, ()),
        )
        for page in package_pages
    ]
    pages.extend(module_pages)
    return tuple(sorted(pages, key=lambda page: page.doc_path.as_posix()))


def package_page(source_path: Path) -> ApiPage:
    """Return metadata for one package index page."""
    relative_parts = source_path.relative_to(PACKAGE_ROOT).parts[:-1]
    module_name = (
        ".".join(("ranchovote", *relative_parts)) if relative_parts else "ranchovote"
    )
    doc_path = Path("api", *relative_parts, "index.md")
    heading = "API Reference" if not relative_parts else module_name
    return ApiPage(module_name=module_name, doc_path=doc_path, heading=heading)


def module_page(source_path: Path) -> ApiPage:
    """Return metadata for one module reference page."""
    relative_parts = source_path.relative_to(PACKAGE_ROOT).with_suffix("").parts
    module_name: str = ".".join(("ranchovote", *relative_parts))
    doc_path: Path = Path("api", *relative_parts).with_suffix(".md")
    return ApiPage(module_name=module_name, doc_path=doc_path, heading=module_name)


def build_package_children(
    package_pages: list[ApiPage],
    module_pages: list[ApiPage],
) -> dict[str, tuple[str, ...]]:
    """Return direct child modules for each package page."""
    children: dict[str, list[str]] = {page.module_name: [] for page in package_pages}
    for page in (*package_pages, *module_pages):
        parent_module = parent_name(page.module_name)
        if parent_module is None:
            continue
        if parent_module in children:
            children[parent_module].append(page.module_name)

    return {
        module_name: tuple(sorted(child_modules))
        for module_name, child_modules in children.items()
    }


def parent_name(module_name: str) -> str | None:
    """Return the dotted parent module name for one page."""
    if module_name == "ranchovote":
        return None
    return module_name.rsplit(".", maxsplit=1)[0]


def render_page(page: ApiPage) -> str:
    """Render one generated reference page."""
    lines = [f"# {page.heading}", ""]

    lines.append(
        "<!-- This page is generated automatically during the docs build from "
        "the package source. Do not edit it by hand. -->"
    )
    lines.append("")

    if page.child_modules:
        lines.append("## Contents")
        lines.append("")
        lines.extend(
            f"- [{child_module}]({relative_link(page.doc_path, doc_path_for_module(child_module))})"
            for child_module in page.child_modules
        )
        lines.append("")

    lines.append(f"::: {page.module_name}")
    lines.append("")
    return "\n".join(lines)


def relative_link(current_doc_path: Path, target_doc_path: Path) -> str:
    """Return a relative Markdown link between two generated reference pages."""
    return Path(relpath(target_doc_path, start=current_doc_path.parent)).as_posix()


def doc_path_for_module(module_name: str) -> Path:
    """Return the generated documentation path for one module name."""
    module_parts: list[str] = module_name.split(".")[1:]
    source_candidate: Path = PACKAGE_ROOT.joinpath(*module_parts)
    if source_candidate.is_dir():
        return Path("api", *module_parts, "index.md")
    return Path("api", *module_parts).with_suffix(".md")


def source_path_for_module(module_name: str) -> Path:
    """Return the source file backing one module name."""
    module_parts: list[str] = module_name.split(".")[1:]
    package_init: Path = PACKAGE_ROOT.joinpath(*module_parts, "__init__.py")
    if package_init.exists():
        return package_init
    return PACKAGE_ROOT.joinpath(*module_parts).with_suffix(".py")


main()
