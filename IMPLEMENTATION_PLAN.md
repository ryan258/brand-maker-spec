# Implementation Plan & Architectural Specs

> [!NOTE]
> Active living-brand system specifications, contract schemas, and operational guides reside under [`docs/specs/`](docs/specs/).

## Core Design Principles

- **Local-First**: Brand systems, workspaces, assets, and compliance checking are stored and
  evaluated locally on SQLite. It is not offline-capable: startup requires an OpenRouter API
  key, generation and logo creation call a remote provider, and some browser pages load fonts
  from a public CDN. Authoring, editing, readiness, exports, and deterministic compliance do
  work without a provider call.
- **Contract-Driven Boundaries**: Strict Pydantic model validation on requests, internal persistence models, and LLM output envelopes.
- **Non-Blocking Storage**: Async execution of SQLite transactions and file I/O using worker thread pools (`run_in_threadpool`).
- **Resilient AI Generation**: Optimistic concurrency handling for simultaneous user autosaves during background section generation runs.
- **Deduplicated & Reference-Guarded Storage**: Content-addressed asset storage with reference counting and audit log snapshot depth bounding.
