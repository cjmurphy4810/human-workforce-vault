#!/usr/bin/env python3
"""
Script 11: Generate docs/index.html from live vault data and intelligence report.
Run after any pipeline update to regenerate the GitHub Pages site.

Usage:
    python3 scripts/11_generate_html.py [--dry-run]
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv

# cwd-first config pattern for test isolation
_cwd = Path.cwd()
ROOT = _cwd if (_cwd / "youtube" / "metadata").exists() else Path(__file__).resolve().parent.parent

# File paths
INDEX_JSON    = ROOT / "youtube" / "metadata" / "index.json"
GRAPH_JSON    = ROOT / "taxonomy" / "knowledge-graph.json"
TOPICS_JSON   = ROOT / "taxonomy" / "topics.json"
REPORT_MD     = ROOT / "exports" / "human-workforce-intelligence-report.md"
OUTPUT_HTML   = ROOT / "docs" / "index.html"

if not REPORT_MD.exists():
    print("ERROR: intelligence report not found. Run script 10 first.", file=sys.stderr)
    sys.exit(1)

# ── Gather live stats ──────────────────────────────────────────────────────────
index_data       = json.loads(INDEX_JSON.read_text()) if INDEX_JSON.exists() else []
video_count      = len(index_data)
transcript_count = sum(1 for v in index_data if v.get("transcript_file"))
summary_count    = sum(1 for v in index_data if v.get("summary_file"))

graph_data = json.loads(GRAPH_JSON.read_text()) if GRAPH_JSON.exists() else {}
node_count = len(graph_data.get("nodes", []))
edge_count = len(graph_data.get("edges", []))

topics_data  = json.loads(TOPICS_JSON.read_text()) if TOPICS_JSON.exists() else {}
topic_count  = len(topics_data)

generated_date = datetime.now().strftime("%B %d, %Y")

# ── Markdown helpers ───────────────────────────────────────────────────────────
def md_inline(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*\n]+?)\*',  r'<em>\1</em>',   text)
    return text.strip()

def section_split(md):
    """Return dict of {section_name: content} split on ## headers."""
    result, name, buf = {}, None, []
    for line in md.split('\n'):
        if line.startswith('## '):
            if name:
                result[name] = '\n'.join(buf).strip()
            name, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if name:
        result[name] = '\n'.join(buf).strip()
    return result

# ── Section parsers ────────────────────────────────────────────────────────────
def parse_themes(text):
    """Return [(title, description), ...]"""
    return re.findall(r'^\d+\.\s+\*\*(.+?)\*\*\s+[—-]\s+(.+)', text, re.MULTILINE)

def parse_findings(text):
    """Return [(title, body), ...]"""
    return re.findall(r'^-\s+\*\*(.+?)\*\*:\s+(.+)', text, re.MULTILINE)

def parse_trends(text):
    """Return [(numbered_title, body), ...]"""
    return re.findall(
        r'^\*\*(\d+\.\s+.+?)\*\*\n(.+?)(?=\n\n\*\*\d+\.|\Z)',
        text, re.MULTILINE | re.DOTALL
    )

def parse_predictions(text):
    """Return [(title, body), ...]"""
    return re.findall(
        r'^\*\*Prediction\s+\d+:\s+(.+?)\*\*\n(.+?)(?=\n\n\*\*Prediction|\Z)',
        text, re.MULTILINE | re.DOTALL
    )

def parse_books(text):
    """Return [(title, thesis, audience), ...]"""
    items = []
    for block in re.split(r'\n\n(?=\*\*Book)', text):
        m = re.search(
            r'\*\*Book\s+\d+:\s+"(.+?)"\*\*\n\*Thesis:\*\s*(.+?)\n\*Target Audience:\*\s*(.+)',
            block, re.DOTALL
        )
        if m:
            items.append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))
    return items

def parse_series(text):
    """Return [(title, concept, [episodes]), ...]"""
    items = []
    for block in re.split(r'\n\n(?=\*\*Series)', text):
        # Title ends at closing quote; subtitle + bold-close may follow before newline
        m = re.search(r'\*\*Series\s+\d+:\s+"(.+?)".*?\*\*\n\*Concept:\*\s*(.+)', block, re.DOTALL)
        if m:
            title   = m.group(1).strip()
            concept = m.group(2).strip().split('\n')[0].strip()
            eps     = re.findall(r'-\s+\*Episode\s+\d+:\*\s+"(.+?)"', block)
            items.append((title, concept, eps))
    return items

