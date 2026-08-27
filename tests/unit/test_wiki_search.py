from apps.api.routes.wiki import _SearchResultParser


def test_search_parser_normalizes_duckduckgo_results() -> None:
    parser = _SearchResultParser()
    parser.feed(
        """
        <div class="result">
          <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fguide">Example Guide</a>
          <a class="result__snippet">A practical guide to the requested topic.</a>
        </div>
        """
    )

    assert parser.results == [
        {
            "title": "Example Guide",
            "url": "https://example.com/guide",
            "snippet": "A practical guide to the requested topic.",
        }
    ]