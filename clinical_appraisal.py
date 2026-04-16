#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib.request
from pathlib import Path
from datetime import datetime

DEFAULT_FRAMEWORK = Path('/Users/home/.openclaw/media/inbound/jcdr-11-JE01---5f8db21a-9210-4656-8682-17074fb9e54d.pdf')
DEFAULT_RENDERER = Path('/Users/home/.openclaw/workspace/md_to_presentation_pdf.py')
DEFAULT_EMAIL = 'amornj@library.readwise.io'
DEFAULT_MODEL = 'gpt-5.4'
DEFAULT_CODEX_AUTH = Path.home() / '.codex' / 'auth.json'


def run(cmd):
    return subprocess.check_output(cmd, text=True)


def pdf_text(path: Path) -> str:
    return run(['pdftotext', str(path), '-'])


def first_match(pattern, text, flags=0, default=''):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else default


def clean_line(line: str) -> str:
    return re.sub(r'\s+', ' ', line).strip(' -:\t')


def infer_title(text: str, fallback: str) -> str:
    lines = [clean_line(x) for x in text.splitlines()]
    lines = [x for x in lines if x and len(x) < 180]
    bad = {'abstract', 'background', 'methods', 'results', 'conclusions', 'introduction'}
    for i, line in enumerate(lines[:40]):
        low = line.lower()
        if low in bad:
            continue
        if 8 < len(line) < 140 and not re.match(r'^(doi|vol\.|journal|review article)', low):
            if i + 1 < len(lines) and lines[i + 1].lower() not in bad and len(lines[i + 1]) < 120:
                candidate = f"{line} {lines[i+1]}"
                if len(candidate) < 160:
                    return candidate
            return line
    return fallback


