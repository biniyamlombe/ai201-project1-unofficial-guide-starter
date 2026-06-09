import argparse
import json
import re
import sys
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_SOURCES = Path("data/sources.json")
DEFAULT_OUTPUT = Path("data/raw/documents.json")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._title_depth = 0
        self.title_parts = []
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        elif tag == "title":
            self._title_depth += 1
        elif tag in {"p", "div", "section", "article", "header", "footer", "li", "br", "h1", "h2", "h3", "h4"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title" and self._title_depth:
            self._title_depth -= 1
        elif tag in {"p", "div", "section", "article", "header", "footer", "li", "h1", "h2", "h3", "h4"}:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return

        text = data.strip()
        if not text:
            return

        if self._title_depth:
            self.title_parts.append(text)
        else:
            self.text_parts.append(text)

    def title(self):
        return normalize_space(" ".join(self.title_parts))

    def text(self):
        return normalize_lines("\n".join(self.text_parts))


@dataclass
class FetchResult:
    source: dict
    fetched_title: str
    raw_text: str
    raw_char_count: int


def normalize_space(text):
    return re.sub(r"\s+", " ", unescape(text)).strip()


def normalize_lines(text):
    text = unescape(text)
    lines = [normalize_space(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def load_sources(path):
    with path.open("r", encoding="utf-8") as file:
        sources = json.load(file)

    required = {"id", "title", "type", "url"}
    for source in sources:
        missing = required - set(source)
        if missing:
            raise ValueError(f"Source {source!r} is missing required fields: {sorted(missing)}")
    return sources


def fetch_url(url, timeout=30):
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AI201-UnofficialGuide/1.0; +https://example.edu/course-project)"
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def extract_text(html):
    parser = TextExtractor()
    parser.feed(html)
    parser.close()
    return parser.title(), parser.text()


def ingest_source(source):
    html = fetch_url(source["url"])
    fetched_title, raw_text = extract_text(html)
    return FetchResult(
        source=source,
        fetched_title=fetched_title,
        raw_text=raw_text,
        raw_char_count=len(raw_text),
    )


def save_documents(results, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    documents = []
    for result in results:
        source = result.source
        documents.append(
            {
                "id": source["id"],
                "planned_title": source["title"],
                "fetched_title": result.fetched_title,
                "type": source["type"],
                "url": source["url"],
                "raw_char_count": result.raw_char_count,
                "raw_text": result.raw_text,
            }
        )

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(documents, file, indent=2, ensure_ascii=False)
        file.write("\n")
    return documents


def main():
    parser = argparse.ArgumentParser(description="Fetch project sources and save raw extracted text.")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    sources = load_sources(args.sources)
    results = []
    failures = []

    for source in sources:
        try:
            result = ingest_source(source)
            results.append(result)
            print(f"loaded {source['id']}: {result.raw_char_count} chars - {source['title']}")
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError) as error:
            failures.append({"source": source, "error": str(error)})
            print(f"failed {source['id']}: {source['url']} - {error}", file=sys.stderr)

    documents = save_documents(results, args.output)
    print(f"\nsaved {len(documents)} raw documents to {args.output}")

    if failures:
        print("\nFailures:", file=sys.stderr)
        for failure in failures:
            source = failure["source"]
            print(f"- {source['id']} {source['url']}: {failure['error']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
