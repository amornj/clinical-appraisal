#!/usr/bin/env python3
"""clinical-appraisal — AI-assisted critical appraisal of clinical study PDFs.

Authentication: Delegates to `codex exec` which handles ChatGPT OAuth internally.
Model: gpt-5.4 (default).
Framework: Al-Jundi & Sakka, JCDR 2017 — 10 standard questions + CONSORT/PRISMA.
Output: PDF → --outdir (default ./output), Markdown → Obsidian Journal.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# ── defaults ──────────────────────────────────────────────────────────────────
DEFAULT_EMAIL      = 'amornj@library.readwise.io'
DEFAULT_MODEL      = 'gpt-5.4'
DEFAULT_OUTDIR     = Path('output')
OBSIDIAN_JOURNAL   = Path('/Users/home/projects/obsidian/Journal')

# ── colours for the clinical PDF (fpdf2) ──────────────────────────────────────
C_HEADER_BG  = (20,  60, 120)
C_HEADER_FG  = (255, 255, 255)
C_SECTION_BG = (235, 241, 250)
C_SECTION_FG = (20,  60, 120)
C_BODY_FG    = (30,  30,  30)
C_ACCENT     = (180,  20,  20)
C_RULE       = (180, 195, 215)


# ── utilities ─────────────────────────────────────────────────────────────────

def pdf_text(path: Path) -> str:
    try:
        return subprocess.check_output(['pdftotext', str(path), '-'], text=True)
    except subprocess.CalledProcessError as e:
        print(f'Error: pdftotext failed for "{path}" (exit {e.returncode}).\n'
              'Make sure pdftotext is installed: brew install poppler', file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print('Error: pdftotext not found. Install with: brew install poppler', file=sys.stderr)
        sys.exit(1)


def sanitise_path(raw: str) -> Path:
    """Strip shell backslash-escapes left inside double-quoted arguments."""
    return Path(raw.replace('\\ ', ' ').replace('\\', ''))


# ── GPT-5.4 appraisal via codex exec ─────────────────────────────────────────

APPRAISAL_PROMPT = """You are a senior clinician-statistician producing a structured critical appraisal
of a clinical research article. Follow the Al-Jundi & Sakka (JCDR 2017) framework exactly.

Rules:
- Be concise, skeptical, and clinically useful.
- Do NOT invent numbers, results, or citations not present in the paper.
- If a section is absent from the paper, say so explicitly — do not omit the heading.
- Use plain markdown (headers, bullet lists, bold for key terms). No tables.
- Output ONLY the appraisal markdown — no explanations, no preamble, no tool calls.
- Do NOT read any files or run any commands. The study text is provided below.

Produce a complete critical appraisal using this exact structure:

# Critical Appraisal: [full paper title]

## Paper Overview
- **Journal:**
- **Year:**
- **DOI:**
- **Authors & Institutions:**
- **Funding / Conflicts of Interest:**

## PICO
- **P — Patient / Problem / Population:**
- **I — Intervention:**
- **C — Comparison:**
- **O — Outcome(s):**

## Study Type Classification
- **Clinical question category:** (one of: Therapy | Aetiology/Causation | Prognosis | Diagnosis | Cost-effectiveness)
- **Specific study design:** (e.g., RCT, cohort, case-control, cross-sectional, SR/meta-analysis, economic analysis)
- **Appropriateness of design for the question:**

## Abstract Appraisal
- **Aim clearly stated:**
- **Methods summary (design, groups, sample size, randomisation, measurement tools):**
- **Results summary (key variables, statistics, significance):**
- **Conclusion answers the question:**

## Introduction / Background
- **Rationale and gap addressed:**
- **Prior work referenced appropriately:**
- **Study purpose identified prospectively or post-hoc:**

---

## 10 Standard Questions (Al-Jundi & Sakka)

### Q1 — What is the research question?
Answer using PICO. Is the question clinically significant and clearly focused?

### Q2 — What is the study type (design)?
Is the design appropriate for the clinical question? Is randomisation described (type, stratification)?
Is there a control group? Are samples similar at baseline?

### Q3 — Selection issues
- How were subjects recruited? Is the sample representative?
- Eligibility criteria stated with reasons?
- Sample size justified (power calculation)?
- Blinding: who was blinded (participants, assessors, analysts)?
- Dropout rate and attrition handling?
- Potential selection biases (prevalence bias, admission-rate bias, volunteer bias, recall bias, lead-time bias, detection bias)?

