# AI Documentation Assistant

A structure-aware Retrieval-Augmented Generation system that converts technical documentation into searchable, metadata-rich knowledge and generates grounded answers using semantic search, hybrid retrieval, reranking, and LLM-based response generation.

> Current status: Work in progress. The core focus is building a high-quality documentation ingestion and retrieval pipeline, especially for Markdown and MDX-based technical docs.

---

## Project Summary

| Area            | Description                                                                             |
| --------------- | --------------------------------------------------------------------------------------- |
| Project Type    | Documentation-focused RAG chatbot                                                       |
| Main Goal       | Answer questions from technical documentation with grounded, source-aware responses     |
| Core Focus      | Structure-aware parsing, chunk quality, retrieval precision, and LLM response grounding |
| Input Format    | Markdown and MDX documentation                                                          |
| Retrieval Style | Vector search + keyword search + hybrid fusion + reranking                              |
| Storage         | Qdrant vector database                                                                  |
| Generation      | LLM-based answer generation with query rewriting and verification                       |

---

## What This Project Does

Most basic RAG systems split documents into fixed-size chunks and directly embed them. That approach often loses important structure, especially in technical documentation where meaning depends on headings, code blocks, commands, tables, notes, warnings, and step-by-step procedures.

This project takes a more structured approach. It parses documentation into meaningful blocks, enriches them with metadata and generic NLP signals, builds retrieval-ready chunks, stores them in a vector database, and retrieves the most relevant context before generating an answer.

The system is designed for documentation-heavy use cases such as developer docs, API references, framework guides, internal engineering notes, and technical knowledge bases.

---

## Key Features

| Feature                   | Description                                                                               |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| Markdown/MDX ingestion    | Loads and normalizes documentation files before parsing                                   |
| Structure-aware parsing   | Preserves headings, paragraphs, lists, tables, code blocks, and MDX component context     |
| Generic signal extraction | Detects prose, commands, configuration, references, action steps, and code-like blocks    |
| IR block generation       | Converts parsed content into intermediate representation blocks for downstream processing |
| Relationship linking      | Connects related blocks such as explanations, commands, code examples, and tables         |
| Metadata-rich chunking    | Builds chunks with heading, context, type, subtype, and retrieval metadata                |
| Token-aware splitting     | Keeps chunks within practical token limits while preserving important context             |
| Validation layer          | Filters noisy, empty, duplicate, or weak chunks before indexing                           |
| Embeddings pipeline       | Converts validated chunks into dense vector representations                               |
| Qdrant integration        | Stores chunks and embeddings in a vector database                                         |
| BM25 retrieval            | Adds keyword-based retrieval for exact technical terms and command-style queries          |
| Hybrid retrieval          | Combines vector and keyword results using fusion logic                                    |
| Reranking                 | Improves final result ordering before answer generation                                   |
| LLM orchestration         | Rewrites queries, formats context, generates answers, and verifies responses              |
| Conversation memory       | Maintains recent interaction context for better follow-up answers                         |

---

## Architecture Overview

| Layer                    | Responsibility                                                                |
| ------------------------ | ----------------------------------------------------------------------------- |
| Document Loading         | Reads Markdown/MDX files and detects supported file types                     |
| Cleaning & Normalization | Cleans raw text and normalizes MDX-specific syntax                            |
| AST Parsing              | Converts Markdown/MDX into structured document elements                       |
| Enrichment               | Adds context, metadata, table/list/code information, and component awareness  |
| IR Layer                 | Builds standardized blocks with role, confidence, retrieval text, and signals |
| Relationship Layer       | Links related documentation blocks together                                   |
| Chunking Engine          | Routes blocks through text, list, code, table, and procedure handlers         |
| Token Control            | Splits or preserves chunks based on token size and content type               |
| Validation               | Removes poor-quality chunks and keeps high-value atomic chunks                |
| Embedding Pipeline       | Generates embeddings for valid chunks                                         |
| Vector Store             | Persists embeddings and payloads in Qdrant                                    |
| Retrieval                | Uses vector search, BM25 search, hybrid fusion, and reranking                 |
| Generation               | Produces grounded answers from retrieved documentation context                |

