"""Look and feel for the Autonomous Data Analyst Agent (graph-paper worksheet theme)."""
import html

import streamlit as st

PALETTE = ["#3E6FB0", "#FFC83D", "#1E9E84", "#E2604D", "#8E8CD8"]

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Figtree:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root{
  --paper:#F2F7FB; --grid:#DCE7F2; --ink:#1D2B3F; --muted:#5F7088;
  --line:#C9D8E8; --edge:#9FB6CF; --blue:#3E6FB0;
  --sun:#FFC83D; --sea:#1E9E84; --sea-soft:#E4F6F1; --coral:#E2604D; --coral-soft:#FFEFEA;
  --font-ui:'Figtree',system-ui,-apple-system,'Segoe UI',sans-serif;
  --font-display:'Bricolage Grotesque','Figtree',system-ui,sans-serif;
  --font-code:'IBM Plex Mono',ui-monospace,Consolas,monospace;
}

/* page: faint graph paper */
[data-testid="stAppViewContainer"]{
  background-color:var(--paper);
  background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);
  background-size:28px 28px;
}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stAppDeployButton"],.stAppDeployButton{display:none;}
footer{visibility:hidden;}
.block-container{max-width:1080px;padding:2.4rem 1.5rem 4rem;}

/* text (icon fonts are left alone) */
.stApp,.stApp p,.stApp li,.stApp label,.stApp input,.stApp button,.stApp td,.stApp th{font-family:var(--font-ui);}

/* hero */
.hero{background:#fff;border:1px solid var(--line);border-radius:8px;padding:34px 36px 30px;margin-bottom:28px;box-shadow:6px 6px 0 var(--sun);}
.stApp .hero h1{font-family:var(--font-display);font-weight:800;font-size:clamp(2rem,4.6vw,3.2rem);line-height:1.05;letter-spacing:-.025em;margin:0 0 12px;padding:0;color:var(--ink);}
.stApp .hero p.lead{max-width:60ch;font-size:1.06rem;line-height:1.55;color:var(--muted);margin:0 0 24px;}
.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:6px;overflow:hidden;}
.flow-cell{background:var(--paper);padding:13px 16px;}
.flow-cell b{display:block;font-family:var(--font-display);font-size:1.05rem;color:var(--ink);margin-bottom:3px;}
.flow-cell span{display:block;font-size:.88rem;line-height:1.45;color:var(--muted);}

/* section headings */
.sec{font-family:var(--font-display);font-weight:700;font-size:1.35rem;letter-spacing:-.01em;color:var(--ink);margin:34px 0 12px;}