### Q4 — Outcome factors and measurement
- All relevant outcomes assessed?
- Measurement tools valid and reliable?
- Intra/inter-examiner reliability reported?
- Measurement error an important source of bias?

### Q5 — Study factors and measurement
- All relevant study factors included?
- Factors measured with appropriate, validated tools?

### Q6 — Confounders
- Potential confounders identified and controlled?
- Methods used: matching, restriction, randomisation, blinding, regression adjustment?
- Is confounding an important residual concern?

### Q7 — Statistical methods
- Tests appropriate for the data type and distribution?
- Methods described in sufficient detail to reproduce?
- Confidence intervals and p-values reported?
- Absolute risk reduction reported alongside relative risk reduction?

### Q8 — Statistical results
- Do results directly answer the research question?
- p-value interpretation: statistical vs clinical significance distinguished?
- Confidence interval width — is precision adequate?
- Adverse events reported?
- Subgroup analyses: pre-specified or exploratory?

### Q9 — Conclusions
- Conclusions justified by the data?
- Authors avoid extrapolating beyond the data?
- Limitations acknowledged, with effects on outcomes discussed?
- Suggestions for future research?
- Bibliography follows a standard format?

### Q10 — Ethics
- Ethics approval / IRB stated?
- Identifiable ethical issues?
- Conflicts of interest declared?

---

## Study-Type Checklist

[Apply CONSORT if RCT; PRISMA if SR/meta-analysis; Observational checklist otherwise.]

**For RCT (CONSORT):**
- Allocation (randomisation method, stratification, concealment):
- Blinding (participants, providers, assessors):
- Follow-up and intention-to-treat analysis:
- Data collection and bias control:
- Power calculation and sample size:
- Results clarity and precision:
- Applicability to local / target population:

**For SR / Meta-analysis (PRISMA):**
- Search strategy (published + unpublished + non-English + expert contact):
- Quality control of included studies (scoring system, >=2 reviewers):
- Homogeneity of included studies:
- Precision and clarity of results:
- Applicability to local population:

**For Observational / Other:**
- Sample selection method and representativeness:
- Control of confounding:
- Measurement validity and reliability:
- Follow-up completeness:
- Generalisability (external validity):

---

## Statistical Appraisal
- Primary result(s) with exact values (mean +/- SD, HR, OR, RR, MD, NNT — whatever is reported):
- p-value(s) and interpretation:
- Confidence interval(s) and clinical meaning:
- Clinical significance vs statistical significance:
- Effect size — is it clinically meaningful?

## Limitations
List the study's own stated limitations and any additional ones identified.

## Bottom Line / Clinical Verdict
A 3-5 sentence synthesis: what this study adds, its key methodological strengths and weaknesses,
and whether the findings are trustworthy enough to influence clinical practice.

---
*Appraisal generated {date} using {model} | Framework: Al-Jundi & Sakka, JCDR 2017*

---

Study text follows:

