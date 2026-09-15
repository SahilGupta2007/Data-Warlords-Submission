"""AgentIQ visual tokens shared by the dashboard and AI chart renderer."""

from urllib.parse import quote
import textwrap

import plotly.graph_objects as go
import plotly.io as pio

PALETTE = ["#06b6d4", "#6366f1", "#f43f5e", "#f59e0b", "#10b981"]
RISK_SCALE = ["#10b981", "#f59e0b", "#f43f5e"]
TELEMETRY_SCALE = ["#151929", "#6366f1", "#06b6d4"]
PLOTLY_CONFIG = {"displaylogo": False, "scrollZoom": False, "responsive": True}


def apply_enterprise_theme(fig):
    """Style a figure in place without changing traces, hover content or axes ranges."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#eef0f8", family="Inter, sans-serif", size=12),
        colorway=PALETTE, margin=dict(l=10, r=10, t=30, b=10),
        hoverlabel=dict(bgcolor="#10141f", bordercolor="#1e2638",
                        font=dict(color="#eef0f8", family="Inter, sans-serif")),
        title=dict(font=dict(size=14), automargin=True, yref="paper", y=1, yanchor="bottom"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8b95b0")),
    )
    if fig.layout.title.text:
        fig.update_layout(title_text="<br>".join(textwrap.wrap(fig.layout.title.text, width=38)))
    # Preserve explicit showgrid=False and hidden axes on the network graph.
    fig.update_xaxes(gridcolor="#1e2638", griddash="dot", zerolinecolor="#1e2638",
                     tickfont=dict(color="#8b95b0"), automargin=True)
    fig.update_yaxes(gridcolor="#1e2638", griddash="dot", zerolinecolor="#1e2638",
                     tickfont=dict(color="#8b95b0"), automargin=True)
    # Keep long titles and legends apart when a chart narrows on mobile.
    if fig.layout.legend.orientation == "h":
        fig.update_layout(legend=dict(y=-0.3, yanchor="top", x=0, xanchor="left"))
    return fig


# Express resolves trace colors at construction, before the final styling helper.
_template = go.layout.Template(pio.templates["plotly_dark"])
_template.layout.update(colorway=PALETTE)
pio.templates["enterprise"] = _template

ENTERPRISE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {
    --canvas:#07090e; --surface:#10141f; --input:#151929;
    --text:#eef0f8; --muted:#8b95b0; --border:rgba(255,255,255,.08);
    --critical:#f43f5e; --warning:#f59e0b; --success:#10b981;
    --active:linear-gradient(135deg,#06b6d4 0%,#6366f1 100%);
    --aiq-font:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
}
html, body, .stApp, .stMarkdown, .stButton button, input, textarea, select {
    font-family:var(--aiq-font); color:var(--text);
}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {background:var(--canvas)}
[data-testid="stHeader"] {background:rgba(7,9,14,.96); border-bottom:1px solid var(--border)}
[data-testid="stMainBlockContainer"] {padding:1.5rem 2rem 3rem; max-width:1800px}
h1,h2,h3,h4 {font-family:var(--aiq-font); color:var(--text)!important; letter-spacing:-.025em}
h3 {font-size:1.16rem!important; font-weight:650!important}
[data-testid="stCaptionContainer"] {color:var(--muted)}
button, a, input, textarea, summary {scroll-margin-top:150px}
button:focus-visible, a:focus-visible, summary:focus-visible {
    outline:2px solid #6ee7d6!important; outline-offset:3px;
}
.dashboard-header {padding:18px 0 8px; margin-bottom:4px}
.dashboard-header h1 {font-size:clamp(1.4rem,2.2vw,2rem); font-weight:750; margin:0; padding:0 0 9px}
.dashboard-header p {color:var(--muted); font-size:13px; max-width:900px; line-height:1.7; margin:0}
.eyebrow {font-size:10px; font-weight:700; letter-spacing:.16em; color:#6ee7d6; margin-bottom:12px}
[data-testid="stSidebar"] {background:var(--surface); border-right:1px solid var(--border)}
[data-testid="stSidebarContent"] {padding:0 0 16px!important}
[data-testid="stSidebarUserContent"] {padding:16px!important}
.sidebar-brand {display:flex; gap:11px; align-items:center; margin:0 0 26px}
.brand-mark {display:grid; place-items:center; width:37px; height:37px; flex-shrink:0;
    background:var(--active); border-radius:11px; color:white; font-weight:800; font-size:18px}
.sidebar-brand strong {font-size:16px; letter-spacing:-.03em}
.sidebar-brand small {display:block; color:var(--muted); font-size:9px; letter-spacing:.12em; margin-top:4px}
.st-key-sidebar_navigation {gap:5px!important; margin-bottom:14px}
.st-key-sidebar_navigation button {display:grid!important; grid-template-columns:18px minmax(0,1fr);
    align-items:center; justify-content:initial!important; text-align:left!important;
    background:transparent!important; border:1px solid transparent!important; min-height:43px;
    padding:9px 10px!important; border-radius:9px!important; gap:10px; color:var(--muted)!important}
.st-key-sidebar_navigation button p {font-size:12px!important; white-space:normal!important;
    text-align:left!important; margin:0!important; width:100%}
.st-key-sidebar_navigation button > div {justify-content:flex-start!important; width:100%!important}
.st-key-sidebar_navigation button > div span,
.st-key-sidebar_navigation button [data-testid="stMarkdownContainer"] {width:100%!important}
.st-key-sidebar_navigation button::before {content:''; width:18px; height:18px; flex-shrink:0;
    background-position:center; background-size:contain; background-repeat:no-repeat}
.st-key-sidebar_navigation button:hover {background:var(--input)!important; color:var(--text)!important}
.st-key-sidebar_navigation button[kind="primary"] {
    background:linear-gradient(135deg,rgba(110,231,214,.13),rgba(129,140,248,.13))!important;
    border-color:rgba(129,140,248,.18)!important; color:var(--text)!important; position:relative}
.st-key-sidebar_navigation button[kind="primary"]::after {content:''; position:absolute; left:-1px;
    top:10px; bottom:10px; width:3px; border-radius:4px; background:linear-gradient(#6ee7d6,#818cf8)}
.st-key-architecture_stack {margin-top:24px; padding:16px; border:1px solid var(--border);
    border-radius:14px; background:var(--canvas)}
.stack-title {color:var(--muted); font-size:10px; letter-spacing:.1em; font-weight:700; margin-bottom:13px}
.stack-row {font-size:11px; color:var(--muted); margin:8px 0; line-height:1.6}
.stack-row strong {color:var(--text); font-weight:500}
.stack-footer {font-size:10px; color:#6ee7b7; border-top:1px solid var(--border); margin-top:12px; padding-top:12px}
.stMetric, [data-testid="stMetric"], .metric-card {
    background:var(--surface); border:1px solid #1e2638; border-radius:15px;
    padding:18px; box-shadow:0 4px 20px rgba(0,0,0,.35); min-height:132px;
    font-variant-numeric:tabular-nums;
}
.metric-card {position:relative; height:100%; overflow-wrap:anywhere}
.metric-card::before {content:''; position:absolute; top:18px; right:15px; width:5px; height:5px;
    background:#06b6d4; border-radius:50%; box-shadow:0 0 9px rgba(6,182,212,.3)}
.metric-card-critical::before {background:var(--critical); box-shadow:0 0 9px rgba(244,63,94,.3)}
.metric-card-warning::before {background:var(--warning)}
.metric-card-success::before {background:var(--success)}
.metric-title, [data-testid="stMetricLabel"] p {font-size:11px!important; color:var(--muted);
    text-transform:uppercase; letter-spacing:.06em; font-weight:600; white-space:normal!important}
.metric-title {padding-right:9px; margin-bottom:13px}
.metric-value, [data-testid="stMetricValue"] {font-size:clamp(28px,2.2vw,32px)!important;
    font-weight:750; line-height:1.2; color:var(--text); font-variant-numeric:tabular-nums}
[data-testid="stMetricValue"] > div {white-space:normal; overflow-wrap:anywhere}
.metric-delta {font-size:11px; color:var(--muted); margin-top:12px}
[data-testid="stMetricDelta"] {font-size:11px; margin-top:8px}
.risk-alert {display:flex; gap:12px; align-items:center; padding:14px 18px; margin:4px 0 18px;
    border:1px solid rgba(244,63,94,.24); border-radius:12px; background:rgba(244,63,94,.055);
    box-shadow:0 0 22px rgba(244,63,94,.035)}
.risk-alert-icon {font-size:18px}
.risk-alert-text {font-size:12px; line-height:1.7; color:#fda4af}
.stTabs [role="tablist"] {display:none!important}
.stTabs [role="tab"] {flex-shrink:0; border-radius:8px; padding:10px 13px;
    color:var(--muted); background:transparent; height:auto; min-height:44px}
.stTabs [role="tab"] p {font-size:12px}
.stTabs [aria-selected="true"] {color:var(--text)!important;
    background:linear-gradient(135deg,rgba(6,182,212,.12),rgba(99,102,241,.16))!important}
.stTabs [aria-selected="true"] {border-bottom:2px solid #6ee7d6!important}
.stTabs [role="tabpanel"] {padding-top:0}
.section-header {border-top:1px solid var(--border); padding:22px 0 4px; margin-top:20px}
.section-header h3 {margin:0; padding:0; font-size:1rem!important}
.stPlotlyChart {border:1px solid var(--border); border-radius:15px; overflow:hidden!important;
    overscroll-behavior:contain; touch-action:pan-y; background:var(--surface);
    box-shadow:0 4px 20px rgba(0,0,0,.15)}
.stDataFrame, [data-testid="stDataFrame"], .stTable {font-variant-numeric:tabular-nums;
    border-radius:12px; border:1px solid var(--border)}
.stElementContainer:has(> [data-testid="stDataFrame"]),
.stElementContainer:has(> [data-testid="stTable"]),
[data-testid="stFullScreenFrame"]:has(> [data-testid="stDataFrame"]) {
    max-width:100%; overflow-x:auto; -webkit-overflow-scrolling:touch;
}
.stButton button, .stDownloadButton button {background:var(--input); color:var(--text);
    border:1px solid var(--border); border-radius:9px; transition:all .2s ease; min-height:40px}
.stButton button:hover, .stDownloadButton button:hover {border-color:#6366f1; color:var(--text)}
.stButton button[kind="primary"] {background:var(--active); border-color:transparent}
.stTextInput [data-baseweb="input"], .stTextArea textarea, .stSelectbox [data-baseweb="select"] > div {
    background:var(--input); border-color:var(--border); color:var(--text); border-radius:9px}
[data-baseweb="popover"], [data-baseweb="menu"] {background:var(--surface); color:var(--text)}
.stSelectbox [role="group"], .stTextInput input, .stTextArea textarea {
    background:var(--input)!important; color:var(--text)!important; border:1px solid var(--border); border-radius:9px;
}
.stSelectbox input, .stSelectbox button {background:transparent!important; color:var(--text)!important}
[role="listbox"], [role="option"] {background:var(--surface); color:var(--text)}
[data-testid="stWidgetLabel"] p {color:var(--muted)!important}
.stExpander {border:1px solid var(--border); border-radius:12px; background:var(--surface)}
.stExpander details {border:0}
.stExpander summary {padding:14px 16px; color:var(--muted)}
.stExpander details[open] summary {color:#6ee7d6; border-bottom:1px solid var(--border)}
.stCode pre {background:var(--canvas)!important}
.quality-badge {display:inline-flex; padding:7px 12px; border-radius:20px; font-size:11px;
    font-weight:500; border:1px solid var(--border)}
.quality-excellent {color:#6ee7b7; background:rgba(16,185,129,.08)}
.quality-good {color:#a5b4fc; background:rgba(99,102,241,.1)}
.graph-legend {display:flex; flex-wrap:wrap; gap:18px; padding:13px 16px; border:1px solid var(--border);
    border-radius:12px; background:var(--surface); margin-bottom:14px}
.legend-item {display:flex; align-items:center; gap:7px; font-size:11px; color:var(--muted)}
.legend-dot {width:12px; height:12px; border-radius:50%; border:1px solid var(--text)}
.st-key-strategist_workspace {min-height:calc(100vh - 220px)}
.st-key-strategist_presets {gap:8px!important; margin:8px 0 18px}
.st-key-strategist_presets button {background:#151929; border:1px solid rgba(255,255,255,.1);
    border-radius:20px; transition:all .2s ease; min-height:40px; padding:8px 14px; text-align:left}
.st-key-strategist_presets button p {font-size:12px; white-space:normal!important}
.st-key-strategist_presets button:hover {background:rgba(99,102,241,.13); border-color:#818cf8}
.agent-selection {padding:12px 16px; border:1px solid var(--border); border-radius:12px;
    background:var(--surface); color:var(--muted); font-size:12px; margin:8px 0}
.agent-selection strong {color:#6ee7d6}
.st-key-executive_finding {background:var(--surface); border:1px solid var(--border);
    border-radius:15px; padding:24px; min-height:430px}
.st-key-executive_finding strong {color:#fcd34d; font-variant-numeric:tabular-nums}
.st-key-executive_finding li {font-size:14px; line-height:1.85; margin-bottom:18px}
.finding-badge {display:inline-flex; border:1px solid rgba(245,158,11,.25); border-radius:20px;
    background:rgba(245,158,11,.08); color:#fcd34d; padding:5px 10px; font-size:10px;
    letter-spacing:.07em; font-weight:600; margin-bottom:14px}
.strategist-empty {border:1px dashed #1e2638; border-radius:15px; padding:50px 28px;
    color:var(--muted); text-align:center; background:var(--surface)}
.strategist-empty strong {color:var(--text); font-size:18px; display:block; margin-bottom:10px}
@media (min-width:768px) {
    [data-testid="stSidebar"][aria-expanded="true"] {width:247px!important; min-width:247px!important; max-width:247px!important}
}
@media (min-width:768px) and (max-width:1199px) {
    .st-key-executive_kpis [data-testid="stHorizontalBlock"] {flex-wrap:wrap}
    .st-key-executive_kpis [data-testid="stColumn"] {flex:1 1 180px!important; min-width:180px!important}
    .topbar-brand span {display:block}
}
@media (max-width:767px) {
    [data-testid="stMainBlockContainer"] {padding:2rem 1rem 2rem}
    [data-testid="stSidebar"][aria-expanded="true"] {width:min(300px,85vw)!important; min-width:0!important; max-width:85vw!important}
    [data-testid="stSidebar"] button p {white-space:normal!important; overflow-wrap:anywhere}
    .dashboard-header {padding-top:14px}
    .dashboard-header p {font-size:12px}
    [data-testid="stHorizontalBlock"] {flex-wrap:wrap}
    [data-testid="stColumn"] {width:100%!important; flex:1 1 100%!important; min-width:0!important}
    .stDataFrame, [data-testid="stDataFrame"], [data-testid="stTable"] table {min-width:640px!important}
    .metric-card, [data-testid="stMetric"] {min-height:120px}
    .st-key-executive_finding {min-height:0; padding:20px}
    .stTabs [role="tab"] {padding:9px 11px}
}
@media (prefers-reduced-motion:reduce) {
    *, *::before, *::after {transition:none!important; animation:none!important; scroll-behavior:auto!important}
}
"""

# Small, local SVGs avoid an icon CDN and keep native buttons keyboard accessible.
_NAV_PATHS = (
    '<path d="M4 20V10m8 10V4m8 16v-7"/>',
    '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M3 10h18M7 15h3"/>',
    '<circle cx="12" cy="5" r="3"/><circle cx="5" cy="18" r="3"/><circle cx="19" cy="18" r="3"/><path d="m10 8-4 7m8-7 4 7M8 18h8"/>',
    '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/>',
    '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 3h6v4H9zM9 12h6m-6 4h6"/>',
)
for _index, _path in enumerate(_NAV_PATHS):
    _svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#8b95b0" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{_path}</svg>'
    ENTERPRISE_CSS += f'.st-key-nav_{_index} button::before {{background-image:url("data:image/svg+xml,{quote(_svg)}")}}\n'
ENTERPRISE_CSS += "</style>"