def infer_doi(text: str) -> str:
    m = re.search(r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', text, re.I)
    return m.group(1) if m else 'DOI not found'


def infer_journal_year(text: str) -> tuple[str, str]:
    journal = first_match(r'^(.*?)\n', text, re.M, 'Unknown journal')
    year = first_match(r'\b(19|20)\d{2}\b', text, 0, '')
    return clean_line(journal), year


def section(text: str, start: str, end_options: list[str]) -> str:
    idx = text.lower().find(start.lower())
    if idx == -1:
        return ''
    tail = text[idx + len(start):]
    end_positions = [tail.lower().find(opt.lower()) for opt in end_options if tail.lower().find(opt.lower()) != -1]
    end = min(end_positions) if end_positions else len(tail)
    return tail[:end].strip()


def extract_bullets(blob: str, limit: int = 6) -> list[str]:
    items = []
    for raw in blob.splitlines():
        line = clean_line(raw)
        if len(line) < 25:
            continue
        if re.match(r'^(background|methods|results|conclusions?|introduction)$', line.lower()):
            continue
        items.append(line)
    uniq = []
    for item in items:
        if item not in uniq:
            uniq.append(item)
    return uniq[:limit]


def framework_points(framework_text: str) -> dict:
    return {
        'standard_questions': [
            'What is the research question?',
            'What is the study type (design)?',
            'Selection issues.',
            'What are the outcome factors and how are they measured?',
            'What are the study factors and how are they measured?',
            'What important potential confounders are considered?',
            'What is the statistical method used in the study?',
            'Statistical results.',
            'What conclusions did the authors reach?',
            'Are ethical issues considered?'
        ],
        'rct_focus': [
            'Allocation and randomization',
            'Blinding',
            'Follow-up and intention-to-treat',
            'Data collection and bias control',
            'Power calculation',
            'Presentation clarity',
            'Applicability to local population'
        ],
        'sr_focus': [
            'Search strategy breadth',
            'Quality control of included studies',
            'Homogeneity',
            'Precision of presentation',
            'Applicability'
        ]
    }


def load_oauth_access_token() -> str | None:
    try:
        data = json.loads(DEFAULT_CODEX_AUTH.read_text())
        return data.get('tokens', {}).get('access_token')
    except Exception:
        return None


def appraise_with_gpt(study_text: str, framework_text: str, pdf_name: str, model: str) -> str | None:
    api_key = os.getenv('OPENAI_API_KEY')
    oauth_token = load_oauth_access_token() if not api_key else None
    if not api_key and not oauth_token:
        return None

    prompt = f'''You are a clinician-statistician producing a structured critical appraisal in markdown.
Use the supplied framework as the appraisal skeleton.
Be concise, skeptical, clinically useful, and specific.
Do not invent numerical results that are not present in the paper.
At the end, include a section titled "# Presentation Slides" with 8 to 12 slide sections in markdown using headings like "## Slide 1: Title" and bullet points under each.

Framework text:
{framework_text[:18000]}

Study PDF filename: {pdf_name}
Study text:
{study_text[:70000]}
'''

    payload = {
        'model': model,
        'input': prompt
    }
    bearer = api_key or oauth_token
    req = urllib.request.Request(
        'https://api.openai.com/v1/responses',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {bearer}',
            'Content-Type': 'application/json'
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if 'output_text' in data and data['output_text']:
            return data['output_text']
        texts = []
        for item in data.get('output', []):
            for content in item.get('content', []):
                if content.get('type') in ('output_text', 'text'):
                    texts.append(content.get('text', ''))
        return '\n'.join(texts).strip() or None
    except Exception:
        return None


def appraise(study_text: str, framework_text: str, pdf_name: str) -> str:
    title = infer_title(study_text, Path(pdf_name).stem)
    doi = infer_doi(study_text)
    journal, year = infer_journal_year(study_text)
    abstract = section(study_text, 'Abstract', ['Introduction', 'Background', 'Methods']) or section(study_text, 'BACKGROUND', ['METHODS'])
    methods = section(study_text, 'Methods', ['Results', 'RESULTS', 'Discussion', 'DISCUSSION'])
    results = section(study_text, 'Results', ['Discussion', 'DISCUSSION', 'Conclusions', 'CONCLUSIONS'])
    discussion = section(study_text, 'Discussion', ['Conclusion', 'CONCLUSION', 'References'])

    abs_bullets = extract_bullets(abstract, 5)
    methods_bullets = extract_bullets(methods, 6)
    results_bullets = extract_bullets(results, 6)
    discussion_bullets = extract_bullets(discussion, 4)
    fw = framework_points(framework_text)

    study_type = 'Randomized trial' if re.search(r'\brandomi[sz]ed\b|placebo|double-blind|trial', study_text, re.I) else 'Systematic review / meta-analysis' if re.search(r'systematic review|meta-analysis|prisma', study_text, re.I) else 'Observational / other study'

    weak_points = []
    if not re.search(r'blinded|double-blind|single-blind', study_text, re.I):
        weak_points.append('Blinding is not clearly described in the extracted text, so measurement and treatment-behavior bias need checking.')
    if not re.search(r'intention to treat|intention-to-treat', study_text, re.I):
        weak_points.append('Intention-to-treat handling is not obvious from the extracted text and should be verified.')
    if not re.search(r'sample size|power', study_text, re.I):
        weak_points.append('Power calculation / sample-size justification is not clearly visible, which weakens confidence in negative or borderline findings.')
    if not re.search(r'confound', study_text, re.I) and study_type != 'Randomized trial':
        weak_points.append('Potential confounders are not explicitly discussed in the extracted text.')
    if not re.search(r'ethic|institutional review|IRB', study_text, re.I):
        weak_points.append('Ethics approval is not obvious in the extracted text and should be confirmed.')
    if not weak_points:
        weak_points.append('No single fatal flaw is obvious from text extraction alone, but protocol details should still be checked against the full paper.')

    strange_points = []
    if study_type == 'Randomized trial' and not re.search(r'control|placebo|comparator', study_text, re.I):
        strange_points.append('Comparator strategy is not clearly visible in the extracted text, which is a basic credibility check.')
    if re.search(r'composite', study_text, re.I):
        strange_points.append('Composite outcomes need inspection for whether the result is driven by the softest component.')
    if re.search(r'surrogate|biomarker', study_text, re.I):
        strange_points.append('Surrogate-heavy reasoning may overstate bedside value if hard clinical outcomes are limited.')
    if not strange_points:
        strange_points.append('The main thing to watch is whether reported strengths are methodological or mostly reporting quality.')

    clinical_take = []
    if study_type == 'Randomized trial':
        clinical_take.append('Use CONSORT-style checks before trusting a strong claim.')
        clinical_take.append('Prioritize randomization, blinding, attrition, endpoint construction, and whether effect size is clinically meaningful.')
    elif 'Systematic review' in study_type:
        clinical_take.append('Use PRISMA-style checks, especially search completeness and quality of included studies.')
        clinical_take.append('A meta-analysis is only as good as the underlying studies and heterogeneity handling.')
    else:
        clinical_take.append('Prioritize selection bias, confounding, follow-up quality, and overclaiming causality.')
        clinical_take.append('Observational effect sizes should be interpreted more cautiously than randomized estimates.')

    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    md = f'''# Clinical Appraisal: {title}

## Citation
- **Journal:** {journal}
- **Year:** {year or 'Unknown'}
- **DOI:** {doi}
- **Generated:** {today}

## Framework Used
This appraisal follows the framework from **Critical Appraisal of Clinical Research** (Al-Jundi and Sakka, JCDR 2017), centered on:
- research question
- study design
- selection issues
- outcome and study factors
- confounders
- statistical methods and results
- conclusions
- ethics

## Rapid Study Identification
- **Inferred study type:** {study_type}
- **Main title extracted:** {title}

## What the paper appears to be asking
'''
    for bullet in abs_bullets[:3] or ['Extracted abstract text was limited, so the exact research question should be confirmed manually.']:
        md += f'- {bullet}\n'

    md += '\n## Methods Snapshot\n'
    for bullet in methods_bullets[:6] or ['Methods section was not cleanly extracted.']:
        md += f'- {bullet}\n'

    md += '\n## Results Snapshot\n'
    for bullet in results_bullets[:6] or ['Results section was not cleanly extracted.']:
        md += f'- {bullet}\n'

    md += '\n## Strange or Weak Methodologic Points\n'
    for bullet in strange_points + weak_points:
        md += f'- {bullet}\n'

    md += '\n## Checklist-Driven Questions to Verify\n'
    for q in fw['standard_questions']:
        md += f'- {q}\n'

    md += '\n## Clinical Appraisal Lens\n'
    focus = fw['rct_focus'] if study_type == 'Randomized trial' else fw['sr_focus'] if 'Systematic review' in study_type else [
        'Selection bias', 'Confounding', 'Measurement validity', 'Follow-up completeness', 'Generalizability'
    ]
    for item in focus:
        md += f'- {item}\n'

    md += '\n## Discussion / Interpretation\n'
    for bullet in discussion_bullets[:4] or clinical_take:
        md += f'- {bullet}\n'
    for bullet in clinical_take:
        if bullet not in discussion_bullets:
            md += f'- {bullet}\n'

    md += '\n## Bottom Line\n'
    md += '- This output is a structured first-pass clinical appraisal built from PDF text extraction and the supplied framework.\n'
    md += '- Trust it most as a checklist-driven critique scaffold, then confirm key claims against the full article and tables.\n'
    md += '- If you want bedside-grade appraisal, review randomization, attrition, outcome definitions, absolute effect size, and external validity before acting on the study.\n'

    md += '\n---\n\n# Presentation Slides\n\n'
    slides = [
        ('Title', [title, f'{journal} {year}'.strip(), doi]),
        ('Framework', ['Research question', 'Study design', 'Selection issues', 'Outcomes and confounders', 'Statistics, conclusions, ethics']),
        ('Rapid Identification', [f'Inferred study type: {study_type}', f'Journal: {journal}', f'DOI: {doi}']),
        ('What the Paper Asks', abs_bullets[:5] or ['Confirm exact PICO manually from full text']),
        ('Methods Snapshot', methods_bullets[:6] or ['Methods extraction limited']),
        ('Results Snapshot', results_bullets[:6] or ['Results extraction limited']),
        ('Strange / Weak Points', (strange_points + weak_points)[:6]),
        ('Checklist Questions', fw['standard_questions'][:6]),
        ('Clinical Appraisal Lens', focus[:6]),
        ('Bottom Line', ['Use this as a first-pass critique scaffold', 'Verify trial mechanics in full text', 'Do not confuse statistical positivity with clinical importance'])
    ]
    for idx, (slide_title, bullets) in enumerate(slides, start=1):
        md += f'## Slide {idx}: {slide_title}\n'
        for b in bullets:
            md += f'- {b}\n'
        md += '\n'
    return md


def render_pdf(md_path: Path, pdf_path: Path, renderer: Path):
    subprocess.check_call([sys.executable, str(renderer), str(md_path), str(pdf_path)])


def send_mail(pdf_path: Path, recipient: str):
    script = f'''
tell application "Mail"
    activate
    set msg to make new outgoing message with properties {{subject:"Clinical appraisal PDF", content:"Attached clinical appraisal PDF."}}
    tell msg
        make new to recipient at end of to recipients with properties {{address:"{recipient}"}}
    end tell
    make new attachment at end of msg with properties {{file name:POSIX file "{pdf_path}"}}
    send msg
end tell
'''
    subprocess.check_call(['osascript', '-e', script])


def main():
    parser = argparse.ArgumentParser(description='Create a clinical-appraisal PDF from a study PDF and email it.')
    parser.add_argument('pdf', type=Path, help='Input study PDF')
    parser.add_argument('--framework', type=Path, default=DEFAULT_FRAMEWORK, help='Framework PDF for appraisal structure')
    parser.add_argument('--email', default=DEFAULT_EMAIL, help='Recipient email address')
    parser.add_argument('--outdir', type=Path, default=Path('output'), help='Output directory')
    parser.add_argument('--model', default=DEFAULT_MODEL, help='AI model for appraisal, default: gpt-5.4')
    parser.add_argument('--no-email', action='store_true', help='Skip email send')
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    study_text = pdf_text(args.pdf)
    framework_text = pdf_text(args.framework)

    stem = re.sub(r'[^a-z0-9]+', '-', args.pdf.stem.lower()).strip('-') or 'clinical-appraisal'
    md_path = args.outdir / f'{stem}-clinical-appraisal.md'
    pdf_path = args.outdir / f'{stem}-clinical-appraisal.pdf'

    markdown = appraise_with_gpt(study_text, framework_text, args.pdf.name, args.model)
    if not markdown:
        markdown = appraise(study_text, framework_text, args.pdf.name)
    md_path.write_text(markdown)
    render_pdf(md_path, pdf_path, DEFAULT_RENDERER)
    if not args.no_email:
        send_mail(pdf_path, args.email)

    print(f'Model: {args.model}')
    print(f'Markdown: {md_path}')
    print(f'PDF: {pdf_path}')
    if not args.no_email:
        print(f'Emailed to: {args.email}')


if __name__ == '__main__':
    main()
