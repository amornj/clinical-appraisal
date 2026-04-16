# clinical-appraisal

AI-assisted CLI tool that produces a structured critical appraisal of a clinical study PDF,
saves it to your Obsidian Journal, and emails the PDF to Readwise Reader.

## Framework

Based on **Al-Jundi & Sakka (JCDR 2017)** — 10 universal standard questions applied to every paper,
plus study-type-specific checklists (CONSORT for RCTs, PRISMA for systematic reviews).

## What it produces

A clinical document PDF covering:

1. Paper overview (journal, title, authors, COI, funding)
2. PICO (P / I / C / O)
3. Study type classification (Therapy / Aetiology / Prognosis / Diagnosis / Cost-effectiveness)
4. Abstract appraisal
5. Introduction / background
6. 10 standard questions — each answered with sub-checklist items
7. Study-type checklist (CONSORT / PRISMA / Observational)
8. Statistical appraisal (p-values, CIs, clinical vs statistical significance)
9. Ethics
10. Limitations
11. Bottom line / clinical verdict

## Output

| Artefact | Location |
|---|---|
| PDF | `./output/<date>-<stem>-appraisal.pdf` |
| Markdown | `/Users/home/projects/obsidian/Journal/<date>-<stem>-appraisal.md` |

## Authentication

OAuth only. The tool reads `~/.codex/auth.json`:

```json
{
  "tokens": {
    "access_token": "<your-oauth-token>"
  }
}
```

If the file is missing or the token is empty the tool exits immediately with a clear error.
There is no API-key fallback and no heuristic fallback — GPT-5.4 or nothing.

## Requirements

- macOS (Apple Mail for email delivery)
- Python 3.10+
- `pdftotext`: `brew install poppler`
- `fpdf2`: `pip3 install fpdf2`
- OAuth token in `~/.codex/auth.json`

## Usage

```bash
# Standard
clinical-appraisal /path/to/study.pdf

# Skip email (useful during testing)
clinical-appraisal /path/to/study.pdf --no-email
```

### All options

| Argument | Default | Description |
|---|---|---|
| `pdf` | *(required)* | Input study PDF |
| `--email` | `amornj@library.readwise.io` | Recipient email |
| `--outdir` | `./output` | PDF output directory |
| `--model` | `gpt-5.4` | Model ID |
| `--no-email` | *(flag)* | Skip email delivery |

## Installation

The tool is symlinked to `~/.local/bin/clinical-appraisal` (already on `$PATH`):

```bash
ln -sf /Users/home/projects/clinical-appraisal/clinical_appraisal.py ~/.local/bin/clinical-appraisal
chmod +x /Users/home/projects/clinical-appraisal/clinical_appraisal.py
```

## License

MIT