/* notes (empty and error states) */
.note{border:1.5px dashed var(--edge);border-radius:8px;padding:18px 20px;background:rgba(255,255,255,.75);color:var(--muted);font-size:.98rem;}
.note.bad{border:1.5px solid var(--coral);background:var(--coral-soft);color:#8A2E20;}

/* uploader and inputs */
[data-testid="stFileUploaderDropzone"]{background:#fff;border:2px dashed var(--edge);border-radius:8px;}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--ink);}
[data-testid="stTextInput"] [data-baseweb="input"]{background:#fff;border:1.5px solid var(--edge);border-radius:8px;}
[data-testid="stTextInput"] [data-baseweb="input"]:focus-within{border-color:var(--ink);box-shadow:3px 3px 0 var(--sun);}
[data-testid="stTextInput"] input{font-size:1.02rem;padding:.8rem .9rem;background:transparent;}

/* buttons: ink fill with a marigold offset shadow */
.stButton>button,[data-testid="stDownloadButton"]>button{
  font-weight:700;font-size:.98rem;color:#fff;background:var(--ink);border:1.5px solid var(--ink);
  border-radius:8px;padding:.6rem 1.3rem;box-shadow:3px 3px 0 var(--sun);
  transition:transform .12s ease,box-shadow .12s ease;
}
.stButton>button:hover{transform:translate(-1px,-1px);box-shadow:5px 5px 0 var(--sun);color:#fff;background:var(--ink);border-color:var(--ink);}
.stButton>button:active{transform:translate(2px,2px);box-shadow:1px 1px 0 var(--sun);}
.stButton>button p{color:#fff;}
[data-testid="stDownloadButton"]>button{background:#fff;color:var(--ink);}
[data-testid="stDownloadButton"]>button p{color:var(--ink);}
[data-testid="stDownloadButton"]>button:hover{transform:translate(-1px,-1px);box-shadow:5px 5px 0 var(--sun);background:#fff;color:var(--ink);border-color:var(--ink);}
.stButton>button:focus-visible,[data-testid="stDownloadButton"]>button:focus-visible{outline:3px solid var(--blue);outline-offset:2px;}

/* summary strip */
.ledger{display:flex;flex-wrap:wrap;background:#fff;border:1px solid var(--line);border-radius:8px;margin:18px 0 6px;}
.ledger>div{flex:1 1 140px;padding:12px 18px;border-right:1px solid var(--line);}
.ledger>div:last-child{border-right:0;}
.ledger .k{font-size:.82rem;font-weight:600;color:var(--muted);}
.ledger .v{font-family:var(--font-display);font-weight:700;font-size:1.5rem;line-height:1.25;color:var(--ink);}

/* tables */
.tbl-wrap{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px;max-height:420px;overflow-y:auto;}
.tbl-wrap table{border-collapse:collapse;width:100%;font-size:.9rem;}
.tbl-wrap th{position:sticky;top:0;background:#E8F0F9;color:var(--ink);text-align:left !important;padding:10px 14px;font-weight:700;border-bottom:1px solid var(--line);white-space:nowrap;}
.tbl-wrap td{padding:9px 14px;border-top:1px solid #E6EEF6;color:#2A3A52;}
.tbl-wrap tr:hover td{background:#F7FAFD;}

/* agent steps as spreadsheet rows */
.ws{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden;}
.ws-row{display:grid;grid-template-columns:46px minmax(0,1fr);border-top:1px solid var(--line);}
.ws-row:first-child{border-top:0;}
.ws-gutter{background:#E8F0F9;border-right:1px solid var(--line);text-align:center;padding:12px 0;font-size:.8rem;font-weight:600;font-variant-numeric:tabular-nums;color:var(--muted);}
.ws-body{padding:11px 16px;}
.ws-title{font-weight:700;font-size:.95rem;color:var(--ink);}
.ws-row.err{background:#FFF8F6;}
.ws-row.err .ws-gutter{background:var(--coral-soft);color:var(--coral);}
.ws-row.ok .ws-gutter{background:var(--sea-soft);color:var(--sea);}
.ws-body pre{margin:8px 0 2px;padding:10px 12px;background:#F7FAFD;border:1px solid var(--line);border-radius:6px;font-family:var(--font-code);font-size:.8rem;line-height:1.5;white-space:pre-wrap;word-break:break-word;color:#2A3A52;max-height:240px;overflow:auto;}

/* insights */
.st-key-insights{background:#fff;border:1px solid var(--line);border-left:6px solid var(--sun);border-radius:8px;padding:18px 26px;}
.st-key-insights p,.st-key-insights li{line-height:1.65;max-width:75ch;}

.foot{margin-top:46px;font-size:.85rem;color:var(--muted);}

@media (max-width:640px){
  .hero{padding:24px 20px 22px;box-shadow:4px 4px 0 var(--sun);}
  .ws-row{grid-template-columns:34px minmax(0,1fr);}
}
@media (prefers-reduced-motion:reduce){*{transition:none !important;}}
</style>"""


def _safe(text) -> str:
    """Escape text for HTML and keep markdown from splitting the block on blank lines."""
    t = html.escape(str(text)).replace("$", "&#36;")
    return "\n".join(line if line.strip() else "\u200b" for line in t.splitlines())


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def hero():
    cells = [
        ("Ask", "Type a business question in plain English."),
        ("Plan", "Gemini decides whether SQL or Python fits best."),
        ("Run", "Safety checks first. If the code fails, the agent reads the error and tries again."),
        ("Explain", "You get a table, a chart and a short written summary."),
    ]
    flow = "".join(f'<div class="flow-cell"><b>{a}</b><span>{b}</span></div>' for a, b in cells)
    st.markdown(
        '<div class="hero"><h1>Autonomous Data Analyst Agent</h1>'
        '<p class="lead">Upload a spreadsheet and ask what you want to know. '
        'The agent writes the code, fixes its own mistakes, and shows its work.</p>'
        f'<div class="flow">{flow}</div></div>',
        unsafe_allow_html=True,
    )


def section(title):
    st.markdown(f'<div class="sec">{_safe(title)}</div>', unsafe_allow_html=True)


def note(text, bad=False):
    st.markdown(f'<div class="note{" bad" if bad else ""}">{_safe(text)}</div>', unsafe_allow_html=True)


def ledger(items):
    cells = "".join(f'<div><div class="k">{_safe(k)}</div><div class="v">{_safe(v)}</div></div>' for k, v in items)
    st.markdown(f'<div class="ledger">{cells}</div>', unsafe_allow_html=True)


def table(d, rows=200):
    # Plain HTML table: avoids pyarrow, which some Windows setups block
    t = d.head(rows).to_html(index=False, border=0)
    st.markdown(f'<div class="tbl-wrap">{t}</div>', unsafe_allow_html=True)


def worksheet(steps):
    rows = []
    for i, (title, detail) in enumerate(steps, 1):
        if title.startswith(("Error", "Stopped")):
            cls = "err"
        elif title.startswith(("3.", "4.")):
            cls = "ok"
        else:
            cls = ""
        rows.append(
            f'<div class="ws-row {cls}"><div class="ws-gutter">{i}</div>'
            f'<div class="ws-body"><div class="ws-title">{_safe(title)}</div><pre>{_safe(detail)}</pre></div></div>'
        )
    st.markdown(f'<div class="ws">{"".join(rows)}</div>', unsafe_allow_html=True)


def style_fig(fig):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        colorway=PALETTE,
        font=dict(family="Figtree, system-ui, sans-serif", color="#1D2B3F"),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig.update_xaxes(showgrid=False, linecolor="#C9D8E8")
    fig.update_yaxes(gridcolor="#E6EEF6")
    return fig


def footer():
    st.markdown('<div class="foot">Built by Nikita Adhau with Python, LangGraph and Gemini.</div>', unsafe_allow_html=True)