# The Unofficial Guide — Project 1: Yale Campus Dining

This repository implements a Retrieval-Augmented Generation (RAG) system for the unofficial guide to Yale Campus Dining. It includes a multi-stage ingestion, paragraph-aware chunking, vector indexing with ChromaDB, and grounded answer generation using the Groq API.

---

## Domain

The system covers Yale campus dining, including residential dining halls, meal plans, schedules, retail locations, dietary accommodations, and student-culture impressions of the dining experience. 

This knowledge is highly valuable for students because finding practical details (such as where they can swipe, guest pass rules, dietary safety, and dining hall traditions) usually requires digging through dozens of different website subpages. In addition, student-culture opinions are scattered across articles and forums. By consolidating policies and impressions into a single RAG-powered interface, students can get grounded, immediate answers to practical dining questions.

---

## Document Sources

We collected 10 sources spanning official Yale Hospitality pages, schedules, dietary guides, and student articles:

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Yale Hospitality homepage | Official Webpage | https://hospitality.yale.edu/ |
| 2 | Residential Dining | Official Webpage | https://hospitality.yale.edu/residential-dining |
| 3 | Explore Meal Plans | Official Webpage | https://hospitality.yale.edu/explore-meal-plans |
| 4 | When & Where | Official Webpage | https://hospitality.yale.edu/when-where |
| 5 | Dietary Requirements | Official Webpage | https://hospitality.yale.edu/eat-well/dietary-requirements |
| 6 | Berkeley Dining | Official Webpage | https://hospitality.yale.edu/residential-dining/berkeley |
| 7 | Branford Dining | Official Webpage | https://hospitality.yale.edu/residential-dining/branford |
| 8 | Jonathan Edwards Dining | Official Webpage | https://hospitality.yale.edu/residential-dining/jonathan-edwards |
| 9 | Commons | Official Webpage | https://hospitality.yale.edu/restaurants-cafes-more/schwarzman-center/commons |
| 10 | Bon Appétit article about Yale breakfast | Editorial Article | https://www.bonappetit.com/story/yale-dining-hall-breakfast |

---

## Chunking Strategy

**Chunk size:** 350-500 words per chunk.

**Overlap:** ~75 words of paragraph overlap between neighboring chunks.