---

## Pipeline Flow

| Step | Stage                | Output                                                                             |
| ---: | -------------------- | ---------------------------------------------------------------------------------- |
|    1 | File detection       | Determines whether the input is Markdown or MDX                                    |
|    2 | Loading              | Reads raw documentation text                                                       |
|    3 | MDX normalization    | Converts MDX-specific patterns into parser-friendly content                        |
|    4 | Cleaning             | Removes formatting noise while preserving useful structure                         |
|    5 | AST parsing          | Produces structured elements from the document                                     |
|    6 | Enrichment           | Adds headings, list context, table structure, text metadata, and component context |
|    7 | IR block building    | Creates normalized documentation blocks with generic signals                       |
|    8 | Relationship linking | Connects related blocks for better context preservation                            |
|    9 | Chunk routing        | Sends content to text, code, list, table, or procedure handlers                    |
|   10 | Token enforcement    | Keeps chunk sizes retrieval-friendly                                               |
|   11 | Validation           | Filters weak or noisy chunks                                                       |
|   12 | Embedding            | Converts chunks into vectors                                                       |
|   13 | Indexing             | Stores vectors and metadata in Qdrant                                              |
|   14 | Retrieval            | Combines semantic and keyword search                                               |
|   15 | Reranking            | Reorders candidates based on query relevance                                       |
|   16 | Generation           | Builds grounded answers using retrieved context                                    |

---

## Parsing Philosophy

This project does not hardcode framework-specific or product-specific knowledge. Instead, it uses generic document and language signals to understand how technical content is structured.

| Signal Type       | Example Purpose                                                    |
| ----------------- | ------------------------------------------------------------------ |
| Sentence signals  | Detect whether a block looks like explanatory prose                |
| Action signals    | Identify instruction-like lines or procedural steps                |
| Code signals      | Detect code-like symbols, command patterns, or syntax-heavy blocks |
| Table signals     | Preserve tabular configuration or option references                |
| Heading context   | Keep content connected to its section hierarchy                    |
| List context      | Understand ordered steps, bullets, and grouped instructions        |
| Component context | Preserve useful MDX component boundaries and meaning               |
| Hygiene signals   | Detect malformed or noisy content such as conflict markers         |

These signals are feature extractors, not hardcoded answers. They help the ingestion pipeline preserve structure before embeddings and retrieval happen.

---

## Tech Stack

| Category         | Tools / Libraries                                                           |
| ---------------- | --------------------------------------------------------------------------- |
| Language         | Python                                                                      |
| API / Runtime    | FastAPI-style backend structure, CLI runner                                 |
| Document Parsing | Markdown/MDX parsing utilities, custom AST parsing, custom enrichment layer |
| Chunking         | Custom structure-aware chunking engine                                      |
| Embeddings       | SentenceTransformers-style local embedding pipeline                         |
| Vector Database  | Qdrant                                                                      |
| Keyword Search   | BM25                                                                        |
| Retrieval        | Vector search, keyword search, hybrid fusion                                |
| Reranking        | Custom reranking logic with query-aware scoring                             |
| LLM Layer        | Query rewriting, answer generation, answer verification                     |
| Conversation     | Short-term and long-term conversation memory modules                        |
| Environment      | dotenv-based configuration                                                  |

---

## Folder Structure

