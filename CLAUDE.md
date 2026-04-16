# CLAUDE.md — clinical-appraisal

## Project overview

Single-file Python 3 CLI that converts a clinical-study PDF into a structured critical-appraisal
document and emails it to Readwise Reader. No external packages beyond stdlib + `fpdf2`.

## Entry point

`clinical_appraisal.py` — all logic lives here.

## Default model

**GPT-5.4** via the OpenAI Responses API (`https://api.openai.com/v1/responses`).

## Authentication — OAuth only

The tool reads an OAuth access token from `~/.codex/auth.json` at key path `tokens.access_token`.
There is no `OPENAI_API_KEY` fallback. If the token is missing, empty, or the API returns an HTTP
error, the tool prints a clear human-readable message and exits non-zero. No silent fallbacks.

Relevant function: `load_oauth_token()`.

## Output routing

| Artefact | Destination |
|---|---|
| Markdown | `/Users/home/projects/obsidian/Journal/<date>-<stem>-appraisal.md` |
| PDF | `./output/<date>-<stem>-appraisal.pdf` (or `--outdir`) |

The PDF is rendered directly from markdown using `fpdf2` (no external renderer, no LaTeX).
No markdown is written to the output folder.

## Appraisal framework — Al-Jundi & Sakka (JCDR 2017)

Three layers, all enforced in the GPT-5.4 prompt:

1. **Paper overview** — journal, title, authors, institution, funding/COI
2. **PICO** — P, I, C, O parsed explicitly
3. **Study type classification** — one of 5 clinical question categories + specific design
4. **10 standard questions** — each answered with sub-checklist items from the article
5. **Study-type checklist** — CONSORT (RCT), PRISMA (SR/meta-analysis), or Observational
6. **Statistical appraisal** — p-values, CIs, absolute vs relative risk, clinical significance
7. **Ethics** — IRB, COI, funding
8. **Limitations & future research**
9. **Bottom line / clinical verdict**

The prompt is in `SYSTEM_PROMPT` + `APPRAISAL_TEMPLATE` constants — edit those to change the
output structure.

## PDF renderer

`render_clinical_pdf(markdown, pdf_path)` uses `fpdf2` to produce a white-background clinical
document (not a dark-slide presentation):
- Navy header bar for `#` headings
- Light-blue fill for `##` section headings
- Red-accent `###` sub-headings
- Bullet list support, horizontal rules, italic footer line

## Running the tool

```bash
# Standard usage
clinical-appraisal /path/to/study.pdf

# Skip email (development)
clinical-appraisal /path/to/study.pdf --no-email

# All options
clinical-appraisal /path/to/study.pdf \
  --email you@example.com \
  --outdir ./output \
  --model gpt-5.4 \
  --no-email
```

## Error handling

| Condition | Behaviour |
|---|---|
| `~/.codex/auth.json` missing | Clear message + exit 1 |
| `access_token` empty/missing | Clear message + exit 1 |
| API HTTP error (401, 429, 5xx) | HTTP code + response body + exit 1 |
| Network error | Reason + exit 1 |
| Empty GPT response | Full response JSON + exit 1 |
| `pdftotext` not found | Install hint + exit 1 |
| `fpdf2` not installed | Install hint + exit 1 |
| Input PDF not found | Path + exit 1 |

## Dependencies

- Python 3.10+ (uses `str | None` union syntax)
- `pdftotext` — `brew install poppler`
- `fpdf2` — already installed (`fpdf2 2.8.6`)
- macOS Mail — required for email delivery

## Design rules

- Single file, no `pip install` setup, no framework.
- Do not add heuristic fallbacks — GPT-5.4 or exit.
- Do not add slides/presentation output — it's a clinical document.
- The Obsidian Journal path and Readwise email are intentional user preferences; do not parameterise them away.
