# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

This project covers Yale campus dining, including residential dining halls, meal plans, dining schedules, dietary requirements, retail dining, and student-facing impressions of the dining experience. This knowledge is useful because students often need practical answers quickly, such as where they can eat, how meal swipes work, what dining halls are known for, and how dietary accommodations are handled. It is hard to find in one place because official Yale pages contain policies and location details, while more informal opinions and dining culture are scattered across articles, Reddit threads, and student conversations.

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Yale Hospitality homepage | Official hub for Yale dining links, menus, schedules, meal plans, and dining services. | https://hospitality.yale.edu/ |
| 2 | Residential Dining | Official overview of Yale's residential dining system and list of residential dining halls. | https://hospitality.yale.edu/residential-dining |
| 3 | Explore Meal Plans | Official meal plan information, including swipes, dining points, guest swipes, costs, and restrictions. | https://hospitality.yale.edu/explore-meal-plans |
| 4 | When & Where | Official operating hours and dining schedule information. | https://hospitality.yale.edu/when-where |
| 5 | Dietary Requirements | Official information about dietary needs and accommodations. | https://hospitality.yale.edu/eat-well/dietary-requirements |
| 6 | Berkeley Dining | Official page describing Berkeley dining, including dining traditions and distinctive food options. | https://hospitality.yale.edu/residential-dining/berkeley |
| 7 | Branford Dining | Official page describing Branford dining, including culinary traditions and dining atmosphere. | https://hospitality.yale.edu/residential-dining/branford |
| 8 | Jonathan Edwards Dining | Official page describing Jonathan Edwards dining, traditions, and dining hall atmosphere. | https://hospitality.yale.edu/residential-dining/jonathan-edwards |
| 9 | Commons | Official page for Commons at the Schwarzman Center, including hours and accepted payment methods. | https://hospitality.yale.edu/restaurants-cafes-more/schwarzman-center/commons |
| 10 | Bon Appetit article about Yale dining hall breakfast | Public student-culture article discussing Yale dining hall breakfast options and reactions. | https://www.bonappetit.com/story/yale-dining-hall-breakfast |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**

Target 350-500 words per chunk, grouped by page section or paragraph boundary rather than by a fixed character count.

**Overlap:**

About 75 words of overlap between neighboring chunks when a page has long sections.

**Reasoning:**

Most of the documents are short informational web pages with headings, bullet lists, and compact descriptions. Section-aware chunks should preserve meaningful units such as "Full Plan," "Flex Plan," "We are Berkeley," or "Dietary Accommodations." A 350-500 word target is large enough to keep policy details together but small enough that retrieval can return a focused answer instead of an entire page. The 75-word overlap helps when important details appear at the boundary between two sections, such as meal plan restrictions or dining point rules.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

sentence-transformers/all-MiniLM-L6-v2

**Top-k:**

4 chunks per query.

**Production tradeoff reflection:**

For this course project, all-MiniLM-L6-v2 is a good choice because it runs locally, is free, is fast, and does not require an API key. In a production system, I would compare it with larger embedding models that may retrieve more accurately on policy-heavy or domain-specific text. I would also weigh cost, latency, context length, multilingual support, privacy, and whether the model should run locally or through an API.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | How many residential dining halls does Yale describe as part of its dining system? | Yale describes 14 residential dining halls. |
| 2 | What does the Full meal plan include for undergraduate students? | The Full plan includes unlimited meals at all 14 residential dining halls, guest passes, and dining points for retail locations. |
| 3 | Which meal plan is designed for off-campus undergraduate students, and what does it include? | The Connect plan is for off-campus undergraduate students and includes weekly meal swipes plus dining points. |
| 4 | What makes Berkeley dining distinctive according to Yale Hospitality? | Berkeley is described as a crowd-pleaser with traditions such as Thunder Brunch and options such as a Mediterranean bowl concept and gourmet pizza from a stone-hearth oven. |
| 5 | What does the project corpus say about wait times at Yale dining halls? | This is expected to be a failure or partial failure: the chosen sources may include official hours and descriptions, but they may not contain enough direct student evidence about wait times. |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. Some documents are official marketing or informational pages, so they may not include candid student complaints about food quality, crowding, or wait times. This could make the system good at answering policy questions but weaker at answering experience-based questions.

2. Yale Hospitality pages repeat the same navigation menu and footer on every page. The ingestion pipeline must remove repeated navigation text, image labels, and footer links so that retrieval does not return irrelevant chunks.

3. Dynamic menu pages may be harder to scrape cleanly than static text pages. If Nutrislice menu content cannot be extracted reliably, the project should either store a manually saved menu snapshot or avoid depending on live menu details in evaluation questions.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

```text
Document Ingestion
  - Load web pages from the 10 source URLs
  - Strip repeated navigation, image labels, footer links, and empty lines
  - Save structured cleaned documents with title, source URL, and text

        |
        v

Chunking
  - Split by headings and paragraph boundaries
  - Target 350-500 words
  - Add about 75 words overlap for long sections
  - Save chunk text plus document metadata

        |
        v

Embedding + Vector Store
  - Embed chunks with sentence-transformers/all-MiniLM-L6-v2
  - Store vectors and metadata in ChromaDB

        |
        v

Retrieval
  - Accept a user question
  - Retrieve top 4 semantically similar chunks
  - Show retrieved chunk IDs and source titles for debugging

        |
        v

Grounded Generation + Interface
  - Send only retrieved chunks to Groq llama-3.3-70b-versatile
  - Instruct the model to answer only from retrieved context
  - Return answer with source attribution
  - Provide a simple query interface for demo
```

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

I will use Codex/ChatGPT/Cladue to help implement the ingestion and chunking scripts. I will provide the Domain, Documents, Chunking Strategy, and Anticipated Challenges sections from this planning file. I expect the AI tool to produce Python code that loads the source pages, removes repeated site navigation, saves cleaned documents, and chunks by section/paragraph boundaries. I will verify the output by inspecting several cleaned documents and sample chunks before building embeddings.

**Milestone 4 — Embedding and retrieval:**

I will use Codex/ChatGPT/Claude to help implement embedding and semantic retrieval with sentence-transformers and ChromaDB. I will provide the Retrieval Approach, Architecture, and Evaluation Plan sections. I expect the AI tool to produce scripts for building the vector index and running a query against top-k chunks. I will verify retrieval before generation by testing the five evaluation questions and checking whether the retrieved chunks contain the expected evidence.

**Milestone 5 — Generation and interface:**

I will use Codex/ChatGPT/Claude to help implement grounded generation and a simple query interface. I will provide the Architecture, Retrieval Approach, and Evaluation Plan sections, plus the requirement that answers must cite sources and must not use outside knowledge. I expect the AI tool to produce code that sends retrieved chunks to Groq and displays the answer with source attribution. I will verify the output by checking that unsupported questions return "not enough information" instead of hallucinated answers.
