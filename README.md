# clinical-appraisal

AI-assisted CLI tool that converts a clinical-study PDF into a structured critical-appraisal document (markdown + presentation PDF) and emails it to Readwise Reader.

## Features

- Extracts text from any clinical PDF with `pdftotext`
- Appraises the study with **GPT-5.4** via the OpenAI Responses API
- Falls back to a built-in heuristic appraisal if no credentials are available
- Applies the **Al-Jundi & Sakka (JCDR 2017)** critical-appraisal framework
- Generates RCT (CONSORT-style) or Systematic Review (PRISMA-style) checklists automatically
- Outputs a markdown file and a presentation-style PDF
- Emails the result via Apple Mail

## Authentication

The tool uses **OAuth** as the primary authentication method. It reads an access token from `~/.codex/auth.json`:

```json
{
  "tokens": {
    "access_token": "<your-oauth-token>"
  }
}
```

As a fallback, set the `OPENAI_API_KEY` environment variable:

```bash
export OPENAI_API_KEY=sk-...
```

## Requirements

- macOS (Apple Mail required for email delivery)
- Python 3.10+
- `pdftotext` (install via `brew install poppler`)
- `~/.openclaw/workspace/md_to_presentation_pdf.py` (markdown → PDF renderer)
- OAuth token in `~/.codex/auth.json` **or** `OPENAI_API_KEY` set

## Usage

```bash
# Minimal — uses all defaults
python3 clinical_appraisal.py /path/to/study.pdf
```

```bash
# Full options
python3 clinical_appraisal.py /path/to/study.pdf \
  --framework /path/to/framework.pdf \
  --email you@example.com \
  --model gpt-5.4 \
  --outdir ./output \
  --no-email
```

### Arguments

| Argument | Default | Description |
|---|---|---|
| `pdf` | *(required)* | Input study PDF |
| `--framework` | `~/.openclaw/media/inbound/jcdr-*.pdf` | Framework PDF for appraisal structure |
| `--email` | `amornj@library.readwise.io` | Recipient email address |
| `--model` | `gpt-5.4` | AI model to use |
| `--outdir` | `./output` | Output directory |
| `--no-email` | *(flag)* | Skip email delivery |

## Output

Files are written to `./output/` (or `--outdir`):

- `<stem>-clinical-appraisal.md` — full appraisal in markdown
- `<stem>-clinical-appraisal.pdf` — presentation-style PDF

## Appraisal structure

The markdown output includes:

1. Citation (journal, year, DOI)
2. Framework summary (Al-Jundi & Sakka)
3. Rapid study identification (inferred study type)
4. Research question
5. Methods snapshot
6. Results snapshot
7. Strange / weak methodologic points
8. Checklist-driven questions (10 standard questions)
9. Clinical appraisal lens (RCT / SR / observational)
10. Discussion and interpretation
11. Bottom line
12. Presentation slides (8–12 slide sections in markdown)

## Model

Default model: **GPT-5.4** (`gpt-5.4`)

Override with `--model <model-id>`.

## License

MIT