{study_text}
"""


def appraise_with_codex(study_text: str, pdf_name: str, model: str) -> str:
    """Call GPT via `codex exec` which handles ChatGPT OAuth internally."""

    # Check codex is available
    try:
        subprocess.check_output(['codex', '--version'], text=True, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        print('Error: codex CLI not found on PATH.\n'
              'Install: npm install -g @openai/codex', file=sys.stderr)
        sys.exit(1)

    # Check login status
    try:
        status = subprocess.check_output(
            ['codex', 'login', 'status'], text=True, stderr=subprocess.STDOUT
        ).strip()
    except subprocess.CalledProcessError:
        status = ''
    if 'Logged in' not in status:
        print('Error: Not logged in to Codex.\n'
              'Please run: codex login\n'
              'Then try again.', file=sys.stderr)
        sys.exit(1)

    date = datetime.now().strftime('%Y-%m-%d %H:%M')
    prompt = APPRAISAL_PROMPT.format(
        date=date,
        model=model,
        study_text=study_text[:72000],
    )

    # Write prompt to temp file (avoids shell argument length limits)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(prompt)
        prompt_path = Path(f.name)

    # Write output to temp file
    output_path = Path(tempfile.mktemp(suffix='.md'))

    print(f'Sending to {model} via codex…', flush=True)
    try:
        result = subprocess.run(
            [
                'codex', 'exec',
                '-m', model,
                '--sandbox', 'read-only',
                '--ephemeral',
                '--skip-git-repo-check',
                '-o', str(output_path),
            ],
            stdin=open(prompt_path),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        print('Error: codex exec timed out after 10 minutes.', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'Error: Failed to run codex exec: {e}', file=sys.stderr)
        sys.exit(1)
    finally:
        prompt_path.unlink(missing_ok=True)

    if result.returncode != 0:
        stderr_msg = result.stderr.strip()
        # Check for common auth/rate-limit issues
        if 'usage limit' in stderr_msg.lower() or 'expired' in stderr_msg.lower():
            print(f'Error: Codex authentication or rate limit issue.\n{stderr_msg}\n'
                  'Try: codex login', file=sys.stderr)
        else:
            print(f'Error: codex exec failed (exit {result.returncode}).\n{stderr_msg}', file=sys.stderr)
        sys.exit(1)

    # Read output
    if output_path.exists():
        markdown = output_path.read_text(encoding='utf-8').strip()
        output_path.unlink(missing_ok=True)
    else:
        markdown = ''

    if not markdown:
        print('Error: codex exec produced no output.\n'
              f'stdout: {result.stdout[:500]}\n'
              f'stderr: {result.stderr[:500]}', file=sys.stderr)
        sys.exit(1)

    return markdown


# ── PDF rendering (fpdf2, clinical document style) ────────────────────────────

_UNICODE_MAP = str.maketrans({
    '\u2014': '--',   # em dash
    '\u2013': '-',    # en dash
    '\u2018': "'",    # left single quote
    '\u2019': "'",    # right single quote
    '\u201c': '"',    # left double quote
    '\u201d': '"',    # right double quote
    '\u2022': '-',    # bullet
    '\u2026': '...',  # ellipsis
    '\u00b1': '+/-',  # plus-minus
    '\u2264': '<=',   # less-than-or-equal
    '\u2265': '>=',   # greater-than-or-equal
    '\u00d7': 'x',    # multiplication sign
    '\u2192': '->',   # right arrow
    '\u00a0': ' ',    # non-breaking space
})


def _latin1_safe(text: str) -> str:
    """Replace Unicode characters that Helvetica (latin-1) can't render."""
    text = text.translate(_UNICODE_MAP)
    # Drop anything still outside latin-1
    return text.encode('latin-1', errors='replace').decode('latin-1')


def render_clinical_pdf(markdown: str, pdf_path: Path) -> None:
    try:
        from fpdf import FPDF
    except ImportError:
        print('Error: fpdf2 not installed. Run: pip3 install fpdf2', file=sys.stderr)
        sys.exit(1)

    class ClinicalPDF(FPDF):
        def header(self):
            pass

        def footer(self):
            self.set_y(-12)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(*C_RULE)
            self.cell(0, 8, f'Page {self.page_no()}', align='C')

    pdf = ClinicalPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()

    usable_w = pdf.w - pdf.l_margin - pdf.r_margin

    def rule():
        pdf.set_draw_color(*C_RULE)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + usable_w, pdf.get_y())
        pdf.ln(2)

    def h1(text: str):
        text = _latin1_safe(re.sub(r'^#+\s*', '', text))
        pdf.set_fill_color(*C_HEADER_BG)
        pdf.set_text_color(*C_HEADER_FG)
        pdf.set_font('Helvetica', 'B', 13)
        pdf.cell(usable_w, 9, text, fill=True, new_x='LMARGIN', new_y='NEXT')
        pdf.ln(2)
        pdf.set_text_color(*C_BODY_FG)

    def h2(text: str):
        text = _latin1_safe(re.sub(r'^#+\s*', '', text))
        pdf.set_fill_color(*C_SECTION_BG)
        pdf.set_text_color(*C_SECTION_FG)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(usable_w, 7, text, fill=True, new_x='LMARGIN', new_y='NEXT')
        pdf.ln(1)
        pdf.set_text_color(*C_BODY_FG)

    def h3(text: str):
        text = _latin1_safe(re.sub(r'^#+\s*', '', text))
        pdf.set_text_color(*C_ACCENT)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.multi_cell(usable_w, 6, text)
        pdf.set_text_color(*C_BODY_FG)
        pdf.ln(0.5)

    def body(text: str):
        pdf.set_font('Helvetica', '', 9.5)
        pdf.set_text_color(*C_BODY_FG)
        pdf.multi_cell(usable_w, 5.5, _latin1_safe(text))

    def bullet(text: str):
        pdf.set_font('Helvetica', '', 9.5)
        pdf.set_text_color(*C_BODY_FG)
        text = _latin1_safe(re.sub(r'\*\*(.+?)\*\*', r'\1', text))
        pdf.set_x(pdf.l_margin + 4)
        pdf.cell(4, 5.5, '-', new_x='RIGHT', new_y='TOP')
        pdf.multi_cell(usable_w - 8, 5.5, text.strip())

    def italic_footer(text: str):
        text = _latin1_safe(re.sub(r'\*(.+?)\*', r'\1', text))
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(usable_w, 5, text)
        pdf.set_text_color(*C_BODY_FG)

    lines = markdown.splitlines()
    for line in lines:
        stripped = line.strip()

        if not stripped:
            pdf.ln(2)
        elif stripped.startswith('# '):
            h1(stripped)
        elif stripped.startswith('## '):
            h2(stripped)
        elif stripped.startswith('### '):
            h3(stripped)
        elif stripped == '---':
            pdf.ln(1)
            rule()
        elif stripped.startswith('- ') or stripped.startswith('* '):
            bullet(stripped[2:])
        elif stripped.startswith('*') and stripped.endswith('*') and stripped.count('*') >= 2:
            italic_footer(stripped)
        else:
            stripped = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
            stripped = re.sub(r'\*(.+?)\*', r'\1', stripped)
            body(stripped)

    pdf.output(str(pdf_path))