def parse_courses(text):
    """Return [(title, audience, [outcomes]), ...]"""
    items = []
    for block in re.split(r'\n\n(?=\*\*Course)', text):
        m = re.search(r'\*\*Course\s+\d+:\s+"(.+?)".*?\*\*\n\*Audience:\*\s*(.+)', block, re.DOTALL)
        if m:
            title    = m.group(1).strip()
            audience = m.group(2).strip().split('\n')[0].strip()
            outcomes = re.findall(r'^-\s+(.+)', block, re.MULTILINE)
            items.append((title, audience, outcomes[:5]))
    return items

def exec_summary_html(text):
    paras = [p.strip() for p in re.split(r'\n\n+', text) if p.strip()]
    out = []
    for p in paras:
        # skip hr lines
        if re.match(r'^-{3,}$', p):
            continue
        out.append(f'<p>{md_inline(p)}</p>')
    return '\n'.join(out)

# ── Parse report ───────────────────────────────────────────────────────────────
report_md = REPORT_MD.read_text()
sections  = section_split(report_md)

themes      = parse_themes(sections.get("Top 25 Themes", ""))
findings    = parse_findings(sections.get("Most Important Findings", ""))
trends      = parse_trends(sections.get("Emerging Trends", ""))
wf_preds    = parse_predictions(sections.get("Workforce Predictions", ""))
ai_preds    = parse_predictions(sections.get("AI Predictions", ""))
gov_preds   = parse_predictions(sections.get("Governance Predictions", ""))
books       = parse_books(sections.get("Recommended Future Books", ""))
series_list = parse_series(sections.get("Recommended Future Podcast Series", ""))
courses     = parse_courses(sections.get("Recommended Future Courses", ""))
exec_html   = exec_summary_html(sections.get("Executive Summary", ""))

print(f"Parsed: {len(themes)} themes, {len(findings)} findings, {len(trends)} trends")
print(f"        {len(wf_preds)+len(ai_preds)+len(gov_preds)} predictions, {len(books)} books, {len(series_list)} series, {len(courses)} courses")

# ── HTML builders ──────────────────────────────────────────────────────────────
def themes_html():
    cards = []
    for i, (title, desc) in enumerate(themes, 1):
        cards.append(f'''
        <div class="theme-card">
          <div class="theme-num">{i}</div>
          <div class="theme-content">
            <strong>{md_inline(title)}</strong>
            <p>{md_inline(desc)}</p>
          </div>
        </div>''')
    return '\n'.join(cards)

def findings_html():
    cards = []
    for title, body in findings:
        cards.append(f'''
        <div class="finding-card">
          <strong>{md_inline(title)}</strong>
          <p>{md_inline(body)}</p>
        </div>''')
    return '\n'.join(cards)

def trends_html():
    cards = []
    for i, (title, body) in enumerate(trends, 1):
        clean_title = re.sub(r'^\d+\.\s+', '', title)
        body_paras = [p.strip() for p in body.strip().split('\n') if p.strip()]
        cards.append(f'''
        <div class="trend-card">
          <h3>{i}. {md_inline(clean_title)}</h3>
          <p>{md_inline(' '.join(body_paras))}</p>
        </div>''')
    return '\n'.join(cards)

def pred_group_html(preds, num_offset=0):
    cards = []
    for i, (title, body) in enumerate(preds, 1 + num_offset):
        body_clean = ' '.join(p.strip() for p in body.strip().split('\n') if p.strip())
        cards.append(f'''
        <div class="prediction-card">
          <div class="pred-num">{i}</div>
          <div>
            <strong>{md_inline(title)}</strong>
            <p>{md_inline(body_clean)}</p>
          </div>
        </div>''')
    return '\n'.join(cards)

def books_html():
    cards = []
    for i, (title, thesis, audience) in enumerate(books, 1):
        cards.append(f'''
        <div class="rec-card">
          <div class="rec-label">Book {i}</div>
          <h3>&#8220;{title}&#8221;</h3>
          <p class="rec-thesis">{md_inline(thesis)}</p>
          <div class="rec-audience">{md_inline(audience)}</div>
        </div>''')
    return '\n'.join(cards)

def series_html():
    cards = []
    for i, (title, concept, eps) in enumerate(series_list, 1):
        ep_items = ''.join(f'<li>{ep}</li>' for ep in eps)
        ep_block = f'<ul class="episode-list">{ep_items}</ul>' if ep_items else ''
        cards.append(f'''
        <div class="rec-card">
          <div class="rec-label">Series {i}</div>
          <h3>&#8220;{title}&#8221;</h3>
          <p class="rec-thesis">{md_inline(concept)}</p>
          {ep_block}
        </div>''')
    return '\n'.join(cards)

