# ============================================================
# app.py — Academic Research Co-Pilot
# UI design based on Stitch design system
# ============================================================
import streamlit as st
import pandas as pd
import json
from rag_pipeline import RAGPipeline
from utils.pdf_parser import extract_pdf_text, extract_paper_metadata

st.set_page_config(
    page_title="Academic Research Co-Pilot",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design tokens from Stitch design ──────────────────────────
# primary:           #001f41  (deep navy)
# primary-container: #0f3460
# tertiary:          #6e001e  (crimson)
# surface:           #fcf9f8  (warm white)
# surface-low:       #f6f3f2

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@700;800&display=swap');

/* ── Reset & base ── */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"], .main, .block-container {
    background-color: #fcf9f8 !important;
    font-family: 'Inter', sans-serif !important;
}
* { box-sizing: border-box; }

/* ── Hide Streamlit default chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
.stDeployButton { display: none; }

/* ── Sidebar — deep navy ── */
section[data-testid="stSidebar"] {
    background-color: #001f41 !important;
    border-right: 1px solid rgba(255,255,255,0.05);
}
section[data-testid="stSidebar"] * {
    color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
}
section[data-testid="stSidebar"] .stSlider * { color: #ffffff !important; }
section[data-testid="stSidebar"] .stFileUploader * { color: #cbd5e1 !important; }

/* ── Main area ── */
[data-testid="block-container"] {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── Tab bar ONLY (not content) ── */
[data-testid="stTabs"] > div:first-child,
[data-baseweb="tab-list"] {
    background: #001f41 !important;
    padding: 0 32px !important;
    border-bottom: 1px solid rgba(255,255,255,0.08) !important;
}
[data-testid="stTabs"] button[role="tab"] {
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #94a3b8 !important;
    padding: 14px 20px !important;
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
    border-radius: 0 !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #ffffff !important;
    border-bottom: 2px solid #6e001e !important;
    background: transparent !important;
}
/* Tab content — warm white, dark text */
[data-testid="stTabsContent"] {
    background: #fcf9f8 !important;
    padding: 40px 48px !important;
    min-height: 70vh !important;
    color: #001f41 !important;
}

/* ── Form submit button ── */
[data-testid="stForm"] button[kind="primaryFormSubmit"],
[data-testid="stForm"] button[type="submit"] {
    background: #001f41 !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    border-radius: 10px !important;
    padding: 10px 28px !important;
}
[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover,
[data-testid="stForm"] button[type="submit"]:hover {
    background: #0f3460 !important;
}

/* ── Textarea ── */
[data-testid="stForm"] textarea {
    background: #ffffff !important;
    border: 2px solid #e5e2e1 !important;
    border-radius: 14px !important;
    color: #001f41 !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
    padding: 18px 22px !important;
    font-family: 'Inter', sans-serif !important;
    resize: none !important;
    box-shadow: 0 1px 4px rgba(0,31,65,0.05) !important;
}
[data-testid="stForm"] textarea:focus {
    border-color: rgba(0,31,65,0.25) !important;
    box-shadow: 0 0 0 3px rgba(0,31,65,0.08) !important;
}

/* ── Main content text — scoped (don't override white-on-dark cards) ── */
[data-testid="stTabsContent"] > div > div > p,
[data-testid="stTabsContent"] > div > div > h1,
[data-testid="stTabsContent"] > div > div > h2,
[data-testid="stTabsContent"] > div > div > h3,
[data-testid="stTabsContent"] > div > div > ul,
[data-testid="stTabsContent"] > div > div > ol,
[data-testid="stTabsContent"] > div > div > li {
    color: #001f41 !important;
}

/* ── Streamlit metric ── */
[data-testid="stMetric"] label { color: #64748b !important; font-size: 11px !important; }
[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #001f41 !important; font-weight: 700 !important; }

/* ── User message bubble ── */
.user-bubble {
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    gap: 12px;
    margin: 24px 0;
}
.user-bubble-content {
    background: #dbeafe;
    border: 1px solid #bfdbfe;
    border-radius: 16px 0px 16px 16px;
    padding: 18px 22px;
    max-width: 720px;
    font-size: 14px;
    color: #001f41;
    line-height: 1.6;
}
.user-icon {
    width: 40px; height: 40px;
    background: #e5e2e1;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; flex-shrink: 0;
}

/* ── AI message bubble ── */
.ai-bubble {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin: 24px 0;
}
.ai-icon {
    width: 40px; height: 40px;
    background: #001f41;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; flex-shrink: 0;
    color: white;
}
.ai-bubble-content {
    background: #ffffff;
    border: 1px solid #ebe7e7;
    border-radius: 0px 16px 16px 16px;
    padding: 22px 26px;
    max-width: 760px;
    font-size: 14px;
    color: #001f41;
    line-height: 1.7;
    box-shadow: 0 1px 4px rgba(0,31,65,0.06);
}
.evidence-block {
    margin-top: 16px;
    padding: 12px 16px;
    background: #f6f3f2;
    border-left: 3px solid #0f3460;
    border-radius: 0 8px 8px 0;
    font-style: italic;
    font-size: 13px;
    color: #001f41;
}

/* ── Citation cards ── */
.citations-label {
    font-size: 11px;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 16px 0 10px 0;
}
.cit-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    max-width: 760px;
}
.cit-card {
    background: #ffffff;
    border-left: 4px solid #001f41;
    border-top: 1px solid #ebe7e7;
    border-right: 1px solid #ebe7e7;
    border-bottom: 1px solid #ebe7e7;
    border-radius: 0 8px 8px 0;
    padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(0,31,65,0.05);
    transition: box-shadow 0.2s;
}
.cit-card:hover { box-shadow: 0 4px 12px rgba(0,31,65,0.1); }
.cit-title { font-size: 12px; font-weight: 700; color: #001f41; margin-bottom: 4px; }
.cit-meta  { font-size: 10px; color: #64748b; margin-bottom: 10px; }
.cit-links { display: flex; gap: 16px; }
.cit-link  { font-size: 10px; font-weight: 700; color: #001f41; text-decoration: none; }
.cit-link:hover { text-decoration: underline; color: #6e001e; }
.badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    float: right;
    margin-top: -2px;
}
.badge-arXiv    { background:#fef2f2; color:#dc2626; }
.badge-IEEE     { background:#eff6ff; color:#2563eb; }
.badge-Springer { background:#fff7ed; color:#ea580c; }
.badge-Semantic { background:#f0fdf4; color:#16a34a; }
.badge-PubMed   { background:#f0f9ff; color:#0369a1; }
.badge-CrossRef { background:#faf5ff; color:#7c3aed; }

/* ── Source rows in sidebar ── */
.src-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 12px; margin: 3px 0;
    background: rgba(255,255,255,0.05);
    border-radius: 6px;
    border-left-width: 4px; border-left-style: solid;
    font-size: 12px;
}
.src-count {
    font-size: 10px;
    background: rgba(255,255,255,0.1);
    color: #cbd5e1;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 700;
}

/* ── Metric cards in sidebar ── */
.metric-card {
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    padding: 12px;
    text-align: left;
}
.metric-num  { font-size: 26px; font-weight: 800; color: #ffffff; line-height: 1; }
.metric-label{ font-size: 10px; color: #94a3b8; margin-top: 2px; }

/* ── Paper mini card (Compare tab) ── */
.paper-mini {
    border: 1px solid #e5e2e1;
    border-radius: 8px;
    padding: 12px 14px;
    background: #ffffff;
    margin: 4px 0;
    font-size: 13px;
    color: #001f41;
}

/* ── Welcome screen ── */
.welcome-wrap {
    text-align: center;
    padding: 60px 20px;
}
.welcome-title {
    font-family: 'Manrope', sans-serif;
    font-size: 22px; font-weight: 800;
    color: #001f41; margin-bottom: 8px;
}
.welcome-sub {
    font-size: 13px; color: #64748b;
    line-height: 1.6; max-width: 480px; margin: 0 auto;
}

/* ── Query input area ── */
.query-title {
    font-family: 'Manrope', sans-serif;
    font-size: 26px; font-weight: 800;
    color: #001f41; margin-bottom: 4px;
}
.query-sub {
    font-size: 13px; color: #64748b; margin-bottom: 16px;
}

/* ── Comparison table ── */
.stDataFrame th {
    background: #001f41 !important;
    color: #ffffff !important;
    font-size: 12px !important;
    font-weight: 700 !important;
}
.stDataFrame td {
    color: #001f41 !important;
    font-size: 12px !important;
    background: #ffffff !important;
}

/* ── Live lab indicator ── */
.live-lab {
    display: inline-flex; align-items: center; gap: 8px;
    background: #ffffff; border: 1px solid rgba(0,31,65,0.1);
    border-radius: 999px; padding: 6px 16px;
    font-size: 10px; font-weight: 700; color: #001f41;
    letter-spacing: 0.08em; text-transform: uppercase;
    box-shadow: 0 4px 20px rgba(0,31,65,0.12);
}
.pulse-dot {
    width: 8px; height: 8px;
    border-radius: 50%; background: #22c55e;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0%,100% { opacity:1; transform:scale(1); }
    50%      { opacity:0.5; transform:scale(1.3); }
}

/* ── Expander style ── */
[data-testid="stExpander"] {
    background: transparent !important;
    border: none !important;
}

/* ── Sidebar file uploader — dashed card look ── */
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    border: 2px dashed rgba(255,255,255,0.18) !important;
    border-radius: 10px !important;
    padding: 4px 8px 8px 8px !important;
    background: rgba(255,255,255,0.03) !important;
    margin-bottom: 10px !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
    border: none !important;
    padding: 8px 4px !important;
    text-align: center !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] {
    color: #94a3b8 !important;
    font-size: 11px !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] svg {
    color: #94a3b8 !important;
    width: 20px !important; height: 20px !important;
}
section[data-testid="stSidebar"] .stFileUploader label { display: none !important; }

/* ── Sidebar buttons ── */
section[data-testid="stSidebar"] .stButton > button {
    background: #6e001e !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    border-radius: 6px !important;
    width: 100% !important;
    padding: 10px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #8b0026 !important;
}

/* ── Sidebar slider ── */
section[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] div[role="slider"] {
    background: #6e001e !important;
}
section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMin"],
section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMax"] {
    color: #64748b !important;
    font-size: 10px !important;
}

/* ── Sidebar text inputs ── */
section[data-testid="stSidebar"] .stTextInput input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #ffffff !important;
    border-radius: 6px !important;
    font-size: 12px !important;
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════
def init_session():
    defaults = {
        "sessions":       [[]],
        "active_session": 0,
        "llm_histories":  [[]],
        "fetch_counts":   {},
        "last_papers":    [],
        "compare_result": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

def current_chat():
    return st.session_state.sessions[st.session_state.active_session]

def current_llm():
    return st.session_state.llm_histories[st.session_state.active_session]

def add_msg(role, content, mtype="chat", cited=None):
    current_chat().append({"role": role, "content": content,
                            "type": mtype, "cited_papers": cited or []})

def new_chat():
    st.session_state.sessions.append([])
    st.session_state.llm_histories.append([])
    st.session_state.active_session = len(st.session_state.sessions) - 1


# ════════════════════════════════════════════════════════════════
# PIPELINE
# ════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner="🔧 Initialising pipeline...")
def load_pipeline():
    return RAGPipeline()

try:
    pipeline = load_pipeline()
except Exception as e:
    st.error(f"❌ Pipeline failed: {e}")
    st.stop()


# ════════════════════════════════════════════════════════════════
# SIDEBAR  (mirrors Stitch Sidebar.tsx)
# ════════════════════════════════════════════════════════════════
with st.sidebar:

    # Logo
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:28px;padding-top:4px;">
        <div style="width:42px;height:42px;background:#6e001e;border-radius:10px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:22px;box-shadow:0 4px 12px rgba(110,0,30,0.4);">🎓</div>
        <div>
            <div style="font-size:14px;font-weight:800;color:#fff;
                        letter-spacing:0.04em;text-transform:uppercase;
                        font-family:'Manrope',sans-serif;line-height:1;">
                Research Co-Pilot
            </div>
            <div style="font-size:9px;color:#475569;font-weight:700;
                        letter-spacing:0.15em;text-transform:uppercase;margin-top:3px;">
                The Intellectual Ledger
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Papers Fetched ─────────────────────────────────────────
    st.markdown('<p style="font-size:10px;font-weight:700;color:#475569;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px;">Papers Fetched</p>', unsafe_allow_html=True)

    fetch_counts = st.session_state.fetch_counts
    total   = sum(fetch_counts.values()) if fetch_counts else 0
    indexed = len(st.session_state.last_papers)

    st.markdown(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:24px;">
        <div class="metric-card">
            <div class="metric-num">{total}</div>
            <div class="metric-label">Total</div>
        </div>
        <div class="metric-card" style="border-left:3px solid #6e001e;">
            <div class="metric-num">{indexed}</div>
            <div class="metric-label">Indexed</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Navigation ─────────────────────────────────────────────
    st.markdown('<p style="font-size:10px;font-weight:700;color:#475569;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:8px;">Navigate</p>', unsafe_allow_html=True)
    st.markdown("""
    <div style="margin-bottom:24px;">
        <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
                    color:#fff;font-weight:700;font-size:13px;
                    border-right:3px solid #6e001e;background:rgba(255,255,255,0.07);
                    border-radius:4px;margin-bottom:2px;">🔍 Research Query</div>
        <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
                    color:#64748b;font-size:13px;border-radius:4px;margin-bottom:2px;">
                    📊 Compare Papers</div>
        <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
                    color:#64748b;font-size:13px;border-radius:4px;">
                    📚 Fetched Papers</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sources ────────────────────────────────────────────────
    st.markdown('<p style="font-size:10px;font-weight:700;color:#475569;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:8px;">Sources</p>', unsafe_allow_html=True)

    SOURCE_STYLES = {
        "arXiv":            ("#ef4444", "🔴"),
        "IEEE":             ("#3b82f6", "🔵"),
        "Springer":         ("#f97316", "🟠"),
        "Semantic Scholar": ("#22c55e", "🟢"),
        "PubMed":           ("#64748b", "🔷"),
        "CrossRef":         ("#a855f7", "🟣"),
    }

    if fetch_counts:
        src_html = ""
        for source, count in fetch_counts.items():
            color, _ = SOURCE_STYLES.get(source, ("#999", "⚪"))
            src_html += f"""
            <div class="src-row" style="border-left-color:{color};">
                <span style="color:#fff;font-size:12px;">{source}</span>
                <span class="src-count">{str(count).zfill(2)}</span>
            </div>"""
        st.markdown(f'<div style="margin-bottom:24px;">{src_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<p style="font-size:11px;color:#475569;margin-bottom:24px;">Run a query to see live counts</p>', unsafe_allow_html=True)

    # ── Upload ─────────────────────────────────────────────────
    st.markdown("""
    <p style="font-size:10px;font-weight:700;color:#475569;letter-spacing:0.15em;
              text-transform:uppercase;margin-bottom:6px;">Upload Your Paper</p>
    """, unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Drag PDF here or click to browse", type=["pdf"],
                                     label_visibility="visible")
    if uploaded_file:
        file_bytes = uploaded_file.read()
        paper_text = extract_pdf_text(file_bytes)
        meta       = extract_paper_metadata(paper_text)
        if paper_text:
            st.success(f"✅ {uploaded_file.name}")
            paper_q = st.text_input("Question (optional)", key="paper_q",
                                    placeholder="What methodology was used?")
            if st.button("Review Paper", use_container_width=True,
                         help="AI review of uploaded paper"):
                with st.spinner("Analysing..."):
                    review = pipeline.review_paper(paper_text, paper_q)
                add_msg("assistant",
                        f"## 📄 Review: {meta.get('title', uploaded_file.name)}\n\n{review}",
                        "review")
                st.rerun()
        else:
            st.error("Could not extract text.")

    st.markdown("<hr style='border-color:rgba(255,255,255,0.06);margin:16px 0;'>", unsafe_allow_html=True)

    # ── Settings footer ────────────────────────────────────────
    top_k = st.slider("RAG Depth", 4, 20, 14,
                      help="Number of paper chunks retrieved per query")
    st.markdown(f'<div style="font-size:10px;color:#475569;text-align:right;margin-top:-12px;">Depth: {top_k}</div>', unsafe_allow_html=True)

    if st.button("🗑️  Clear Chat", use_container_width=True):
        st.session_state.sessions[st.session_state.active_session] = []
        st.session_state.llm_histories[st.session_state.active_session] = []
        st.rerun()


# ════════════════════════════════════════════════════════════════
# HEADER  (mirrors Stitch Header.tsx)
# ════════════════════════════════════════════════════════════════
sess_n = st.session_state.active_session + 1
sess_t = len(st.session_state.sessions)

# Header + New Chat button row
h1, h2 = st.columns([11, 1])
with h1:
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,#001f41 0%,#0f3460 100%);
                padding:16px 32px;display:flex;align-items:center;
                justify-content:space-between;margin-bottom:0;">
        <div style="display:flex;align-items:center;gap:32px;">
            <div>
                <div style="font-size:18px;font-weight:800;color:#fff;
                            font-family:'Manrope',sans-serif;letter-spacing:-0.01em;">
                    Academic Research Co-Pilot
                </div>
                <div style="font-size:11px;color:#94a3b8;margin-top:2px;">
                    RAG-powered &nbsp;·&nbsp; Citation-grounded &nbsp;·&nbsp; Hallucination-free
                </div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:20px;">
            <span style="background:#6e001e;color:#fff;font-size:10px;
                         font-weight:800;padding:3px 12px;border-radius:999px;
                         text-transform:uppercase;letter-spacing:0.06em;">RAG v1.0</span>
            <span style="font-size:10px;color:#475569;font-family:monospace;opacity:0.7;">
                SES: {sess_n:04d}-XP</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with h2:
    st.write("")
    if st.button("➕ New Chat", use_container_width=True, help="Start a new session"):
        new_chat()
        st.rerun()
    st.caption(f"{sess_n}/{sess_t}")


# ── Tabs ──────────────────────────────────────────────────────
tab_query, tab_compare, tab_papers = st.tabs([
    "🔍  QUERY",
    "📊  COMPARE",
    "📚  LIBRARY",
])


# ════════════════════════════════════════════════════════════════
# TAB 1 — RESEARCH QUERY
# ════════════════════════════════════════════════════════════════
with tab_query:

    # ── Query input section ───────────────────────────────────
    st.markdown("""
    <div style="font-family:'Manrope',sans-serif;font-size:26px;font-weight:800;
                color:#001f41;margin-bottom:4px;display:flex;align-items:center;gap:10px;">
        💬 Ask a Research Question
    </div>
    <div style="font-size:13px;color:#64748b;margin-bottom:16px;
                display:flex;align-items:center;gap:6px;">
        🛡️ Answers come only from fetched research papers — no hallucination
    </div>
    """, unsafe_allow_html=True)

    with st.form("qform", clear_on_submit=True):
        query  = st.text_area("", height=130, label_visibility="collapsed",
                              placeholder="E.g., What are the current limitations of Transformer models in processing long-context sequences within medical datasets?")
        submit = st.form_submit_button("🚀  Ask Co-Pilot", use_container_width=False, type="primary")

    st.markdown("<hr style='border-color:#ebe7e7;margin:28px 0 24px;'>", unsafe_allow_html=True)

    # ── Chat history ──────────────────────────────────────────
    chat = current_chat()
    if not chat:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-family:'Manrope',sans-serif;font-size:22px;font-weight:800;
                        color:#001f41;margin-bottom:8px;">Your Research Session Awaits</div>
            <div style="font-size:13px;color:#64748b;line-height:1.7;
                        max-width:480px;margin:0 auto;">
                Ask any academic question above. The system will fetch live papers from<br>
                <span style="color:#001f41;font-weight:600;">
                arXiv · IEEE · Springer · Semantic Scholar · PubMed · CrossRef
                </span><br>
                and generate a grounded, citation-backed answer.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in chat:
            role    = msg.get("role", "user")
            content = msg.get("content", "")
            mtype   = msg.get("type", "chat")
            cited   = msg.get("cited_papers", [])

            if role == "user":
                st.markdown(f"""
                <div style="display:flex;justify-content:flex-end;align-items:flex-start;
                            gap:12px;margin:24px 0;">
                    <div style="background:#dbeafe;border:1px solid #bfdbfe;
                                border-radius:16px 0 16px 16px;padding:18px 22px;
                                max-width:720px;font-size:14px;color:#001f41;line-height:1.6;">
                        {content}
                    </div>
                    <div style="width:40px;height:40px;background:#e5e2e1;border-radius:8px;
                                display:flex;align-items:center;justify-content:center;
                                font-size:18px;flex-shrink:0;">🧑‍🔬</div>
                </div>
                """, unsafe_allow_html=True)

            else:
                # Build citations HTML grid — all inline styles (no CSS classes)
                # so Streamlit's markdown renderer applies them reliably
                cit_html = ""
                if mtype == "rag" and cited:
                    BADGE_STYLES = {
                        "arXiv":            "background:#fef2f2;color:#dc2626;",
                        "IEEE":             "background:#eff6ff;color:#2563eb;",
                        "Springer":         "background:#fff7ed;color:#ea580c;",
                        "Semantic Scholar": "background:#f0fdf4;color:#16a34a;",
                        "PubMed":           "background:#f0f9ff;color:#0369a1;",
                        "CrossRef":         "background:#faf5ff;color:#7c3aed;",
                    }
                    cards = ""
                    for p in cited:
                        authors = p.get("authors", [])
                        auth    = (authors[0] if authors else "Unknown")
                        if len(authors) > 1: auth += " et al."
                        src        = p.get("source", "")
                        badge_css  = BADGE_STYLES.get(src, "background:#f1f5f9;color:#475569;")
                        title_safe = p.get("title", "N/A")[:72] + ("…" if len(p.get("title","")) > 72 else "")
                        doi_link   = (f'<a href="https://doi.org/{p["doi"]}" target="_blank" '
                                      f'style="font-size:10px;font-weight:700;color:#001f41;text-decoration:none;'
                                      f'display:inline-flex;align-items:center;gap:3px;">🔗 DOI</a>'
                                      if p.get("doi") else "")
                        url        = p.get("url") or "#"
                        cards += f"""
                        <div style="background:#ffffff;border-left:4px solid #001f41;
                                    border-top:1px solid #ebe7e7;border-right:1px solid #ebe7e7;
                                    border-bottom:1px solid #ebe7e7;border-radius:0 8px 8px 0;
                                    padding:14px 16px;box-shadow:0 1px 3px rgba(0,31,65,0.05);">
                            <div style="overflow:hidden;margin-bottom:4px;">
                                <span style="float:right;font-size:10px;font-weight:700;
                                             padding:2px 6px;border-radius:4px;{badge_css}">{src}</span>
                                <div style="font-size:12px;font-weight:700;color:#001f41;
                                            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                                    {title_safe}
                                </div>
                            </div>
                            <div style="font-size:10px;color:#64748b;margin-bottom:10px;">
                                {auth} · {p.get('year','N/A')} · 📊 {p.get('citation_count',0):,} citations
                            </div>
                            <div style="display:flex;gap:16px;">
                                <a href="{url}" target="_blank"
                                   style="font-size:10px;font-weight:700;color:#001f41;
                                          text-decoration:none;display:inline-flex;align-items:center;gap:3px;">
                                    ↗ View Paper
                                </a>
                                {doi_link}
                            </div>
                        </div>"""

                    cit_html = f"""
                    <div style="font-size:11px;font-weight:700;color:#94a3b8;
                                letter-spacing:0.12em;text-transform:uppercase;
                                margin:20px 0 10px 0;display:flex;align-items:center;gap:6px;">
                        📖 Grounded Citations ({len(cited)})
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:760px;">
                        {cards}
                    </div>"""

                st.markdown(f"""
                <div style="display:flex;align-items:flex-start;gap:12px;margin:24px 0;">
                    <div style="width:40px;height:40px;background:#001f41;border-radius:8px;
                                display:flex;align-items:center;justify-content:center;
                                font-size:18px;flex-shrink:0;">🤖</div>
                    <div style="flex:1;max-width:760px;">
                        <div style="background:#ffffff;border:1px solid #ebe7e7;
                                    border-radius:0 16px 16px 16px;padding:22px 26px;
                                    font-size:14px;color:#001f41;line-height:1.7;
                                    box-shadow:0 1px 4px rgba(0,31,65,0.06);">
                            {content.replace(chr(10),'<br>')}
                        </div>
                        {cit_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── Handle submit ─────────────────────────────────────────
    if submit and query.strip():
        add_msg("user", query)
        with st.spinner("🔍 Fetching relevant papers · ⟳ Indexing · 🤖 Generating answer..."):
            try:
                answer, chunks, cited_papers = pipeline.query(
                    user_query=query,
                    conversation_history=current_llm(),
                    top_k=top_k,
                )
                st.session_state.fetch_counts = pipeline.get_fetch_counts()
                st.session_state.last_papers  = pipeline.get_all_papers()
                current_llm().append({"role": "user",      "content": query})
                current_llm().append({"role": "assistant",  "content": answer})
                add_msg("assistant", answer, "rag", cited_papers)
            except Exception as e:
                add_msg("assistant", f"❌ Error: {e}\n\nCheck API keys in config.py.")
        st.rerun()
    elif submit:
        st.warning("Please enter a research query.")

    # ── Live Lab indicator ────────────────────────────────────
    st.markdown("""
    <div style="text-align:right;margin-top:32px;">
        <span class="live-lab">
            <span class="pulse-dot"></span>
            Live Lab Mode
        </span>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# TAB 2 — COMPARE PAPERS
# ════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown('<div style="font-family:\'Manrope\',sans-serif;font-size:26px;font-weight:800;color:#001f41;margin-bottom:4px;">📊 Compare Papers</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#64748b;margin-bottom:16px;">Select 2–5 papers from the current session to compare side-by-side.</div>', unsafe_allow_html=True)

    all_papers = pipeline.get_all_papers() if pipeline else []

    if not all_papers:
        st.info("🔍 Run a query in the **Research Query** tab first to fetch papers.")
    else:
        selected = st.multiselect("Select papers", [p["title"] for p in all_papers], max_selections=5)

        if selected:
            sel_papers = [p for p in all_papers if p["title"] in selected]
            cols = st.columns(min(len(sel_papers), 3))
            for i, p in enumerate(sel_papers):
                with cols[i % 3]:
                    auth = ", ".join(p.get("authors",[])[:2])
                    if len(p.get("authors",[])) > 2: auth += " et al."
                    st.markdown(f"""
                    <div style="border:1px solid #ebe7e7;border-radius:8px;
                                padding:12px 14px;background:#ffffff;margin:4px 0;">
                        <div style="color:#001f41;font-size:13px;font-weight:700;margin-bottom:4px;">
                            {p['title'][:70]}{'…' if len(p['title'])>70 else ''}
                        </div>
                        <div style="color:#64748b;font-size:11px;">
                            📅 {p.get('year','N/A')} &nbsp;|&nbsp;
                            🏛️ {p.get('source','')} &nbsp;|&nbsp;
                            📊 {p.get('citation_count',0):,} citations
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            if len(selected) >= 2:
                if st.button("⚡ Generate Comparison", type="primary", use_container_width=True):
                    with st.spinner("Comparing papers..."):
                        st.session_state.compare_result = pipeline.compare_papers(selected)

                if st.session_state.compare_result:
                    st.markdown("<hr style='border-color:#ebe7e7;margin:24px 0;'>",
                                unsafe_allow_html=True)
                    rows = [{
                        "Title":     p.get("title","")[:80],
                        "Authors":   ", ".join(p.get("authors",[])[:2]) + (" et al." if len(p.get("authors",[]))>2 else ""),
                        "Year":      p.get("year","N/A"),
                        "Source":    p.get("source","N/A"),
                        "Citations": p.get("citation_count", 0),
                    } for p in sel_papers]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    # Strip trailing code fences / stray HTML the LLM occasionally appends
                    import re as _re
                    clean_result = _re.sub(r'```[\w]*\n?[\s\S]*?```', '',
                                           st.session_state.compare_result).strip()

                    # Convert markdown to readable HTML in one shot
                    def _md_to_html(txt):
                        lines, out = txt.split('\n'), []
                        for ln in lines:
                            ln = ln.rstrip()
                            if ln.startswith('### '):
                                out.append(f'<h4 style="color:#001f41;font-family:Manrope,sans-serif;'
                                           f'font-weight:800;font-size:14px;margin:20px 0 6px;">'
                                           f'{ln[4:]}</h4>')
                            elif ln.startswith('## '):
                                out.append(f'<h3 style="color:#001f41;font-family:Manrope,sans-serif;'
                                           f'font-weight:800;font-size:16px;margin:22px 0 8px;">'
                                           f'{ln[3:]}</h3>')
                            elif ln.startswith('# '):
                                out.append(f'<h2 style="color:#001f41;font-family:Manrope,sans-serif;'
                                           f'font-weight:800;font-size:18px;margin:24px 0 10px;">'
                                           f'{ln[2:]}</h2>')
                            elif ln.startswith('- ') or ln.startswith('* '):
                                out.append(f'<li style="color:#001f41;font-size:14px;'
                                           f'line-height:1.8;margin-left:20px;">'
                                           f'{ln[2:]}</li>')
                            elif ln == '':
                                out.append('<br>')
                            else:
                                # bold **text**
                                ln = _re.sub(r'\*\*(.+?)\*\*',
                                             r'<strong style="color:#001f41;">\1</strong>', ln)
                                out.append(f'<p style="color:#001f41;font-size:14px;'
                                           f'line-height:1.8;margin:4px 0;">{ln}</p>')
                        return '\n'.join(out)

                    analysis_html = _md_to_html(clean_result)
                    st.markdown(f"""
                    <div style="background:#ffffff;border:1px solid #ebe7e7;border-radius:12px;
                                padding:24px 32px;box-shadow:0 1px 4px rgba(0,31,65,0.06);
                                margin-bottom:16px;">
                        <div style="font-family:'Manrope',sans-serif;font-size:16px;font-weight:800;
                                    color:#001f41;margin-bottom:16px;padding-bottom:12px;
                                    border-bottom:1px solid #ebe7e7;">
                            🔬 Detailed AI Analysis
                        </div>
                        {analysis_html}
                    </div>
                    """, unsafe_allow_html=True)

                    st.download_button("📥 Download Analysis", clean_result,
                                       "comparison.md", "text/markdown")
            else:
                st.warning("Select at least 2 papers to compare.")


# ════════════════════════════════════════════════════════════════
# TAB 3 — FETCHED PAPERS LIBRARY
# ════════════════════════════════════════════════════════════════
with tab_papers:
    st.markdown('<div style="font-family:\'Manrope\',sans-serif;font-size:26px;font-weight:800;color:#001f41;margin-bottom:4px;">📚 Fetched Papers Library</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#64748b;margin-bottom:16px;">All papers retrieved in the current session, ranked by citation count.</div>', unsafe_allow_html=True)

    all_papers = pipeline.get_all_papers() if pipeline else []

    if not all_papers:
        st.info("Run a query to populate the library.")
    else:
        total_cit = sum(p.get("citation_count", 0) for p in all_papers)
        max_cit   = max((p.get("citation_count", 0) for p in all_papers), default=0)
        sources   = list(set(p.get("source","") for p in all_papers))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📄 Papers",    len(all_papers))
        c2.metric("📊 Citations", f"{total_cit:,}")
        c3.metric("🏆 Top Cited", f"{max_cit:,}")
        c4.metric("🌐 Sources",   len(sources))

        st.markdown("<hr style='border-color:#ebe7e7;margin:20px 0;'>", unsafe_allow_html=True)

        fc1, fc2 = st.columns(2)
        with fc1:
            src_filter = st.multiselect("Filter by source", sources, default=sources)
        with fc2:
            min_cit = st.number_input("Min citations", min_value=0, value=0, step=10)

        filtered = [p for p in all_papers
                    if p.get("source","") in src_filter
                    and p.get("citation_count",0) >= min_cit]

        st.caption(f"Showing {len(filtered)} of {len(all_papers)} papers")

        if filtered:
            rows = [{
                "Title":     p.get("title","")[:80],
                "Authors":   ", ".join(p.get("authors",[])[:2]),
                "Year":      p.get("year","N/A"),
                "Source":    p.get("source","N/A"),
                "Citations": p.get("citation_count",0),
                "URL":       p.get("url",""),
            } for p in filtered]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.download_button("📥 Export JSON", json.dumps(filtered, indent=2),
                               "papers.json", "application/json")