# ── email via Apple Mail ───────────────────────────────────────────────────────

def send_mail(pdf_path: Path, recipient: str):
    abs_path = str(pdf_path.resolve())
    script = f'''tell application "Mail"
    activate
    set msg to make new outgoing message with properties {{subject:"Clinical Appraisal: {pdf_path.stem}", content:"Please find the clinical appraisal attached."}}
    tell msg
        make new to recipient at end of to recipients with properties {{address:"{recipient}"}}
        make new attachment at end of attachments with properties {{file name:POSIX file "{abs_path}"}}
        send
    end tell
end tell'''
    try:
        subprocess.check_call(['osascript', '-e', script])
    except subprocess.CalledProcessError as e:
        print(f'Warning: Email failed (osascript exit {e.returncode}). PDF is at {abs_path}', file=sys.stderr)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Critical appraisal of a clinical study PDF using GPT-5.4 via Codex OAuth.'
    )
    parser.add_argument('pdf',        type=Path,        help='Input study PDF')
    parser.add_argument('--email',    default=DEFAULT_EMAIL,  help='Recipient email (default: Readwise Reader)')
    parser.add_argument('--outdir',   type=Path, default=DEFAULT_OUTDIR, help='PDF output directory (default: ./output)')
    parser.add_argument('--model',    default=DEFAULT_MODEL,  help='Model (default: gpt-5.4)')
    parser.add_argument('--no-email', action='store_true',    help='Skip email delivery')
    args = parser.parse_args()

    # Normalise path
    args.pdf = sanitise_path(str(args.pdf))
    if not args.pdf.exists():
        print(f'Error: PDF not found: {args.pdf}', file=sys.stderr)
        sys.exit(1)

    # Output paths
    args.outdir.mkdir(parents=True, exist_ok=True)
    OBSIDIAN_JOURNAL.mkdir(parents=True, exist_ok=True)

    today_prefix = datetime.now().strftime('%Y-%m-%d')
    stem = re.sub(r'[^a-z0-9]+', '-', args.pdf.stem.lower()).strip('-') or 'clinical-appraisal'
    md_path  = OBSIDIAN_JOURNAL / f'{today_prefix}-{stem}-appraisal.md'
    pdf_path = args.outdir / f'{today_prefix}-{stem}-appraisal.pdf'

    # Extract text
    print(f'Extracting text from {args.pdf.name}…', flush=True)
    study_text = pdf_text(args.pdf)
    if len(study_text.strip()) < 200:
        print('Warning: Very little text extracted. The PDF may be scanned/image-only.', file=sys.stderr)

    # Appraise via codex
    markdown = appraise_with_codex(study_text, args.pdf.name, args.model)

    # Save markdown to Obsidian Journal
    md_path.write_text(markdown, encoding='utf-8')
    print(f'Markdown saved: {md_path}')

    # Render clinical PDF
    print('Rendering PDF…', flush=True)
    render_clinical_pdf(markdown, pdf_path)
    print(f'PDF saved:      {pdf_path}')

    # Email
    if not args.no_email:
        print(f'Sending to {args.email}…', flush=True)
        send_mail(pdf_path, args.email)
        print(f'Emailed to:     {args.email}')

    print(f'\nDone. Model: {args.model}')


if __name__ == '__main__':
    main()