```text
rag/
├── conversation/
│   ├── formatter.py
│   ├── long_term.py
│   ├── manager.py
│   ├── memory.py
│   └── state.py
│
├── generation/
│   ├── formatting/
│   │   └── context_formatter.py
│   ├── llm/
│   │   ├── client.py
│   │   ├── generator.py
│   │   ├── orchestrator.py
│   │   ├── rewriter.py
│   │   └── verifier.py
│   └── prompting/
│       ├── builder.py
│       ├── context_block.py
│       ├── dialogue.py
│       ├── history_block.py
│       ├── identity.py
│       ├── reasoning.py
│       ├── rules.py
│       ├── structure.py
│       └── style.py
│
├── ingestion/
│   ├── parser/
│   │   ├── adapters/
│   │   │   └── mdx_adapter.py
│   │   ├── enrichment/
│   │   │   ├── component_context.py
│   │   │   ├── enricher.py
│   │   │   ├── lists.py
│   │   │   ├── metadata.py
│   │   │   ├── tables.py
│   │   │   └── texts.py
│   │   ├── ir/
│   │   │   ├── block_builder.py
│   │   │   ├── relationships.py
│   │   │   ├── schema.py
│   │   │   └── signals.py
│   │   ├── ast_parser.py
│   │   ├── cleaner.py
│   │   ├── filetype.py
│   │   ├── heading_builder.py
│   │   ├── list_parser.py
│   │   ├── markdown.py
│   │   ├── metadata.py
│   │   └── table_parser.py
│   │
│   ├── chunking/
│   │   ├── engine/
│   │   │   ├── builders/
│   │   │   │   ├── chunk_builder.py
│   │   │   │   └── prefix_builder.py
│   │   │   ├── detectors/
│   │   │   │   ├── density.py
│   │   │   │   ├── intent.py
│   │   │   │   └── structure.py
│   │   │   ├── handlers/
│   │   │   │   ├── code.py
│   │   │   │   ├── list.py
│   │   │   │   ├── procedure.py
│   │   │   │   ├── table.py
│   │   │   │   └── text.py
│   │   │   ├── splitters/
│   │   │   │   ├── procedure.py
│   │   │   │   ├── structured.py
│   │   │   │   └── text.py
│   │   │   ├── utils/
│   │   │   │   └── grouping.py
│   │   │   └── orchestrator.py
│   │   ├── chunker.py
│   │   ├── models.py
│   │   ├── overlap.py
│   │   ├── section_splitter.py
│   │   ├── token_splitter.py
│   │   ├── utils.py
│   │   └── validator.py
│   │
│   └── embeddings/
│       ├── embedder.py
│       ├── pipeline.py
│       ├── schema.py
│       ├── store.py
│       └── validator.py
│
├── retrieval/
│   ├── fusion/
│   │   └── hybrid.py
│   ├── keyword_search/
│   │   └── bm25.py
│   ├── reranking/
│   │   └── reranker.py
│   └── vector_search/
│       └── cosine_similarity.py
│
├── embed.py
├── parse_mdx.py
├── test_parser.py
├── chunk_test.py
└── serve.py
```

---

## Important Modules

| Module                                          | Purpose                                                    |
| ----------------------------------------------- | ---------------------------------------------------------- |
| `rag/ingestion/parser/__init__.py`              | Main parser entrypoint for Markdown/MDX documents          |
| `rag/ingestion/parser/adapters/mdx_adapter.py`  | Normalizes MDX content before parsing                      |
| `rag/ingestion/parser/ir/signals.py`            | Extracts generic NLP and syntax signals from blocks        |
| `rag/ingestion/parser/ir/block_builder.py`      | Builds standardized intermediate representation blocks     |
| `rag/ingestion/parser/ir/relationships.py`      | Links related blocks for context preservation              |
| `rag/ingestion/chunking/chunker.py`             | Main chunking pipeline orchestrator                        |
| `rag/ingestion/chunking/engine/orchestrator.py` | Routes parsed blocks through specialized handlers          |
| `rag/ingestion/chunking/validator.py`           | Validates chunks before indexing                           |
| `rag/ingestion/embeddings/pipeline.py`          | Embedding pipeline for validated chunks                    |
| `rag/ingestion/embeddings/store.py`             | Qdrant storage integration                                 |
| `rag/retrieval/keyword_search/bm25.py`          | BM25 keyword retrieval                                     |
| `rag/retrieval/fusion/hybrid.py`                | Hybrid result fusion                                       |
| `rag/retrieval/reranking/reranker.py`           | Query-aware reranking logic                                |
| `rag/generation/llm/orchestrator.py`            | Coordinates rewriting, answer generation, and verification |
| `rag/conversation/manager.py`                   | Manages recent conversation state                          |

