# Implementation Plan & Architectural Specs

> [!NOTE]
> Active living-brand system specifications, contract schemas, and operational guides reside under [`docs/specs/`](file:///Users/ryanjohnson/Projects/brand-maker-spec/docs/specs/).

## Core Design Principles

- **Local-First & Offline Capable**: All brand systems, workspaces, assets, and compliance checking run locally on SQLite without cloud dependencies.
- **Contract-Driven Boundaries**: Strict Pydantic model validation on requests, internal persistence models, and LLM output envelopes.
- **Non-Blocking Storage**: Async execution of SQLite transactions and file I/O using worker thread pools (`run_in_threadpool`).
- **Resilient AI Generation**: Optimistic concurrency handling for simultaneous user autosaves during background section generation runs.
- **Deduplicated & Reference-Guarded Storage**: Content-addressed asset storage with reference counting and audit log snapshot depth bounding.
