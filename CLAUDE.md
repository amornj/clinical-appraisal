# CLAUDE.md — clinical-appraisal

## Project overview

A CLI tool that converts a clinical-study PDF into a structured critical-appraisal document (markdown + presentation PDF) and emails it to a configured recipient.

## Key entry point

`clinical_appraisal.py` — single-file Python 3 CLI. No external packages beyond stdlib.

## Default model

**GPT-5.4** via the OpenAI Responses API (`https://api.openai.com/v1/responses`).

## Authentication strategy (OAuth-first)

The tool resolves a bearer token in this priority order:

1. `OPENAI_API_KEY` environment variable (standard API key).
2. **OAuth access token** read from `~/.codex/auth.json` at key path `tokens.access_token` — this is the primary method for this project.

The loader is `load_oauth_access_token()` at line 124. The token is passed as a standard `Authorization: Bearer` header to the Responses API, so OAuth and API-key paths are interchangeable at the HTTP level.

## Important file paths (user-specific, do not change without checking)

| Constant | Purpose |
|---|---|
| `DEFAULT_FRAMEWORK` | Framework PDF (`~/.openclaw/media/inbound/jcdr-*.pdf`) |
| `DEFAULT_RENDERER` | Markdown → PDF script (`~/.openclaw/workspace/md_to_presentation_pdf.py`) |
| `DEFAULT_EMAIL` | Readwise Reader email (`amornj@library.readwise.io`) |
| `DEFAULT_CODEX_AUTH` | OAuth token file (`~/.codex/auth.json`) |

## Appraisal pipeline

```
Input PDF
  ↓ pdftotext
study_text
  ↓ appraise_with_gpt()   ← tries GPT-5.4 first
  │     (falls back to)
  └─ appraise()            ← heuristic regex-based fallback
  ↓
Markdown file  (output/<stem>-clinical-appraisal.md)
  ↓ md_to_presentation_pdf.py
PDF file       (output/<stem>-clinical-appraisal.pdf)
  ↓ osascript / Apple Mail
Email to recipient
```

## Framework used for critical appraisal

Based on **Al-Jundi & Sakka, JCDR 2017** — 10 standard questions covering: research question, study design, selection, outcomes, confounders, statistical method, results, conclusions, ethics. Extra checklists for RCTs (CONSORT-style) and systematic reviews (PRISMA-style).

## Running the tool

```bash
# Minimal — uses all defaults
python3 clinical_appraisal.py /path/to/study.pdf

# Full options
python3 clinical_appraisal.py /path/to/study.pdf \
  --framework /path/to/framework.pdf \
  --email you@example.com \
  --model gpt-5.4 \
  --outdir ./output \
  --no-email
```

## Development notes

- Python 3.10+ required (uses `str | None` union syntax).
- `pdftotext` (poppler-utils) must be on `PATH`.
- Apple Mail must be configured on the host machine for email delivery.
- The tool is intentionally dependency-free (no `pip install` needed).
- Do **not** add speculative features or extra abstraction layers — the single-file design is intentional.

## Testing

There is no test suite. Manual testing: run against a real PDF and verify markdown output. Check `output/` for generated files.

## Output

Files are written to `./output/` by default:
- `<stem>-clinical-appraisal.md`
- `<stem>-clinical-appraisal.pdf`
