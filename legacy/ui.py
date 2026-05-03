from __future__ import annotations

import html
from typing import Any

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ll-ink: #0f172a;
            --ll-muted: #64748b;
            --ll-line: #e2e8f0;
            --ll-panel: #ffffff;
            --ll-bg: #f6f8fb;
            --ll-accent: #2563eb;
            --ll-accent-2: #0f766e;
            --ll-navy: #0b1220;
            --ll-soft-blue: #dbeafe;
            --ll-shadow: 0 18px 44px rgba(15, 23, 42, .08);
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(37,99,235,.08), transparent 34rem),
                linear-gradient(180deg, #f8fafc 0%, var(--ll-bg) 42%, #eef3f8 100%);
            color: var(--ll-ink);
        }
        .block-container { padding-top: 1.1rem; max-width: 1500px; padding-bottom: 3rem; }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border-right: 1px solid var(--ll-line);
        }
        section[data-testid="stSidebar"] > div { padding-top: 1.25rem; }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 { color: var(--ll-ink); }
        .hero-card {
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(135deg, rgba(11,18,32,.98) 0%, rgba(15,35,68,.98) 50%, rgba(14,116,144,.92) 100%);
            color: white;
            padding: 34px 40px 32px 40px;
            border-radius: 18px;
            margin-bottom: 20px;
            box-shadow: 0 24px 60px rgba(15,23,42,.22);
            border: 1px solid rgba(255,255,255,.18);
        }
        .hero-card:after {
            content:"";
            position:absolute;
            width: 520px; height: 520px;
            right: -180px; top: -260px;
            background: radial-gradient(circle, rgba(219,234,254,.22), transparent 62%);
        }
        .hero-kicker { color: #bfdbfe; text-transform: uppercase; letter-spacing: .08em; font-weight: 780; font-size: .78rem; }
        .hero-card h1 { margin: 8px 0 6px 0; font-size: 3.25rem; letter-spacing: 0; line-height: 1.0; }
        .hero-subtitle { font-size: 1.24rem; color: #eff6ff; font-weight: 650; margin: 0 0 8px 0; }
        .hero-card p { max-width: 940px; font-size: 1.0rem; color: #cbd5e1; margin: 0; line-height: 1.55; }
        .hero-badges { display:flex; flex-wrap:wrap; gap: 8px; margin-top: 18px; }
        .pill {
            display:inline-block;
            padding: 7px 11px;
            border-radius: 999px;
            background: rgba(219,234,254,.14);
            color:#e0f2fe;
            border: 1px solid rgba(219,234,254,.22);
            font-weight:720;
            font-size: .82rem;
            line-height: 1;
        }
        .pill-light {
            background:#eff6ff;
            color:#1e3a8a;
            border: 1px solid #bfdbfe;
        }
        .section-card, .card, .chat-card, .memo-card {
            background: var(--ll-panel);
            border: 1px solid var(--ll-line);
            border-radius: 16px;
            padding: 20px 22px;
            box-shadow: var(--ll-shadow);
            margin-bottom: 16px;
        }
        .section-card-tight { padding: 16px 18px; }
        .metric-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid var(--ll-line);
            border-radius: 16px;
            padding: 16px 17px;
            min-height: 118px;
            box-shadow: 0 12px 30px rgba(15,23,42,.07);
        }
        .metric-label {
            color: var(--ll-muted);
            font-weight: 720;
            font-size: .80rem;
            text-transform: uppercase;
            letter-spacing: .045em;
            margin-bottom: 8px;
        }
        .metric-value {
            color: var(--ll-ink);
            font-weight: 820;
            font-size: 1.65rem;
            line-height: 1.12;
            margin-bottom: 8px;
        }
        .metric-help {
            color: var(--ll-muted);
            font-size: .86rem;
            line-height: 1.35;
        }
        .section-title {
            font-size: 1.23rem;
            font-weight: 820;
            color: var(--ll-ink);
            margin: 18px 0 5px 0;
        }
        .section-note {
            color: var(--ll-muted);
            font-size: .95rem;
            margin-bottom: 14px;
            line-height: 1.45;
        }
        .small-muted { color: var(--ll-muted); font-size: .88rem; line-height: 1.45; }
        .sidebar-title {
            color: #0f172a;
            font-size: .82rem;
            font-weight: 820;
            letter-spacing: .06em;
            text-transform: uppercase;
            margin: 18px 0 8px 0;
        }
        .data-status {
            border: 1px solid #bbf7d0;
            background: #f0fdf4;
            color: #166534;
            border-radius: 12px;
            padding: 10px 12px;
            font-size: .88rem;
            line-height: 1.35;
            margin-bottom: 6px;
        }
        .selected-loop-card {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-left: 5px solid var(--ll-accent);
            border-radius: 16px;
            padding: 17px 19px;
            margin-bottom: 16px;
            box-shadow: 0 12px 30px rgba(15,23,42,.07);
        }
        .selected-loop-card h3 { margin: 0 0 9px 0; font-size: 1.05rem; }
        .selected-grid { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 10px; }
        .selected-item { border-top: 1px solid #e2e8f0; padding-top: 9px; }
        .selected-item span { display:block; color: var(--ll-muted); font-size:.76rem; font-weight:720; text-transform:uppercase; letter-spacing:.04em; }
        .selected-item strong { display:block; margin-top:4px; color: var(--ll-ink); font-size:.98rem; overflow-wrap:anywhere; }
        .insight-list {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 14px 16px;
            color: #334155;
            line-height: 1.55;
        }
        .ask-panel {
            background:
                linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            border: 1px solid #bfdbfe;
            border-left: 6px solid var(--ll-accent);
            border-radius: 18px;
            padding: 22px 24px;
            box-shadow: 0 18px 42px rgba(37,99,235,.10);
            margin: 12px 0 18px 0;
        }
        .chat-card {
            border-left: 5px solid #93c5fd;
            background: #ffffff;
        }
        .memo-card {
            background: #ffffff;
            border-color: #cbd5e1;
            padding: 26px 30px;
        }
        .memo-card h3 { margin-top: 0; }
        div[data-testid="stChatMessage"] {
            background: transparent;
            border-radius: 16px;
        }
        div[data-testid="stMetric"] {
            background: var(--ll-panel);
            border: 1px solid var(--ll-line);
            border-radius: 14px;
            padding: 14px 16px;
            box-shadow: 0 8px 20px rgba(16,24,40,.05);
        }
        div[data-testid="stMetricLabel"] p { color: var(--ll-muted); font-weight: 650; }
        div[data-testid="stMetricValue"] { color: var(--ll-ink); }
        .stTabs [data-baseweb="tab-list"] {
            gap: 7px;
            border-bottom: 1px solid var(--ll-line);
            background: rgba(255,255,255,.72);
            padding: 8px 8px 0 8px;
            border-radius: 16px 16px 0 0;
        }
        .stTabs [data-baseweb="tab"] {
            background: #eef2f7;
            border-radius: 12px 12px 0 0;
            padding: 11px 15px;
            color: #334155;
            font-weight: 720;
        }
        .stTabs [aria-selected="true"] {
            background: #ffffff !important;
            color: var(--ll-navy) !important;
            border: 1px solid var(--ll-line);
            border-bottom: 1px solid #ffffff;
        }
        .stButton > button, div[data-testid="stFormSubmitButton"] button {
            border-radius: 12px;
            border: 1px solid #bfdbfe;
            background: linear-gradient(180deg, #ffffff 0%, #eff6ff 100%);
            color: #1e3a8a;
            font-weight: 740;
            min-height: 2.65rem;
        }
        .stButton > button:hover, div[data-testid="stFormSubmitButton"] button:hover {
            border-color: #2563eb;
            color: #1d4ed8;
            box-shadow: 0 8px 22px rgba(37,99,235,.12);
        }
        div[data-testid="stForm"] {
            border: 0;
            background: transparent;
            padding: 0;
        }
        .stTextInput input, .stTextArea textarea {
            border-radius: 12px;
            border-color: #cbd5e1;
            min-height: 2.9rem;
            font-size: .98rem;
            background: #ffffff;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            overflow: hidden;
            box-shadow: 0 8px 22px rgba(15,23,42,.04);
        }
        .stAlert {
            border-radius: 14px;
        }
        .verify-card {
            background: #f8fafc;
            border: 1px solid #d9e1ea;
            border-radius: 14px;
            padding: 13px 15px;
            margin: 8px 0 12px 0;
        }
        .verify-badge {
            display: inline-block;
            border-radius: 999px;
            padding: 5px 10px;
            font-size: .82rem;
            font-weight: 760;
            margin-bottom: 8px;
        }
        .verify-ok { background: #dcfce7; color: #14532d; border: 1px solid #86efac; }
        .verify-warn { background: #fffbeb; color: #92400e; border: 1px solid #fcd34d; }
        .verify-bad { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
        .verify-summary {
            color: #344054;
            font-size: .94rem;
            line-height: 1.45;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero() -> None:
    st.markdown(
        """
        <div class="hero-card">
          <div class="hero-kicker">Public-funding intelligence workspace</div>
          <h1>LoopLens</h1>
          <div class="hero-subtitle">AI-assisted review of circular charity funding patterns</div>
          <p>LoopLens helps human reviewers explore circular transfer patterns, inspect evidence, ask
          data-grounded questions, and generate neutral review memos from available records.</p>
          <div class="hero-badges">
            <span class="pill">Review-priority system, not an accusation system</span>
            <span class="pill">Data-grounded analytics</span>
            <span class="pill">Human review required</span>
            <span class="pill">LLM hallucination guard</span>
            <span class="pill">SQL and evidence transparency</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_start() -> None:
    st.markdown('<div class="card">', unsafe_allow_html=True)


def card_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def section(title: str, note: str | None = None) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="section-note">{note}</div>', unsafe_allow_html=True)


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else "n/a"))


def metric_card(label: str, value: Any, helper: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">{_esc(label)}</div>
          <div class="metric-value">{_esc(value)}</div>
          <div class="metric-help">{_esc(helper)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def selected_loop_card(loop_id: str, label: Any, score: Any, flow: Any, participants: int | None = None) -> None:
    part = "n/a" if participants is None else f"{participants:,}"
    st.markdown(
        f"""
        <div class="selected-loop-card">
          <span class="pill pill-light">Active review context</span>
          <h3>Selected loop: {_esc(loop_id)}</h3>
          <div class="small-muted">Used by Network View, Ask LoopLens, and Memo and Verification.</div>
          <div class="selected-grid">
            <div class="selected-item"><span>Review label</span><strong>{_esc(label)}</strong></div>
            <div class="selected-item"><span>Review score</span><strong>{_esc(score)}</strong></div>
            <div class="selected-item"><span>Circular flow</span><strong>{_esc(flow)}</strong></div>
            <div class="selected-item"><span>Participants</span><strong>{_esc(part)}</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_card(title: str, body: str, badge: str | None = None) -> None:
    badge_html = f'<span class="pill pill-light">{_esc(badge)}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="section-card section-card-tight">
          {badge_html}
          <div class="section-title" style="margin-top:8px;">{_esc(title)}</div>
          <div class="section-note" style="margin-bottom:0;">{_esc(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
