from pathlib import Path

import pytest

from factorio_docs.html_generator import AgentTableVisitor, HtmlDocumentationGenerator


class TestAgentTableVisitor:
    def test_renders_header_and_data_rows(self) -> None:
        visitor = AgentTableVisitor()

        assert visitor.visit_table_row(object(), ["Name", "Type"], True) == "Table: Name\tType\n"
        assert visitor.visit_table_row(object(), ["Example", "string"], False) == (
            "* Example\tstring\n"
        )

    def test_rejects_empty_rows(self) -> None:
        with pytest.raises(ValueError, match="at least one cell"):
            AgentTableVisitor().visit_table_row(object(), [], False)

    @pytest.mark.parametrize("whitespace", ["\t", "\n", "\r"])
    def test_rejects_ambiguous_cell_whitespace(self, whitespace: str) -> None:
        with pytest.raises(ValueError, match="ambiguous whitespace"):
            AgentTableVisitor().visit_table_row(object(), [f"left{whitespace}right"], False)


class TestHtmlDocumentationGenerator:
    def test_maps_only_html_files_and_honors_blacklist(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        output = tmp_path / "output"
        (source / "auxiliary").mkdir(parents=True)
        (source / "static").mkdir()
        (source / "auxiliary" / "article.html").write_text(
            '<main class="panel-inset-lighter"><h1>Article</h1></main>',
            encoding="utf-8",
        )
        (source / "auxiliary" / "global.html").write_text(
            '<p><a href="article.html">Moved</a></p>',
            encoding="utf-8",
        )
        (source / "static" / "embedded.html").write_text(
            '<main class="panel-inset-lighter"><p>Static HTML</p></main>',
            encoding="utf-8",
        )
        (source / "script.js").write_text("const ignored = true;", encoding="utf-8")
        (source / "data.json").write_text("{}", encoding="utf-8")
        (source / "upper.HTML").write_text("ignored", encoding="utf-8")

        count = HtmlDocumentationGenerator.generate(
            source,
            output,
            frozenset({Path("auxiliary/global.html")}),
        )

        assert count == 2
        assert (output / "auxiliary" / "article.md").read_text(encoding="utf-8") == ("# Article\n")
        assert (output / "static" / "embedded.md").read_text(encoding="utf-8") == ("Static HTML\n")
        assert sorted(path.relative_to(output) for path in output.rglob("*")) == [
            Path("auxiliary"),
            Path("auxiliary/article.md"),
            Path("static"),
            Path("static/embedded.md"),
        ]

    def test_extracts_main_and_removes_heading_permalink(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "document.html").write_text(
            """
            <nav>Repeated navigation</nav>
            <div class="docs-content">
              <main class="panel-inset-lighter">
                <h2 id="topic">Topic<a class="ml8 link" href="#topic">
                  <img src="static/link-symbol.png">
                </a></h2>
                <p>Useful content.</p>
              </main>
            </div>
            <footer>Repeated footer</footer>
            """,
            encoding="utf-8",
        )

        output = tmp_path / "output"
        HtmlDocumentationGenerator.generate(source, output, frozenset())

        assert (output / "document.md").read_text(encoding="utf-8") == (
            "## Topic\n\nUseful content.\n"
        )

    def test_extracts_legacy_content_div(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "document.html").write_text(
            """
            <div class="docs-content">
              <div class="panel-inset-lighter"><p>Legacy content.</p></div>
            </div>
            <div class="docs-sidebar">
              <div class="panel-inset-lighter"><p>Navigation.</p></div>
            </div>
            """,
            encoding="utf-8",
        )

        output = tmp_path / "output"
        HtmlDocumentationGenerator.generate(source, output, frozenset())

        assert (output / "document.md").read_text(encoding="utf-8") == "Legacy content.\n"

    def test_extracts_root_page_layout(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "index.html").write_text(
            """
            <div id="docs-layout-panel">
              <h1 data-pagefind-meta="title">Hidden title</h1>
              <div class="panel-inset mt0"><p>Root content.</p></div>
            </div>
            """,
            encoding="utf-8",
        )

        output = tmp_path / "output"
        HtmlDocumentationGenerator.generate(source, output, frozenset())

        assert (output / "index.md").read_text(encoding="utf-8") == "Root content.\n"

    def test_rewrites_tables_during_conversion(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "table.html").write_text(
            """
            <main class="panel-inset-lighter">
              <table>
                <thead><tr><th>Name</th><th>Type</th><th>Description</th></tr></thead>
                <tbody><tr><td>Example</td><td>string</td><td>An example value</td></tr></tbody>
              </table>
            </main>
            """,
            encoding="utf-8",
        )

        output = tmp_path / "output"
        HtmlDocumentationGenerator.generate(source, output, frozenset())

        assert (output / "table.md").read_text(encoding="utf-8") == (
            "Table: Name\tType\tDescription\n* Example\tstring\tAn example value\n"
        )

    def test_removes_responsive_table_description_duplicates(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "table.html").write_text(
            """
            <main class="panel-inset-lighter">
              <table>
                <tr>
                  <td>Name</td>
                  <td class="td-inline-description">Description</td>
                </tr>
                <tr class="tr-separate-description">
                  <td class="td-modif" colspan="3">Description</td>
                </tr>
              </table>
            </main>
            """,
            encoding="utf-8",
        )

        output = tmp_path / "output"
        HtmlDocumentationGenerator.generate(source, output, frozenset())

        assert (output / "table.md").read_text(encoding="utf-8") == ("Table: Name\tDescription\n")

    def test_rejects_unrecognized_or_ambiguous_layout(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        missing = source / "missing.html"
        missing.write_text("<p>No article container.</p>", encoding="utf-8")

        with pytest.raises(ValueError, match="found 0"):
            HtmlDocumentationGenerator.generate(source, tmp_path / "missing-output", frozenset())

        missing.unlink()
        ambiguous = source / "ambiguous.html"
        ambiguous.write_text(
            """
            <main class="panel-inset-lighter"><p>First.</p></main>
            <main class="panel-inset-lighter"><p>Second.</p></main>
            """,
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="found 2"):
            HtmlDocumentationGenerator.generate(
                source,
                tmp_path / "ambiguous-output",
                frozenset(),
            )

    def test_rejects_invalid_blacklist_and_existing_output(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "article.html").write_text(
            '<main class="panel-inset-lighter"><p>Article.</p></main>',
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="relative HTML path"):
            HtmlDocumentationGenerator.generate(
                source,
                tmp_path / "first-output",
                frozenset({Path("not-html.txt")}),
            )
        with pytest.raises(FileNotFoundError, match="does not exist"):
            HtmlDocumentationGenerator.generate(
                source,
                tmp_path / "second-output",
                frozenset({Path("missing.html")}),
            )

        output = tmp_path / "existing-output"
        output.mkdir()
        with pytest.raises(FileExistsError, match="already exists"):
            HtmlDocumentationGenerator.generate(source, output, frozenset())

    def test_complete_archive_converts(
        self,
        tmp_path: Path,
        factorio_versions: Path,
    ) -> None:
        count = HtmlDocumentationGenerator.generate(
            factorio_versions / "2.0.77" / "files",
            tmp_path / "output",
            frozenset(
                {
                    Path("auxiliary/global.html"),
                    Path("concepts/int.html"),
                    Path("concepts/uint.html"),
                    Path("tree.html"),
                }
            ),
        )

        assert count == 1507
