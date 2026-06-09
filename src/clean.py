import argparse
import json
import re
from pathlib import Path


DEFAULT_INPUT = Path("data/raw/documents.json")
DEFAULT_OUTPUT = Path("data/processed/documents.json")


YALE_NAV_LINES = {
    "Skip to main content",
    "Yale University",
    "Open Main Navigation",
    "Close Main Navigation",
    "Search this site",
    "Schedules",
    "Order Steep",
    "ELI Bucks",
    "SMART Meals",
    "Menus",
    "Yale Foodie",
    "Residential Dining",
    "Dietary Requirements",
    "Benjamin Franklin",
    "Berkeley",
    "Branford",
    "Davenport",
    "Ezra Stiles",
    "Grace Hopper",
    "Jonathan Edwards",
    "Morse",
    "Pauli Murray",
    "Pierson",
    "Saybrook",
    "Silliman",
    "Timothy Dwight",
    "Trumbull",
    "Restaurants, Cafés & More",
    "Café Law",
    "Café Med",
    "Charley’s Place at SOM",
    "McNay Café at SOM",
    "Schwarzman Center",
    "Commons",
    "Elm",
    "Ivy",
    "The Bow Wow",
    "The Well",
    "Slifka Center for Jewish Life",
    "Steep Café",
    "The Refectory at Divinity",
    "West Campus Café",
    "Catering",
    "Catering Menu",
    "Venues",
    "Bar Service",
    "Event Rentals",
    "Contact Yale Catering",
    "Catering Team",
    "Eat Well",
    "A Note From Chef James",
    "Sourcing & Sustainability",
    "Food Literacy",
    "Graduate & Professional",
    "Home",
    ">",
    "Learn More",
    "Helpful Links",
    "About Us",
    "Leadership Team",
    "Parent Information",
    "Partnerships",
    "News & Press",
    "Connect",
    "Contact Us",
    "Feedback",
    "Accessibility at Yale",
    "Privacy policy",
    "Yale",
    "·",
}


BON_APPETIT_NAV_LINES = {
    "Skip to main content",
    "Cook Something Great Tonight",
    "Download the App Now",
    "Newsletter",
    "Recipes",
    "Drinks",
    "Cooking",
    "Shopping",
    "Restaurants",
    "Culture",
    "Video",
    "Podcast",
    "Merch",
    "Culinary Getaways",
    "Bon Appétit Wine Shop",
    "Search",
    "TikTok content",
    "By",
}


STOP_MARKERS = {
    "official_page": [
        "Helpful Links",
        "Connect",
        "Accessibility at Yale",
        "Copyright © 2026 Yale University",
    ],
    "article": [
        "More Culture Stories",
        "Li is an associate newsletter editor",
        "Explore Bon Appétit",
        "More from Bon Appétit",
        "ABOUT US",
    ],
}


SOURCE_STOP_MARKERS = {
    "doc10": [
        "Tesla is selling $150 CyberBeer",
    ],
}


def normalize_line(line):
    line = re.sub(r"\s+", " ", line).strip()
    line = line.replace("\u00a0", " ")
    return line


def split_lines(text):
    return [normalize_line(line) for line in text.splitlines()]


def trim_after_stop_marker(lines, doc_type, doc_id):
    markers = SOURCE_STOP_MARKERS.get(doc_id, []) + STOP_MARKERS.get(doc_type, [])
    for index, line in enumerate(lines):
        if any(marker in line for marker in markers):
            return lines[:index]
    return lines


def remove_boilerplate_lines(lines, doc_type):
    nav_lines = YALE_NAV_LINES if doc_type == "official_page" else BON_APPETIT_NAV_LINES
    cleaned = []
    previous = None

    for line in lines:
        if not line:
            continue
        if line in nav_lines:
            continue
        if line.startswith("Plus, Tesla is selling"):
            continue
        if line.startswith("Copyright © 2026 Yale University"):
            continue
        if line.startswith("© 2026 Condé Nast"):
            continue
        if line == previous:
            continue
        cleaned.append(line)
        previous = line

    return cleaned


def remove_source_specific_noise(lines, doc_id):
    if doc_id != "doc10":
        return lines

    cleaned = []
    skipping_roundup_intro = False
    for line in lines:
        if line.startswith("Also this week, Tesla announced"):
            skipping_roundup_intro = True
            continue
        if line.startswith("Everyone has dining hall envy"):
            skipping_roundup_intro = False
        if skipping_roundup_intro:
            continue
        if line.startswith("Read more about Yale’s breakfast options"):
            continue
        cleaned.append(line)
    return cleaned


def clean_text(document):
    lines = split_lines(document["raw_text"])
    lines = trim_after_stop_marker(lines, document["type"], document["id"])
    lines = remove_boilerplate_lines(lines, document["type"])
    lines = remove_source_specific_noise(lines, document["id"])
    return "\n".join(lines).strip()


def clean_documents(input_path, output_path):
    with input_path.open("r", encoding="utf-8") as file:
        raw_documents = json.load(file)

    cleaned_documents = []
    for document in raw_documents:
        cleaned_text = clean_text(document)
        cleaned_documents.append(
            {
                "id": document["id"],
                "title": document["planned_title"],
                "fetched_title": document["fetched_title"],
                "type": document["type"],
                "url": document["url"],
                "raw_char_count": document["raw_char_count"],
                "clean_char_count": len(cleaned_text),
                "clean_text": cleaned_text,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(cleaned_documents, file, indent=2, ensure_ascii=False)
        file.write("\n")

    return cleaned_documents


def main():
    parser = argparse.ArgumentParser(description="Clean raw project documents for chunking.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    documents = clean_documents(args.input, args.output)
    for document in documents:
        print(
            f"cleaned {document['id']}: "
            f"{document['raw_char_count']} raw chars -> {document['clean_char_count']} clean chars "
            f"- {document['title']}"
        )
    print(f"\nsaved {len(documents)} cleaned documents to {args.output}")


if __name__ == "__main__":
    raise SystemExit(main())