**Why these choices fit your documents:**
Most source pages are short, structured documents with headings, bullet lists, and policy details. We implemented a paragraph-based sliding window algorithm rather than a raw character split. This preserves semantic unity (e.g., keeping a specific meal plan's rules, rates, and restrictions together in one piece) without splitting mid-sentence or mid-bullet point.

**Preprocessing:**
- Stripped HTML tags, scripts, styles, and SVG graphics.
- Normalized whitespaces, converted HTML entities, and removed empty lines.
- Filtered repeated site navigation menus and standard footers via stop markers in `src/clean.py` (such as `"Helpful Links"` and `"Accessibility at Yale"`).
- Cleaned article-specific advertisement wrappers.

**Final chunk count:** 17 chunks across all documents.

---

## Embedding Model

**Model used:** `sentence-transformers/all-MiniLM-L6-v2` (run locally).

**Production tradeoff reflection:**
`all-MiniLM-L6-v2` is free, fast, and runs locally. If deploying a production system for real users with no cost constraints, we would weigh the following:
- **Context Length:** `all-MiniLM` has a limit of 256 tokens. A production model (like `text-embedding-3-large` with 8k tokens) would allow us to ingest larger chunks containing complex, cross-referenced dining policies without boundary dilution.
- **Latency vs. Cost:** Running embeddings locally has zero network latency and no API costs, but requires dedicated server memory and GPU computation. API-based models (like OpenAI or Cohere) transfer the hosting burden but introduce network round-trips and API costs.
- **Domain Accuracy:** We would test models fine-tuned on hospitality and educational terminology to reduce distance scores on specific vocabulary (such as meal plan terms or dining hall names).

---

## Grounded Generation

**System prompt grounding instruction:**
We enforce grounding in [generate.py](file:///Users/biniyamlombe/ai201-project1-unofficial-guide-starter/src/generate.py#L41-L49) using this instruction:
> You are a helpful and precise Yale campus dining assistant. Your goal is to answer the user's question using ONLY the provided text context.
> 
> Strict grounding guidelines:
> 1. Your answer must be directly supported by and derived ONLY from the provided text context.
> 2. Do NOT use any outside knowledge, assumptions, or extrapolations. Do not make up facts or details.
> 3. If the provided context does not contain the answer, you must state exactly: "I do not have enough information in my source documents to answer this question."
> 4. Format your answer clearly and cite your sources. Surround inline citations with square brackets, referencing the exact "Source Title" from the context (e.g., [Berkeley Dining] or [Explore Meal Plans]).
> 5. If the source information is from the Bon Appétit article, cite it as [Bon Appétit article].

We also set the LLM model temperature to `0.0` to force deterministic responses and eliminate creative extrapolations.

**How source attribution is surfaced in the response:**
The LLM includes inline square-bracket citations mapping directly to the "Source Title" (e.g. `[Berkeley Dining]`). The Streamlit web interface displays these inline citations alongside an interactive accordion section (`🔍 View Retrieved Sources & Distance Scores`) showing the exact text blocks, source URLs, and cosine distance scores used for grounding.

---

## Evaluation Report

Here are the results of our 5 evaluation questions run through the RAG pipeline:

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | How many residential dining halls does Yale describe as part of its dining system? | Yale describes 14 residential dining halls. | Yale has 14 residential dining halls. [Residential Dining] [Explore Meal Plans] | Relevant | Accurate |
| 2 | What does the Full meal plan include for undergraduate students? | The Full plan includes unlimited meals at all 14 residential dining halls, guest passes, and dining points for retail locations. | Unlimited meals at all 14 dining halls, guest passes, and $300 points per semester for retail locations. [Explore Meal Plans] | Relevant | Accurate |
| 3 | Which meal plan is designed for off-campus undergraduate students, and what does it include? | The Connect plan is for off-campus undergraduate students and includes weekly swipes plus dining points. | The Connect Meal Plan. Includes 5 weekly swipes and $375 points per semester for retail locations. [Explore Meal Plans] | Relevant | Accurate |
| 4 | What makes Berkeley dining distinctive according to Yale Hospitality? | Berkeley is a crowd-pleaser with traditions such as Thunder Brunch, a Mediterranean bowl concept, and a stone-hearth pizza oven. | Distinctive for its Innovative Mediterranean Bowl Concept, stone-hearth pizza oven, and traditions like Thunder Brunch. [Berkeley Dining] | Relevant | Accurate |
| 5 | What does the project corpus say about wait times at Yale dining halls? | Fail/partial fail (corpus doesn't contain wait times). | "I do not have enough information in my source documents to answer this question." | Off-target | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** *"What does the project corpus say about wait times at Yale dining halls?"*

**What the system returned:** *"I do not have enough information in my source documents to answer this question."*

**Root cause (tied to a specific pipeline stage):**
This is a retrieval-stage failure. Our scraped documents (official Yale Hospitality pages and the Bon Appétit breakfast feature) contain policy parameters, menus, locations, and schedules, but do not contain any information regarding student wait times, lines, or crowding. Consequently, the vector store returned calendar schedules and transfer rules (`doc04_chunk02`) as the closest matches with high distance scores (>=0.68). 

**What you would change to fix it:**
To answer this question, we would expand our ingestion pipeline to collect informal data sources such as student reviews, forum posts (from the `r/yale` subreddit), or student survey results that capture crowd patterns, peak hours, and actual dining line wait times.

---

## Spec Reflection

**One way the spec helped you during implementation:**
Defining strict expected answers in the evaluation plan allowed us to immediately spot that the Connect Meal Plan details were missing during our initial tests. We traced this back to a data cleaning bug in `clean.py` where a stop marker (`"Connect"`) prematurely truncated the document.

**One way your implementation diverged from the spec, and why:**
We diverged by removing the `"Connect"` stop marker from the official page cleaning configuration. The spec originally proposed using `"Connect"` to strip out the footer, but substring matching ran into a collision with the `"Connect (Off-Campus) Plan"` heading, which discarded half of the Explore Meal Plans page. Removing it was safe because `"Helpful Links"` already cleanly handles the footer truncation on all pages.

---

## AI Usage

**Instance 1**
- *What I gave the AI:* The Chunking Strategy and Architecture sections of `planning.md`.
- *What it produced:* A basic character-based chunking utility.
- *What I changed or overrode:* I overrode the character-based split to implement a paragraph-aware sliding window algorithm that measures word count, guaranteeing that list items, headings, and paragraphs are never cut off in the middle of sentences.

**Instance 2**
- *What I gave the AI:* Requirements for local ChromaDB indexing and Streamlit UI code.
- *What it produced:* Scripts for loading embeddings and a basic search form.
- *What I changed or overrode:* I wrapped the model initialization and database connection in Streamlit `@st.cache_resource` decorators to prevent slow reloads, added workspace root paths to `sys.path` to resolve module imports, and designed card-based UI container blocks for showing distance scores and citations.