---

## Retrieval Strategy

| Retrieval Component    | Role                                                               |
| ---------------------- | ------------------------------------------------------------------ |
| Vector Search          | Finds semantically similar chunks                                  |
| BM25 Search            | Captures exact terms, command names, flags, and technical keywords |
| Hybrid Fusion          | Combines semantic and keyword retrieval results                    |
| Reranking              | Reorders candidates using query-aware scoring and metadata signals |
| LLM Context Formatting | Converts selected chunks into a clean prompt context               |

This combination is useful for technical documentation because many queries require both semantic understanding and exact keyword matching.

---

## Why Hybrid Retrieval?

Technical documentation often contains exact tokens that matter:

| Example        | Why Exact Matching Matters                                    |
| -------------- | ------------------------------------------------------------- |
| CLI commands   | `dev`, `build`, `start`, `typegen` should not be blurred away |
| Flags          | `--port`, `--https`, `--debug` require exact matching         |
| Config keys    | Configuration names often have precise spelling               |
| API names      | Function, class, and module names need lexical precision      |
| Error messages | Small wording differences can change the answer               |

Vector search helps with meaning. BM25 helps with exactness. Hybrid retrieval brings both into the same pipeline.

---

## Current Project Status

| Area                 | Status                   |
| -------------------- | ------------------------ |
| Markdown parsing     | In progress              |
| MDX normalization    | In progress              |
| IR block generation  | In progress              |
| Relationship linking | In progress              |
| Chunking engine      | In progress              |
| Embeddings pipeline  | In progress              |
| Qdrant storage       | Integrated               |
| BM25 retrieval       | Integrated               |
| Hybrid retrieval     | Integrated               |
| Reranking            | Experimental             |
| LLM generation       | Integrated               |
| Conversation memory  | Basic implementation     |
| Production readiness | Not yet production-ready |

---

## Roadmap

| Priority | Task                                                       |
| -------- | ---------------------------------------------------------- |
| High     | Improve MDX parsing accuracy for real-world docs           |
| High     | Strengthen chunk validation and reduce noisy chunks        |
| High     | Improve retrieval evaluation with test queries             |
| Medium   | Add better source citation support                         |
| Medium   | Add document upload API                                    |
| Medium   | Add frontend chat interface                                |
| Medium   | Improve query processing and intent detection              |
| Low      | Add dashboard for chunk inspection and retrieval debugging |
| Low      | Add automated benchmarks for parser and retrieval quality  |

---

## Example Use Cases

| Use Case                        | Description                                                  |
| ------------------------------- | ------------------------------------------------------------ |
| Developer documentation chatbot | Answer questions from framework or library documentation     |
| Internal engineering assistant  | Search internal docs, setup guides, and engineering notes    |
| API support assistant           | Retrieve accurate answers from API references                |
| Technical onboarding assistant  | Help new developers understand project documentation         |
| CLI documentation assistant     | Answer command, flag, option, and workflow-related questions |
| Knowledge base search           | Improve retrieval over structured technical content          |

---

## Design Goals

| Goal                           | Explanation                                                                             |
| ------------------------------ | --------------------------------------------------------------------------------------- |
| Preserve structure             | Avoid losing meaning by separating headings, code, tables, and explanations incorrectly |
| Stay domain-independent        | Use generic parsing signals instead of framework-specific hardcoding                    |
| Improve chunk quality          | Build chunks that are useful for retrieval, not just text fragments                     |
| Support exact technical search | Combine embeddings with keyword retrieval for commands, flags, and config names         |
| Keep answers grounded          | Generate answers only from retrieved documentation context                              |
| Make debugging easier          | Keep metadata, chunk types, and signals visible for inspection                          |

---

## License

This project is licensed under the MIT License.