def courses_html():
    cards = []
    for i, (title, audience, outcomes) in enumerate(courses, 1):
        out_items = ''.join(f'<li>{md_inline(o)}</li>' for o in outcomes)
        out_block = f'<ul class="episode-list">{out_items}</ul>' if out_items else ''
        cards.append(f'''
        <div class="rec-card">
          <div class="rec-label">Course {i}</div>
          <h3>&#8220;{title}&#8221;</h3>
          <p class="rec-thesis">{md_inline(audience)}</p>
          {out_block}
        </div>''')
    return '\n'.join(cards)

# ── HTML template ──────────────────────────────────────────────────────────────
GH_ACTIONS_URL = "https://github.com/cjmurphy4810/human-workforce-vault/actions/workflows/refresh-vault.yml"

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Human Workforce Intelligence Report</title>
<style>
  :root {{
    --brand:#0f172a;--accent:#3b82f6;--accent-light:#dbeafe;
    --gold:#f59e0b;--gold-light:#fef3c7;--text:#1e293b;--muted:#64748b;
    --border:#e2e8f0;--bg:#f8fafc;--white:#ffffff;--sidebar-w:260px;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Georgia',serif;background:var(--bg);color:var(--text);line-height:1.7}}
  header{{background:var(--brand);color:white;position:sticky;top:0;z-index:100;box-shadow:0 2px 12px rgba(0,0,0,.3)}}
  .header-inner{{max-width:1300px;margin:0 auto;padding:16px 32px;display:flex;align-items:center;gap:16px}}
  .logo{{font-family:'Arial',sans-serif;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--gold);white-space:nowrap}}
  .header-title{{font-size:15px;color:#94a3b8;border-left:1px solid #334155;padding-left:16px}}
  .header-actions{{margin-left:auto;display:flex;gap:10px;align-items:center}}
  .btn-refresh{{background:var(--gold);color:var(--brand);font-family:'Arial',sans-serif;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:6px 14px;border-radius:4px;text-decoration:none;white-space:nowrap;transition:opacity .15s}}
  .btn-refresh:hover{{opacity:.85}}
  .btn-guide{{background:transparent;color:#94a3b8;font-family:'Arial',sans-serif;font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;padding:6px 14px;border-radius:4px;text-decoration:none;border:1px solid #334155;white-space:nowrap;transition:all .15s}}
  .btn-guide:hover{{color:white;border-color:#94a3b8}}
  .layout{{display:flex;max-width:1300px;margin:0 auto;min-height:calc(100vh - 60px)}}
  nav{{width:var(--sidebar-w);flex-shrink:0;position:sticky;top:60px;height:calc(100vh - 60px);overflow-y:auto;padding:32px 0 32px 24px;border-right:1px solid var(--border);background:var(--white)}}
  nav h3{{font-family:'Arial',sans-serif;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:12px;padding-left:12px}}
  nav ul{{list-style:none}}
  nav ul li a{{display:block;font-family:'Arial',sans-serif;font-size:13px;color:var(--muted);text-decoration:none;padding:6px 12px;border-radius:6px 0 0 6px;transition:all .15s}}
  nav ul li a:hover,nav ul li a.active{{color:var(--accent);background:var(--accent-light);font-weight:600}}
  main{{flex:1;min-width:0;padding:48px 56px 80px}}
  .hero{{background:linear-gradient(135deg,var(--brand) 0%,#1e3a5f 100%);color:white;border-radius:12px;padding:48px 48px 40px;margin-bottom:48px}}
  .hero-eyebrow{{font-family:'Arial',sans-serif;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--gold);margin-bottom:16px}}
  .hero h1{{font-size:36px;font-weight:700;line-height:1.2;margin-bottom:16px}}
  .hero-meta{{font-family:'Arial',sans-serif;font-size:13px;color:#94a3b8;margin-bottom:8px}}
  .hero-updated{{font-family:'Arial',sans-serif;font-size:11px;color:#475569;margin-bottom:32px}}
  .stats{{display:flex;gap:32px;flex-wrap:wrap}}
  .stat-num{{display:block;font-size:32px;font-weight:700;color:var(--gold);line-height:1}}
  .stat-label{{font-family:'Arial',sans-serif;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;margin-top:4px}}
  section{{margin-bottom:64px;scroll-margin-top:80px}}
  .section-header{{display:flex;align-items:center;gap:12px;margin-bottom:24px;padding-bottom:12px;border-bottom:2px solid var(--border)}}
  .section-icon{{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}}
  .icon-blue{{background:var(--accent-light)}}.icon-gold{{background:var(--gold-light)}}.icon-green{{background:#dcfce7}}.icon-purple{{background:#f3e8ff}}.icon-red{{background:#fee2e2}}
  h2{{font-size:24px;font-weight:700;color:var(--brand)}}
  .exec-summary p{{font-size:16px;line-height:1.8;color:var(--text);margin-bottom:20px}}
  .exec-summary p:last-child{{margin-bottom:0}}
  .themes-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}}
  .theme-card{{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:18px 20px;display:flex;gap:14px;align-items:flex-start;transition:box-shadow .15s}}
  .theme-card:hover{{box-shadow:0 4px 16px rgba(0,0,0,.08)}}
  .theme-num{{font-family:'Arial',sans-serif;font-size:11px;font-weight:700;color:var(--accent);background:var(--accent-light);border-radius:6px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px}}
  .theme-content strong{{display:block;font-size:14px;font-weight:700;color:var(--brand);margin-bottom:4px}}
  .theme-content p{{font-size:13px;color:var(--muted);line-height:1.5}}
  .findings-list{{display:flex;flex-direction:column;gap:16px}}
  .finding-card{{background:var(--white);border:1px solid var(--border);border-left:4px solid var(--accent);border-radius:0 10px 10px 0;padding:20px 24px}}
  .finding-card strong{{display:block;font-size:15px;font-weight:700;color:var(--brand);margin-bottom:8px}}
  .finding-card p{{font-size:14px;line-height:1.7;color:var(--text)}}
  .trends-list{{display:flex;flex-direction:column;gap:20px}}
  .trend-card{{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:24px}}
  .trend-card h3{{font-size:16px;font-weight:700;color:var(--brand);margin-bottom:10px}}
  .trend-card p{{font-size:14px;line-height:1.7;color:var(--text)}}
  .predictions-group{{margin-bottom:40px}}
  .predictions-group h3{{font-family:'Arial',sans-serif;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid var(--border)}}
  .prediction-list{{display:flex;flex-direction:column;gap:12px}}
  .prediction-card{{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:20px 24px;display:flex;gap:16px}}
  .pred-num{{font-family:'Arial',sans-serif;font-size:20px;font-weight:700;color:var(--border);line-height:1;flex-shrink:0;width:28px;text-align:right;padding-top:2px}}
  .prediction-card strong{{display:block;font-size:14px;font-weight:700;color:var(--brand);margin-bottom:6px}}
  .prediction-card p{{font-size:13px;line-height:1.65;color:var(--text)}}
  .recs-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px}}
  .rec-card{{background:var(--white);border:1px solid var(--border);border-radius:12px;padding:24px;display:flex;flex-direction:column;gap:10px}}
  .rec-label{{font-family:'Arial',sans-serif;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--gold)}}
  .rec-card h3{{font-size:15px;font-weight:700;color:var(--brand);line-height:1.4}}
  .rec-thesis{{font-size:13px;color:var(--text);line-height:1.6}}
  .rec-audience{{font-size:12px;color:var(--muted);font-style:italic;margin-top:auto;padding-top:8px;border-top:1px solid var(--border)}}
  .episode-list{{margin-left:16px;margin-top:8px}}
  .episode-list li{{font-size:13px;color:var(--muted);margin-bottom:4px;font-style:italic}}
  footer{{background:var(--brand);color:#64748b;text-align:center;padding:24px;font-family:'Arial',sans-serif;font-size:12px}}
  footer a{{color:var(--gold);text-decoration:none}}
  @media(max-width:900px){{nav{{display:none}}main{{padding:24px 20px 60px}}.hero{{padding:32px 24px}}.hero h1{{font-size:26px}}.stats{{gap:20px}}}}
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div class="logo">The Human Workforce</div>
    <div class="header-title">Intelligence Report</div>
    <div class="header-actions">
      <a href="guide.html" class="btn-guide">Methodology Guide</a>
      <a href="{GH_ACTIONS_URL}" target="_blank" rel="noopener" class="btn-refresh">↻ Refresh Data</a>
    </div>
  </div>
</header>

<div class="layout">
  <nav>
    <h3>Contents</h3>
    <ul>
      <li><a href="#summary">Executive Summary</a></li>
      <li><a href="#themes">Top 25 Themes</a></li>
      <li><a href="#findings">Key Findings</a></li>
      <li><a href="#trends">Emerging Trends</a></li>
      <li><a href="#predictions">Predictions</a></li>
      <li><a href="#books">Future Books</a></li>
      <li><a href="#series">Podcast Series</a></li>
      <li><a href="#courses">Courses</a></li>
    </ul>
  </nav>
  <main>

    <div class="hero">
      <div class="hero-eyebrow">Intelligence Report · Full Content Vault Analysis</div>
      <h1>The Human Workforce<br>Intelligence Report</h1>
      <div class="hero-meta">Produced by Senior Research Analyst &nbsp;·&nbsp; 120,000+ characters analyzed</div>
      <div class="hero-updated">Last updated: {generated_date}</div>
      <div class="stats">
        <div class="stat"><span class="stat-num">{video_count}</span><span class="stat-label">Videos</span></div>
        <div class="stat"><span class="stat-num">{transcript_count}</span><span class="stat-label">Transcripts</span></div>
        <div class="stat"><span class="stat-num">{summary_count}</span><span class="stat-label">Summaries</span></div>
        <div class="stat"><span class="stat-num">{node_count:,}</span><span class="stat-label">Knowledge Nodes</span></div>
        <div class="stat"><span class="stat-num">{edge_count:,}</span><span class="stat-label">Graph Edges</span></div>
      </div>
    </div>

    <section id="summary">
      <div class="section-header">
        <div class="section-icon icon-blue">📋</div>
        <h2>Executive Summary</h2>
      </div>
      <div class="exec-summary">
        {exec_html}
      </div>
    </section>

    <section id="themes">
      <div class="section-header">
        <div class="section-icon icon-gold">🔑</div>
        <h2>Top {len(themes)} Themes</h2>
      </div>
      <div class="themes-grid">
        {themes_html()}
      </div>
    </section>

    <section id="findings">
      <div class="section-header">
        <div class="section-icon icon-red">⚡</div>
        <h2>Most Important Findings</h2>
      </div>
      <div class="findings-list">
        {findings_html()}
      </div>
    </section>

    <section id="trends">
      <div class="section-header">
        <div class="section-icon icon-green">📈</div>
        <h2>Emerging Trends</h2>
      </div>
      <div class="trends-list">
        {trends_html()}
      </div>
    </section>

    <section id="predictions">
      <div class="section-header">
        <div class="section-icon icon-purple">🔭</div>
        <h2>Predictions</h2>
      </div>
      <div class="predictions-group">
        <h3>Workforce Predictions</h3>
        <div class="prediction-list">{pred_group_html(wf_preds)}</div>
      </div>
      <div class="predictions-group">
        <h3>AI Predictions</h3>
        <div class="prediction-list">{pred_group_html(ai_preds)}</div>
      </div>
      <div class="predictions-group">
        <h3>Governance Predictions</h3>
        <div class="prediction-list">{pred_group_html(gov_preds)}</div>
      </div>
    </section>

    <section id="books">
      <div class="section-header">
        <div class="section-icon icon-gold">📚</div>
        <h2>Recommended Future Books</h2>
      </div>
      <div class="recs-grid">{books_html()}</div>
    </section>

    <section id="series">
      <div class="section-header">
        <div class="section-icon icon-blue">🎙️</div>
        <h2>Recommended Future Podcast Series</h2>
      </div>
      <div class="recs-grid">{series_html()}</div>
    </section>

    <section id="courses">
      <div class="section-header">
        <div class="section-icon icon-green">🎓</div>
        <h2>Recommended Future Courses</h2>
      </div>
      <div class="recs-grid">{courses_html()}</div>
    </section>

  </main>
</div>

<footer>
  <p>© 2026 <a href="https://www.youtube.com/@TheHumanWorkforce">The Human Workforce</a>
  &nbsp;·&nbsp; {video_count} videos analysed &nbsp;·&nbsp; Knowledge vault built with Claude AI
  &nbsp;·&nbsp; <a href="guide.html">Methodology Guide</a></p>
</footer>

<script>
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('nav a');
  window.addEventListener('scroll', () => {{
    let current = '';
    sections.forEach(s => {{ if (window.scrollY >= s.offsetTop - 100) current = s.id; }});
    navLinks.forEach(a => {{ a.classList.toggle('active', a.getAttribute('href') === '#' + current); }});
  }});
</script>
</body>
</html>"""

if DRY_RUN:
    print("DRY RUN — HTML not written.")
    print(f"Would write {len(HTML)} chars to {OUTPUT_HTML}")
else:
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(HTML)
    print(f"Written: {OUTPUT_HTML} ({len(HTML):,} chars)")
