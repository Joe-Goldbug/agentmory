# ObsidianVault - Trae Second Brain

> LLM-powered knowledge management based on Karpathy approach

## What is This

Personal knowledge management system integrating:
- Trae + Claude Code workflow automation
- GStack Skills system
- sage-wiki LLM compilation engine
- Obsidian visual knowledge base

## Core Loop

```
You work (Trae / Claude Code / CLI)
    ↓
MCP Server monitors
    ↓
sage-wiki auto-organizes
    ↓
ObsidianVault auto-updates
    ↓
GitHub private repo auto-syncs
```

## Vault Structure

```
ObsidianVault/
├── 01-工作流/            # Claude Code standard workflow
├── 02-Skills/            # GStack + custom Skills index
├── 03-Memory/            # User config, experience
├── 04-Projects/          # Project-specific knowledge
├── 05-Raw-Sources/       # Raw source backup
└── config.yaml           # sage-wiki config
```

The MASTER-* files at the vault root remain the canonical source notes; these folders are the organized module entry points.

## Tech Stack

| Component | Purpose |
|-----------|---------|
| sage-wiki | LLM engine + MCP Server |
| Obsidian | Knowledge base visualization |
| Trae | AI IDE |
| Claude Code | CLI AI Agent |

## Features

- Passive沉淀 - Just work, AI auto-summarizes
- Bidirectional links - Auto-connected notes
- MCP integration - Trae/Claude Code seamless
- Auto-sync - Session end auto Git commit
- Version control - GitHub private repo

## Karpathy Three-Layer Architecture

```
Layer 3: SCHEMA      ← Tell AI how to understand Wiki
Layer 2: The Wiki    ← Auto-evolving knowledge base
Layer 1: Raw Sources ← Raw data read-only
```

## Quick Start

```bash
git clone https://github.com/EthanLau1/obsidian-vault-Ethan.git
cd obsidian-vault-Ethan

# Install sage-wiki
go install github.com/xoai/sage-wiki/cmd/sage-wiki@latest

# Initialize
sage-wiki init --vault

# Open in Obsidian → Select Vault → ~/Documents/ObsidianVault
```

## Philosophy

> "Do not use LLM as a search engine, but like a programmer maintaining a Markdown knowledge base."
> — Andrej Karpathy

---

**Last Updated**: 2026-04-07
**Maintainer**: Ethan (@EthanLau1)
**License**: Private - All Rights Reserved
