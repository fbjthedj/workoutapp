import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from collections import defaultdict

# =============================================================
# Page config — mobile-first, distraction-free
# =============================================================
st.set_page_config(
    page_title="10K Speed – Strength Tracker (v4)",
    page_icon="🏃‍♂️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# =============================================================
# Constants & Files
# =============================================================
DATA_DIR = "."
WORKOUT_DATA_FILE = os.path.join(DATA_DIR, "workout_data.json")
WORKOUT_HISTORY_FILE = os.path.join(DATA_DIR, "workout_history.json")
SCHEMA_VERSION = 4  # v4: 3-day split, time caps, progression tips, deload toggle
SESSION_CAP_MIN = 30  # 30-minute sessions by design

# =============================================================
# Compatibility helpers (Streamlit versions)
# =============================================================

def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def ui_segmented(label, options, default, format_func=lambda x: x):
    """Use segmented control if available; otherwise horizontal radio."""
    if hasattr(st, "segmented_control"):
        return st.segmented_control(label, options=options, default=default, format_func=format_func)
    # Fallback to radio
    idx = options.index(default) if default in options else 0
    return st.radio(label, options, index=idx, format_func=format_func, horizontal=True)


def ui_container_border():
    return st.container()


def safe_toast(msg: str):
    if hasattr(st, "toast"):
        st.toast(msg)
    else:
        st.info(msg)


def get_query_param(key: str, default: str):
    if hasattr(st, "query_params"):
        try:
            val = st.query_params.get(key)
            return val if isinstance(val, str) else (val[0] if isinstance(val, list) and val else default)
        except Exception:
            return default
    elif hasattr(st, "experimental_get_query_params"):
        params = st.experimental_get_query_params()
        val = params.get(key)
        return val[0] if isinstance(val, list) and val else default
    return default


def set_query_param(key: str, value: str):
    if hasattr(st, "query_params"):
        try:
            st.query_params[key] = value
            return
        except Exception:
            pass
    if hasattr(st, "experimental_set_query_params"):
        try:
            st.experimental_set_query_params(**{key: value})
        except Exception:
            pass


def ui_toggle(label: str, value: bool):
    if hasattr(st, "toggle"):
        return st.toggle(label, value=value)
    return st.checkbox(label, value=value)

# =============================================================
# Global styles (light/dark + generous spacing)
# =============================================================
st.markdown(
    """
    <style>
      :root { --radius: 16px; --muted:#64748b; --space-1:6px; --space-2:10px; --space-3:16px; --space-4:24px; --card:#ffffff; --line:#E5E7EB; }

      .block-container { max-width: 880px !important; padding-top: var(--space-4) !important; padding-bottom: var(--space-4) !important; }
      .main-title { text-align:center; margin: var(--space-3) 0 var(--space-1) 0; line-height: 1.15; }
      .sub-title { text-align:center; color:var(--muted); margin-bottom: var(--space-3); }
      .tiny { color:var(--muted); font-size:12px; text-align:center; }
      .section-head { margin: var(--space-4) 0 var(--space-2); font-weight: 800; font-size: 1.05rem; letter-spacing: .2px; }

      .stTabs [role="tablist"] { gap: 8px; margin-bottom: var(--space-3); }
      .stTabs [role="tab"] { padding: 8px 12px; border-radius: 9999px; }

      .stButton>button { width: 100%; padding: 14px 16px; border-radius: var(--radius); font-weight: 700; margin: 6px 0; }

      .ex-card { background: var(--card); border:1.5px solid var(--line); border-radius: var(--radius); padding:18px 16px; margin-bottom: var(--space-3); box-shadow: 0 6px 20px rgba(0,0,0,0.05); }
      .ex-card.done { border-color:#10B981; background: #F0FDF4; box-shadow: 0 8px 24px rgba(16,185,129,0.12); }
      .badge { display:inline-block; padding:4px 10px; border-radius:9999px; font-size:12px; font-weight:700; margin-left:8px; }
      .warmup { background:#FFEAD5; color:#9A3412; }
      .strength { background:#FEE2E2; color:#991B1B; }
      .power { background:#EDE9FE; color:#6D28D9; }
      .core { background:#DBEAFE; color:#1E40AF; }
      .accessory { background:#F1F5F9; color:#0F172A; }
      .cooldown { background:#DCFCE7; color:#166534; }
      .tendon { background:#FFEDD5; color:#9A3412; }
      .pr { background:#FEF9C3; color:#854D0E; border:1px solid #FDE68A; }
      .timecap { background:#ECFCCB; color:#3F6212; }

      .sticky-wrap { margin-top: var(--space-4); }
      .sticky-bar { position: sticky; bottom: 10px; z-index: 50; background: rgba(255,255,255,0.96); backdrop-filter: blur(8px); border:1px solid var(--line); padding:12px; border-radius: var(--radius); display:flex; gap:12px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }

      @media (prefers-color-scheme: dark) {
        :root { --card:#0B1220; --line:#263041; }
        .ex-card { background:var(--card); border-color:var(--line); box-shadow: 0 8px 22px rgba(0,0,0,0.35); }
        .ex-card.done { background:#0f1b12; border-color:#14532d; box-shadow: 0 8px 24px rgba(16,185,129,0.18); }
        .sticky-bar { background: rgba(9,13,22,0.92); border-color:var(--line); box-shadow: 0 10px 30px rgba(0,0,0,0.45); }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================
# Templates — 3-day split for 10K performance, age-aware joints
# Principles: heavy(ish) but low volume, unilateral control, elastic power,
# calf-tendon stiffness, anti-rotation core. 30-minute cap.
# =============================================================
WORKOUT_TEMPLATES = {
    "monday": {
        "title": "A – Max Strength + Stiffness",
        "emoji": "🔵",
        "time_cap_min": 30,
        "blocks": [
            {"name": "Warm‑up (3–4 min)", "items": [
                {"name": "Jump rope – easy", "sets": 1, "reps": "2–3 min", "cat": "warmup", "note": "Soft, quick contacts."},
                {"name": "Hip openers + ankle rocks", "sets": 1, "reps": "6/side", "cat": "warmup", "note": "Grease range."},
            ]},
            {"name": "Strength A (Superset)", "items": [
                {"name": "Goblet squat (KB 24kg or DB 22.5kg)", "sets": 4, "reps": "5", "cat": "strength", "note": "RPE 8; 75–90s btw supersets."},
                {"name": "1‑arm DB row (22.5kg)", "sets": 4, "reps": "6/arm", "cat": "strength", "note": "Brace. Pull to hip."},
            ]},
            {"name": "Posterior Chain Power", "items": [
                {"name": "KB swings (24kg)", "sets": 3, "reps": "10", "cat": "power", "note": "Explode. 60–75s rest."},
            ]},
            {"name": "Tendon Stiffness", "items": [
                {"name": "Standing calf raise slow tempo", "sets": 3, "reps": "10 @ 2‑1‑2", "cat": "tendon", "note": "Heels to floor; pause top."},
            ]},
            {"name": "Core – Anti‑extension", "items": [
                {"name": "Ab wheel rollouts", "sets": 3, "reps": "6–10", "cat": "core", "note": "Ribs down, glutes on."},
            ]},
            {"name": "Cooldown", "items": [
                {"name": "Hip flexor + calves", "sets": 1, "reps": "45–60s/each", "cat": "cooldown", "note": "Easy breathe."}
            ]},
        ],
    },
    "wednesday": {
        "title": "B – Unilateral + Elastic",
        "emoji": "🟢",
        "time_cap_min": 30,
        "blocks": [
            {"name": "Warm‑up (3–4 min)", "items": [
                {"name": "Jump rope – high knees", "sets": 1, "reps": "90s", "cat": "warmup", "note": "Cues cadence."},
                {"name": "Walking lunges + leg swings", "sets": 1, "reps": "8/side", "cat": "warmup", "note": "Tall posture."},
            ]},
            {"name": "Strength B (Unilateral Superset)", "items": [
                {"name": "Bulgarian split squat (15kg)", "sets": 3, "reps": "6/leg", "cat": "strength", "note": "Bench for rear foot."},
                {"name": "Single‑leg RDL (12.5–15kg)", "sets": 3, "reps": "6/leg", "cat": "strength", "note": "Hips square; reach long."},
            ]},
            {"name": "Elastic Power", "items": [
                {"name": "Lateral bounds to stick", "sets": 3, "reps": "5/side", "cat": "power", "note": "Quiet landing, 2s hold."},
                {"name": "Ankle pogos", "sets": 2, "reps": "20s", "cat": "power", "note": "Stiff ankles; quick."},
            ]},
            {"name": "Carries + Anti‑rotation", "items": [
                {"name": "Suitcase carry (KB 24kg)", "sets": 2, "reps": "20–30m/side", "cat": "accessory", "note": "Don’t lean."},
                {"name": "Pallof press (band)", "sets": 2, "reps": "8–10/side", "cat": "core", "note": "Resist twist; slow."},
            ]},
            {"name": "Cooldown", "items": [
                {"name": "T‑spine + hips", "sets": 1, "reps": "45–60s/each", "cat": "cooldown", "note": "Downshift."}
            ]},
        ],
    },
    "friday": {
        "title": "C – Posterior Chain + Core",
        "emoji": "🟣",
        "time_cap_min": 30,
        "blocks": [
            {"name": "Warm‑up (3–4 min)", "items": [
                {"name": "Jump rope – easy", "sets": 1, "reps": "2 min", "cat": "warmup", "note": "Nose-breathe."},
                {"name": "Glute bridge + ham curls (band)", "sets": 1, "reps": "10 + 10", "cat": "warmup", "note": "Wake posterior chain."},
            ]},
            {"name": "Strength C (Superset)", "items": [
                {"name": "DB hip thrust (shoulders on bench, 22.5kg)", "sets": 4, "reps": "6–8", "cat": "strength", "note": "2s hold at top."},
                {"name": "DB overhead press (12.5–15kg)", "sets": 3, "reps": "6–8", "cat": "strength", "note": "Ribs down; no lean."},
            ]},
            {"name": "Calf‑Achilles", "items": [
                {"name": "Seated/leaning calf raises (DB on knee)", "sets": 3, "reps": "8–10 @ 2‑1‑2", "cat": "tendon", "note": "Slow eccentrics."},
            ]},
            {"name": "Core – Rotary", "items": [
                {"name": "Russian twists (light/mod)", "sets": 3, "reps": "10/side", "cat": "core", "note": "Rotate through ribs."},
                {"name": "Side plank", "sets": 2, "reps": "30–45s/side", "cat": "core", "note": "Long line."},
            ]},
            {"name": "Cooldown", "items": [
                {"name": "Hamstrings + hip flexor", "sets": 1, "reps": "45–60s/each", "cat": "cooldown", "note": "Easy breath."}
            ]},
        ],
    },
}

# =============================================================
# Cache helpers — load/save/migrate
# =============================================================
@st.cache_data(show_spinner=False)
def load_json(path, fallback):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return fallback
    return fallback


def save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        safe_toast(f"Could not save {os.path.basename(path)}: {e}")

# =============================================================
# Session State + Migration
# =============================================================
if "schema" not in st.session_state:
    st.session_state.schema = SCHEMA_VERSION
if "workout_data" not in st.session_state:
    st.session_state.workout_data = load_json(WORKOUT_DATA_FILE, {"_schema": SCHEMA_VERSION, "monday": {}, "wednesday": {}, "friday": {}})
if "history" not in st.session_state:
    st.session_state.history = load_json(WORKOUT_HISTORY_FILE, [])
if "selected_day" not in st.session_state:
    st.session_state.selected_day = get_query_param("day", "monday")
if "rest_timer_end" not in st.session_state:
    st.session_state.rest_timer_end = None
if "workout_started_at" not in st.session_state:
    st.session_state.workout_started_at = datetime.utcnow().isoformat()
if "auto_rest" not in st.session_state:
    st.session_state.auto_rest = 75  # seconds default to keep within 30min
if "confetti_on_save" not in st.session_state:
    st.session_state.confetti_on_save = True
if "deload_mode" not in st.session_state:
    st.session_state.deload_mode = False  # reduce sets/intensity when on

# Migration from older schemas

def migrate(data):
    if isinstance(data, dict) and data.get("_schema") == SCHEMA_VERSION:
        return data
    migrated = {"_schema": SCHEMA_VERSION, "monday": {}, "wednesday": {}, "friday": {}}
    # attempt to carry over any existing day data keys
    for day in ("monday", "wednesday", "friday", "tuesday", "thursday"):
        day_data = (data or {}).get(day, {})
        if not isinstance(day_data, dict):
            continue
        new_day = {}
        for ex_key, sets_map in day_data.items():
            new_day[ex_key] = {}
            for idx, val in sets_map.items():
                if isinstance(val, dict):
                    slot = {
                        "done": bool(val.get("done")),
                        "weight": val.get("weight"),
                        "reps": val.get("reps"),
                        "rpe": val.get("rpe"),
                    }
                else:
                    slot = {"done": bool(val), "weight": None, "reps": None, "rpe": None}
                new_day[ex_key][str(idx)] = slot
        if day in migrated:
            migrated[day] = new_day
    return migrated

st.session_state.workout_data = migrate(st.session_state.workout_data)

# =============================================================
# Utility functions
# =============================================================

def ex_key_from(block_i, item_i):
    return f"b{block_i}_i{item_i}"


def save_state():
    save_json(WORKOUT_DATA_FILE, st.session_state.workout_data)


def set_done(day, ex_key, set_index, done):
    st.session_state.workout_data.setdefault(day, {}).setdefault(ex_key, {})
    slot = st.session_state.workout_data[day][ex_key].get(str(set_index), {"done": False, "weight": None, "reps": None, "rpe": None})
    slot["done"] = done
    st.session_state.workout_data[day][ex_key][str(set_index)] = slot
    save_state()


def set_set_detail(day, ex_key, set_index, field, value):
    st.session_state.workout_data.setdefault(day, {}).setdefault(ex_key, {})
    slot = st.session_state.workout_data[day][ex_key].get(str(set_index), {"done": False, "weight": None, "reps": None, "rpe": None})
    slot[field] = value
    st.session_state.workout_data[day][ex_key][str(set_index)] = slot
    save_state()


def compute_progress(day):
    total_sets = 0
    done_sets = 0
    for b_i, block in enumerate(WORKOUT_TEMPLATES[day]["blocks"]):
        for i_i, it in enumerate(block["items"]):
            sets = it["sets"]
            # Apply deload: reduce sets by 1 (min 1)
            if st.session_state.deload_mode and sets > 1 and it["cat"] in ("strength", "tendon"):
                sets -= 1
            total_sets += sets
            k = ex_key_from(b_i, i_i)
            for s in range(sets):
                if st.session_state.workout_data.get(day, {}).get(k, {}).get(str(s), {}).get("done"):
                    done_sets += 1
    pct = (done_sets / total_sets * 100) if total_sets else 0
    return done_sets, total_sets, round(pct, 1)


def progress_ring(pct):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number={'suffix': '%', 'font': {'size': 36}},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'thickness': 0.28}, 'bgcolor': 'rgba(0,0,0,0)'}
    ))
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)


def start_rest(seconds: int):
    st.session_state.rest_timer_end = (datetime.utcnow() + timedelta(seconds=seconds)).isoformat()


def rest_widget():
    if st.session_state.rest_timer_end:
        end = datetime.fromisoformat(st.session_state.rest_timer_end)
        remaining = (end - datetime.utcnow()).total_seconds()
        if remaining <= 0:
            st.success("Rest done. Go! 💥")
            st.session_state.rest_timer_end = None
        else:
            st.info(f"Rest: {int(remaining)}s remaining…")
            safe_rerun()


def elapsed_widget():
    start = datetime.fromisoformat(st.session_state.workout_started_at)
    elapsed = (datetime.utcnow() - start).total_seconds()
    mm = int(elapsed // 60)
    ss = int(elapsed % 60)
    st.caption(f"⏱️ Elapsed: {mm:02d}:{ss:02d}")


def session_cap_widget():
    start = datetime.fromisoformat(st.session_state.workout_started_at)
    cap = start + timedelta(minutes=SESSION_CAP_MIN)
    remaining = (cap - datetime.utcnow()).total_seconds()
    if remaining <= 0:
        st.error("⏳ 30‑min cap reached — wrap with cooldown.")
    else:
        mm = int(remaining // 60)
        ss = int(remaining % 60)
        st.caption(f"🕒 Time left in session: {mm:02d}:{ss:02d}")

# ---- History helpers: last used load/RPE per exercise name ----

def build_last_values():
    last = {}
    for entry in sorted(st.session_state.history, key=lambda x: x.get("date", "")):
        data = entry.get("data", {})
        name_map = entry.get("meta", {}).get("name_map", {})
        for ex_key, sets_map in data.items():
            ex_name = name_map.get(ex_key)
            if not ex_name:
                continue
            w_vals = [v.get("weight") for v in sets_map.values() if isinstance(v, dict) and v.get("weight")]
            r_vals = [v.get("rpe") for v in sets_map.values() if isinstance(v, dict) and v.get("rpe")]
            if w_vals or r_vals:
                last[ex_name] = {
                    "weight": (w_vals[-1] if w_vals else None),
                    "rpe": (r_vals[-1] if r_vals else None),
                }
    return last

LAST_VALUES = build_last_values()

# ---- Personal Records (simple) — max weight per exercise name ----

def compute_prs():
    prs = defaultdict(float)
    for entry in st.session_state.history:
        data = entry.get("data", {})
        name_map = entry.get("meta", {}).get("name_map", {})
        for ex_key, sets_map in data.items():
            ex_name = name_map.get(ex_key)
            if not ex_name:
                continue
            for slot in sets_map.values():
                if isinstance(slot, dict) and slot.get("weight"):
                    prs[ex_name] = max(prs[ex_name], float(slot["weight"]))
    return prs

PRS = compute_prs()

# =============================================================
# Header
# =============================================================
st.markdown(
    """
<h1 class='main-title'>🏃‍♂️ 10K Speed – Strength (3×/week)</h1>
<p class='sub-title'>30‑minute sessions for a 47‑year‑old runner: max strength, elastic power, tendon stiffness, and core control.</p>
""",
    unsafe_allow_html=True,
)

date_label = datetime.now().strftime("%a, %b %d")
st.caption(f"📅 {date_label}")
elapsed_widget()
session_cap_widget()

# Coaching note
st.info("Pro tip: keep rests 60–90s on supersets; 75s default. Power work gets quality over fatigue. If short on time, skip last accessory block and hit cooldown.")

# =============================================================
# Tabs
# =============================================================
main_tab, analytics_tab, history_tab, settings_tab = st.tabs([
    "🏋️ Workout",
    "📊 Analytics",
    "📅 History",
    "⚙️ Settings",
])

# =============================================================
# Workout tab
# =============================================================
with main_tab:
    col_day, col_prog = st.columns([1, 1])
    with col_day:
        day = ui_segmented(
            "Day",
            options=["monday", "wednesday", "friday"],
            default=st.session_state.selected_day,
            format_func=lambda d: f"{WORKOUT_TEMPLATES[d]['emoji']} {d.title()}",
        )
        st.session_state.selected_day = day
        set_query_param("day", day)
    with col_prog:
        done, total, pct = compute_progress(day)
        progress_ring(pct)
        st.caption(f"{done}/{total} sets complete")

    # Render blocks
    name_map = {}  # ex_key -> exercise display name for metadata
    for b_i, block in enumerate(WORKOUT_TEMPLATES[day]["blocks"]):
        st.markdown(f"<div class='section-head'>{block['name']}</div>", unsafe_allow_html=True)
        for i_i, it in enumerate(block["items"]):
            k = ex_key_from(b_i, i_i)
            name_map[k] = it["name"]

            sets_cfg = it["sets"]
            # Apply deload mode: reduce sets by 1 for strength/tendon where possible
            sets_to_show = sets_cfg
            if st.session_state.deload_mode and sets_cfg > 1 and it["cat"] in ("strength", "tendon"):
                sets_to_show = sets_cfg - 1

            sets_map = st.session_state.workout_data.get(day, {}).get(k, {})
            done_sets = sum(1 for s in range(sets_to_show) if sets_map.get(str(s), {}).get("done"))
            is_done = done_sets == sets_to_show

            pr_weight = PRS.get(it["name"])
            pr_html = f"<span class='badge pr'>PR {pr_weight:g}kg</span>" if pr_weight else ""
            timecap_html = "<span class='badge timecap'>30‑min cap</span>" if b_i == 0 else ""

            with ui_container_border():
                st.markdown(
                    f"<div class='ex-card {'done' if is_done else ''}'>"
                    f"<div style='display:flex; align-items:center; justify-content:space-between; gap:10px;'>"
                    f"<div style='min-width:60%;'><strong>{'✅' if is_done else '⭕'} {it['name']}</strong>"
                    f"<span class='badge {it['cat']}'>{it['cat']}</span>{pr_html} {timecap_html}</div>"
                    f"<div style='font-size:12px; color:#64748b; text-align:right;'>{it['reps']}</div>"
                    f"</div>"
                    f"<div style='color:#64748b; margin:8px 0 12px 0;'>{it.get('note','')}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                q1, q2, q3 = st.columns(3)
                with q1:
                    if st.button("Mark all sets ✅", key=f"all_{day}_{k}"):
                        for s in range(sets_to_show):
                            set_done(day, k, s, True)
                        if st.session_state.auto_rest:
                            start_rest(int(st.session_state.auto_rest))
                with q2:
                    if st.button("Reset exercise ↺", key=f"reset_{day}_{k}"):
                        st.session_state.workout_data.get(day, {}).pop(k, None)
                        save_state()
                with q3:
                    if st.button("Start rest ⏱️", key=f"rest_{day}_{k}"):
                        start_rest(int(st.session_state.auto_rest or 75))

                cols = st.columns(min(sets_to_show, 6))
                for s in range(sets_to_show):
                    with cols[s % 6]:
                        slot = sets_map.get(str(s), {"done": False, "weight": None, "reps": None, "rpe": None})
                        label = f"Set {s+1}"
                        if st.button(f"{'✅' if slot['done'] else label}", key=f"btn_{day}_{k}_{s}"):
                            set_done(day, k, s, not slot["done"])
                            if not slot["done"] and st.session_state.auto_rest:
                                start_rest(int(st.session_state.auto_rest))

                # Per-set logging — prefill with last values
                last_w = LAST_VALUES.get(it["name"], {}).get("weight")
                last_rpe = LAST_VALUES.get(it["name"], {}).get("rpe")
                with st.expander("Log load / RPE (optional)"):
                    dcols = st.columns(3)
                    for s in range(sets_to_show):
                        slot = sets_map.get(str(s), {"done": False, "weight": None, "reps": None, "rpe": None})
                        with dcols[s % 3]:
                            w_default = float(slot["weight"]) if slot["weight"] is not None else float(last_w or 0.0)
                            w = st.number_input(
                                f"Wgt (s{s+1})",
                                min_value=0.0,
                                value=w_default,
                                step=0.5,
                                key=f"w_{day}_{k}_{s}",
                            )
                            set_set_detail(day, k, s, "weight", w if w > 0 else None)

                            r_default = float(slot["rpe"]) if slot["rpe"] is not None else float(last_rpe or 0.0)
                            r = st.number_input(
                                f"RPE (s{s+1})",
                                min_value=0.0,
                                max_value=10.0,
                                value=r_default,
                                step=0.5,
                                key=f"rpe_{day}_{k}_{s}",
                            )
                            set_set_detail(day, k, s, "rpe", r if r > 0 else None)

                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Sticky Actions bar
    with st.container():
        st.markdown("<div class='sticky-wrap'></div>", unsafe_allow_html=True)
        st.markdown("<div class='sticky-bar'>", unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
        with c1:
            if st.button("🔄 Reset Day"):
                st.session_state.workout_data[day] = {}
                save_state()
                safe_toast("Day reset.")
        with c2:
            if st.button("⏱️ 60s Rest"):
                start_rest(60)
        with c3:
            if st.button("⏱️ 75s Rest"):
                start_rest(75)
        with c4:
            if st.button("⏱️ 90s Rest"):
                start_rest(90)
        with c5:
            if st.button("✅ Finish & Save"):
                d, t, p = compute_progress(day)
                if t == 0:
                    st.warning("No sets today yet.")
                else:
                    entry = {
                        "date": datetime.utcnow().isoformat(),
                        "day": day,
                        "workout_name": WORKOUT_TEMPLATES[day]["title"],
                        "completed_sets": d,
                        "total_sets": t,
                        "completion_percentage": p,
                        "data": st.session_state.workout_data.get(day, {}),
                        "meta": {
                            "schema": SCHEMA_VERSION,
                            "duration_sec": (datetime.utcnow() - datetime.fromisoformat(st.session_state.workout_started_at)).seconds,
                            "name_map": name_map,
                            "deload": st.session_state.deload_mode,
                        },
                    }
                    st.session_state.history.append(entry)
                    save_json(WORKOUT_HISTORY_FILE, st.session_state.history)
                    st.session_state.workout_data[day] = {}
                    st.session_state.workout_started_at = datetime.utcnow().isoformat()
                    save_state()
                    try:
                        if st.session_state.confetti_on_save:
                            st.balloons()
                    except Exception:
                        pass
                    st.success("Saved to history.")
        st.markdown("</div>", unsafe_allow_html=True)

    rest_widget()

# =============================================================
# Analytics tab
# =============================================================
with analytics_tab:
    st.markdown("<div class='section-head'>Weekly Output</div>", unsafe_allow_html=True)
    if len(st.session_state.history) == 0:
        st.info("Complete and save a workout to see analytics.")
    else:
        df = pd.DataFrame(st.session_state.history)
        df["date"] = pd.to_datetime(df["date"]) 
        df["week"] = df["date"].dt.isocalendar().week
        df["year"] = df["date"].dt.isocalendar().year

        weekly = df.groupby(["year", "week", "day"], as_index=False)["completed_sets"].sum()
        fig = go.Figure()
        for day_name in weekly["day"].unique():
            subset = weekly[weekly["day"] == day_name]
            fig.add_trace(go.Bar(x=subset["week"].astype(str), y=subset["completed_sets"], name=day_name.title()))
        fig.update_layout(barmode="group", title="Completed Sets per Week", xaxis_title="ISO Week", yaxis_title="Sets")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("<div class='section-head'>Completion % over Time</div>", unsafe_allow_html=True)
        comp = df.sort_values("date")
        fig2 = go.Figure(go.Scatter(x=comp["date"], y=comp["completion_percentage"], mode="lines+markers"))
        fig2.update_layout(yaxis_title="Completion %", xaxis_title="Date")
        st.plotly_chart(fig2, use_container_width=True)

        # Progression tips: suggest load bump if all sets logged <= RPE 7
        st.markdown("<div class='section-head'>Progression Tips</div>", unsafe_allow_html=True)
        tips = []
        # look at last 5 sessions
        for entry in sorted(st.session_state.history, key=lambda x: x["date"], reverse=True)[:5]:
            name_map = entry.get("meta", {}).get("name_map", {})
            for ex_key, sets_map in entry.get("data", {}).items():
                ex_name = name_map.get(ex_key)
                if not ex_name:
                    continue
                rpes = [slot.get("rpe") for slot in sets_map.values() if isinstance(slot, dict) and slot.get("rpe") is not None]
                if rpes and max(rpes) <= 7 and ex_name.lower().split()[0] in ("goblet", "bulgarian", "single‑leg", "hip", "overhead", "calf"):
                    tips.append(f"Increase load next time on **{ex_name}** by 0.5–2.5kg if form is solid (last session all sets ≤ RPE 7).")
        if tips:
            for t in tips[:8]:
                st.write("• ", t)
        else:
            st.caption("Log RPEs to unlock auto‑progression suggestions.")

        st.markdown("<div class='section-head'>Personal Records (by Load)</div>", unsafe_allow_html=True)
        PRS = compute_prs()
        prs_rows = sorted([(k, v) for k, v in PRS.items()], key=lambda x: x[0])
        if prs_rows:
            st.dataframe(pd.DataFrame(prs_rows, columns=["Exercise", "Max Load (kg)"]), use_container_width=True, hide_index=True)
        else:
            st.caption("No PRs yet — log some weights!")

# =============================================================
# History tab
# =============================================================
with history_tab:
    st.markdown("<div class='section-head'>Recent Workouts</div>", unsafe_allow_html=True)
    if len(st.session_state.history) == 0:
        st.info("No history yet.")
    else:
        for item in sorted(st.session_state.history, key=lambda x: x["date"], reverse=True)[:30]:
            d = pd.to_datetime(item["date"]).strftime("%b %d, %Y – %H:%M")
            dur = item.get("meta", {}).get("duration_sec")
            deload = item.get("meta", {}).get("deload")
            deload_tag = " • Deload" if deload else ""
            dur_label = f" • ⏱️ {int(dur//60)}m{int(dur%60)}s" if isinstance(dur, (int, float)) else ""
            st.markdown(
                f"**{item['workout_name']}** ({item['day'].title()}) — {d}{dur_label}{deload_tag}  "
                f"Completion: {item['completed_sets']}/{item['total_sets']} ({item['completion_percentage']}%)"
            )
            c1, c2 = st.columns([1,1])
            with c1:
                with st.expander("Details"):
                    st.json(item.get("data", {}))
            with c2:
                if st.button("Duplicate as Today", key=f"dup_{item['date']}"):
                    prefill = {}
                    for ex_key, sets_map in item.get("data", {}).items():
                        prefill[ex_key] = {s: {"done": False, "weight": None, "reps": None, "rpe": None} for s in sets_map.keys()}
                    st.session_state.workout_data[st.session_state.selected_day] = prefill
                    save_state()
                    safe_toast("Loaded past structure for today.")

# =============================================================
# Settings tab
# =============================================================
with settings_tab:
    st.markdown("<div class='section-head'>Preferences</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.auto_rest = st.number_input("Auto‑rest after set (seconds)", min_value=0, max_value=300, value=int(st.session_state.auto_rest), step=15)
        st.caption("Set to 0 to disable auto‑rest.")
        st.session_state.deload_mode = ui_toggle("Deload mode (reduce sets)", value=bool(st.session_state.deload_mode))
        st.caption("Use deload in recovery weeks or when legs feel beat up from running.")
    with col2:
        st.session_state.confetti_on_save = ui_toggle("🎉 Confetti on save", value=bool(st.session_state.confetti_on_save))
        st.caption("Because progress should feel fun.")

    st.divider()
    st.markdown("<div class='section-head'>Runner‑specific Scheduling</div>", unsafe_allow_html=True)
    st.markdown("""
    • **Mon (A)**: Heavy-ish lower + stiffness → place **after** an easy run day.
    
    • **Wed (B)**: Unilateral + elastic → pairs well with **short easy run** same day.
    
    • **Fri (C)**: Posterior chain + core → keep the day **before quality run** light on eccentrics; prioritize power & calves.
    
    If racing/doing intervals the next day, toggle **Deload**.
    """)

    st.divider()
    st.markdown("<div class='section-head'>Data</div>", unsafe_allow_html=True)
    cA, cB, cC = st.columns(3)
    with cA:
        st.download_button(
            label="⬇️ Download history.json",
            data=json.dumps(st.session_state.history, indent=2),
            file_name="workout_history.json",
            mime="application/json",
            use_container_width=True,
        )
    with cB:
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.history = []
            save_json(WORKOUT_HISTORY_FILE, [])
            st.success("History cleared.")
    with cC:
        if st.button("🧹 Clear Today", use_container_width=True):
            st.session_state.workout_data[st.session_state.selected_day] = {}
            save_state()
            safe_toast("Cleared today's sets.")

    st.caption("Schema v4 – 3‑day split, 30‑min cap, deload toggle, progression tips, tendon stiffness focus.")
