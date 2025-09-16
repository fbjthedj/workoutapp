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
    page_title="Elite 10K Runner - Strength Hub",
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
SCHEMA_VERSION = 4  # v4: Elite runner-specific programming

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
# Global styles (enhanced for elite training focus)
# =============================================================
st.markdown(
    """
    <style>
      :root { 
        --radius: 16px; 
        --muted: #64748b; 
        --space-1: 6px; 
        --space-2: 10px; 
        --space-3: 16px; 
        --space-4: 24px; 
        --card: #ffffff; 
        --line: #E5E7EB;
        --elite: #FF6B35;
        --power: #8B5CF6;
        --endurance: #10B981;
      }

      .block-container { max-width: 920px !important; padding-top: var(--space-4) !important; padding-bottom: var(--space-4) !important; }
      .main-title { text-align:center; margin: var(--space-3) 0 var(--space-1) 0; line-height: 1.15; color: var(--elite); }
      .sub-title { text-align:center; color:var(--muted); margin-bottom: var(--space-3); font-weight: 500; }
      .performance-badge { background: linear-gradient(135deg, var(--elite), var(--power)); color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 700; }
      .section-head { margin: var(--space-4) 0 var(--space-2); font-weight: 800; font-size: 1.1rem; letter-spacing: .3px; color: #1f2937; }

      .stTabs [role="tablist"] { gap: 8px; margin-bottom: var(--space-3); }
      .stTabs [role="tab"] { padding: 10px 16px; border-radius: 9999px; font-weight: 600; }

      .stButton>button { width: 100%; padding: 14px 16px; border-radius: var(--radius); font-weight: 700; margin: 6px 0; transition: all 0.2s; }
      .stButton>button:hover { transform: translateY(-1px); }

      .ex-card { 
        background: var(--card); 
        border: 2px solid var(--line); 
        border-radius: var(--radius); 
        padding: 20px 18px; 
        margin-bottom: var(--space-3); 
        box-shadow: 0 8px 25px rgba(0,0,0,0.06);
        transition: all 0.2s;
      }
      .ex-card:hover { transform: translateY(-2px); box-shadow: 0 12px 35px rgba(0,0,0,0.1); }
      .ex-card.done { 
        border-color: var(--endurance); 
        background: linear-gradient(135deg, #F0FDF4, #ECFDF5); 
        box-shadow: 0 8px 25px rgba(16,185,129,0.15); 
      }

      .badge { display:inline-block; padding:5px 11px; border-radius:9999px; font-size:11px; font-weight:700; margin-left:8px; text-transform: uppercase; letter-spacing: 0.5px; }
      .warmup { background:#FFF7ED; color:#C2410C; border: 1px solid #FDBA74; }
      .strength { background:#FEF2F2; color:#DC2626; border: 1px solid #FCA5A5; }
      .power { background:#F3E8FF; color:#7C3AED; border: 1px solid #C4B5FD; }
      .endurance { background:#ECFDF5; color:#059669; border: 1px solid #6EE7B7; }
      .stability { background:#EFF6FF; color:#2563EB; border: 1px solid #93C5FD; }
      .recovery { background:#F0FDF4; color:#16A34A; border: 1px solid #86EFAC; }
      .pr { background:linear-gradient(135deg,#FEF9C3,#FDE68A); color:#92400E; border:1px solid #F59E0B; }

      .intensity-high { border-left: 4px solid #EF4444; }
      .intensity-med { border-left: 4px solid #F59E0B; }
      .intensity-low { border-left: 4px solid #10B981; }

      .sticky-wrap { margin-top: var(--space-4); }
      .sticky-bar { 
        position: sticky; 
        bottom: 15px; 
        z-index: 50; 
        background: rgba(255,255,255,0.95); 
        backdrop-filter: blur(12px); 
        border: 2px solid var(--line); 
        padding: 14px; 
        border-radius: var(--radius); 
        display: flex; 
        gap: 12px; 
        box-shadow: 0 12px 35px rgba(0,0,0,0.1); 
      }

      .runner-stats { 
        background: linear-gradient(135deg, var(--elite), var(--power)); 
        color: white; 
        padding: 16px; 
        border-radius: var(--radius); 
        margin-bottom: var(--space-3); 
        text-align: center;
      }

      @media (prefers-color-scheme: dark) {
        :root { --card:#0F1419; --line:#374151; }
        .main-title { color: var(--elite); }
        .section-head { color: #F9FAFB; }
        .ex-card { background:var(--card); border-color:var(--line); box-shadow: 0 8px 25px rgba(0,0,0,0.4); }
        .ex-card.done { background: linear-gradient(135deg, #064E3B, #065F46); border-color: #059669; }
        .sticky-bar { background: rgba(15,20,25,0.95); border-color:var(--line); }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================
# Elite 10K Runner Templates - Science-Based 3-Day Split
# =============================================================
WORKOUT_TEMPLATES = {
    "power_strength": {
        "title": "Power & Max Strength",
        "emoji": "⚡",
        "description": "Explosive power + maximal force production for speed endurance",
        "intensity": "high",
        "duration": "28-32 min",
        "blocks": [
            {
                "name": "Neural Activation (5 min)",
                "items": [
                    {"name": "Jump rope - quick tempo", "sets": 1, "reps": "90s", "cat": "warmup", "note": "Light bounces, stay on toes. Target 140-160 rpm.", "rest": "30s"},
                    {"name": "Dynamic leg swings", "sets": 1, "reps": "10/direction", "cat": "warmup", "note": "Front-back, side-side. Controlled tempo.", "rest": "30s"},
                    {"name": "Ankle bounces", "sets": 2, "reps": "15s", "cat": "power", "note": "Stiff ankles, rapid ground contact.", "rest": "30s"},
                ],
            },
            {
                "name": "Max Strength Block (12 min)",
                "items": [
                    {"name": "Goblet squat (22kg DB)", "sets": 4, "reps": "4-6", "cat": "strength", "note": "2s down, explosive up. RPE 8-9.", "rest": "2.5min"},
                    {"name": "Single-leg Romanian deadlift (15kg DB)", "sets": 3, "reps": "5/leg", "cat": "strength", "note": "Control eccentric, powerful concentric.", "rest": "90s"},
                ],
            },
            {
                "name": "Explosive Power (8 min)",
                "items": [
                    {"name": "Kettlebell swings (24kg)", "sets": 4, "reps": "8-10", "cat": "power", "note": "Explosive hip drive, float at top.", "rest": "75s"},
                    {"name": "Jump squat (bodyweight)", "sets": 3, "reps": "6", "cat": "power", "note": "Maximal jump height, soft landing.", "rest": "60s"},
                ],
            },
            {
                "name": "Running-Specific Core (7 min)",
                "items": [
                    {"name": "Ab wheel rollouts", "sets": 3, "reps": "8-12", "cat": "stability", "note": "Maintain neutral spine throughout.", "rest": "45s"},
                    {"name": "Single-leg glute bridge (15kg DB)", "sets": 2, "reps": "10/leg", "cat": "stability", "note": "Squeeze glutes hard, avoid back arch.", "rest": "45s"},
                ],
            },
        ],
    },
    "endurance_strength": {
        "title": "Strength Endurance & Stability",
        "emoji": "🎯", 
        "description": "Muscular endurance + postural control for 10K pace maintenance",
        "intensity": "med",
        "duration": "26-30 min",
        "blocks": [
            {
                "name": "Movement Prep (4 min)",
                "items": [
                    {"name": "Jump rope - steady rhythm", "sets": 1, "reps": "2 min", "cat": "warmup", "note": "Relaxed shoulders, nasal breathing.", "rest": "45s"},
                    {"name": "World's greatest stretch", "sets": 1, "reps": "5/side", "cat": "warmup", "note": "Hip flexor + thoracic rotation.", "rest": "30s"},
                ],
            },
            {
                "name": "Unilateral Strength (14 min)",
                "items": [
                    {"name": "Bulgarian split squat (15kg DB)", "sets": 3, "reps": "8-10/leg", "cat": "strength", "note": "Control descent, drive through heel.", "rest": "90s"},
                    {"name": "Step-ups (22kg DB)", "sets": 3, "reps": "8/leg", "cat": "endurance", "note": "Full hip extension, control down.", "rest": "75s"},
                    {"name": "Single-arm DB row (22kg)", "sets": 3, "reps": "8-10/arm", "cat": "strength", "note": "Stable core, squeeze shoulder blade.", "rest": "60s"},
                ],
            },
            {
                "name": "Endurance Circuit (8 min)",
                "items": [
                    {"name": "Resistance band lateral walks", "sets": 2, "reps": "12/direction", "cat": "endurance", "note": "Maintain squat position, resist band.", "rest": "45s"},
                    {"name": "Calf raises (22kg DB)", "sets": 3, "reps": "15-20", "cat": "endurance", "note": "2s up, 1s pause, 2s down.", "rest": "45s"},
                    {"name": "Plank to downward dog", "sets": 2, "reps": "10", "cat": "stability", "note": "Smooth transitions, strong core.", "rest": "30s"},
                ],
            },
            {
                "name": "Recovery & Mobility (4 min)",
                "items": [
                    {"name": "Hip flexor stretch", "sets": 1, "reps": "60s/side", "cat": "recovery", "note": "Deep stretch, relaxed breathing.", "rest": "0s"},
                    {"name": "Calf stretch", "sets": 1, "reps": "45s/side", "cat": "recovery", "note": "Straight and bent knee versions.", "rest": "0s"},
                ],
            },
        ],
    },
    "speed_power": {
        "title": "Speed & Reactive Power", 
        "emoji": "🚀",
        "description": "Fast-twitch recruitment + elastic energy for 10K finishing speed",
        "intensity": "high", 
        "duration": "25-30 min",
        "blocks": [
            {
                "name": "CNS Activation (5 min)",
                "items": [
                    {"name": "Jump rope - high knees", "sets": 1, "reps": "60s", "cat": "warmup", "note": "High knee lift, quick feet.", "rest": "45s"},
                    {"name": "Leg swings + arm circles", "sets": 1, "reps": "8/direction", "cat": "warmup", "note": "Dynamic range of motion prep.", "rest": "30s"},
                    {"name": "Mini band monster walks", "sets": 1, "reps": "10/direction", "cat": "warmup", "note": "Activate glute medius.", "rest": "30s"},
                ],
            },
            {
                "name": "Plyometric Power (10 min)",
                "items": [
                    {"name": "Broad jumps", "sets": 4, "reps": "3", "cat": "power", "note": "Max distance, stick landing 2s.", "rest": "90s"},
                    {"name": "Lateral bounds", "sets": 3, "reps": "5/side", "cat": "power", "note": "Single leg takeoff and landing.", "rest": "75s"},
                    {"name": "Single-leg hop progression", "sets": 2, "reps": "5/leg", "cat": "power", "note": "Forward, lateral, backward hops.", "rest": "60s"},
                ],
            },
            {
                "name": "Strength-Speed (8 min)",
                "items": [
                    {"name": "Goblet squat jumps (12kg KB)", "sets": 3, "reps": "6", "cat": "power", "note": "Fast down, explosive up.", "rest": "75s"},
                    {"name": "Single-arm KB swing (24kg)", "sets": 2, "reps": "8/arm", "cat": "power", "note": "Anti-rotation focus.", "rest": "60s"},
                ],
            },
            {
                "name": "Reactive Stability (7 min)",
                "items": [
                    {"name": "Single-leg deadlift holds (12kg KB)", "sets": 2, "reps": "30s/leg", "cat": "stability", "note": "Eyes closed progression.", "rest": "45s"},
                    {"name": "Bird dog (resistance band)", "sets": 2, "reps": "8/side", "cat": "stability", "note": "Slow, controlled, resist band.", "rest": "45s"},
                    {"name": "Wall sit (22kg DB)", "sets": 1, "reps": "45-60s", "cat": "endurance", "note": "Maintain perfect posture.", "rest": "0s"},
                ],
            },
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
    st.session_state.workout_data = load_json(WORKOUT_DATA_FILE, {"_schema": SCHEMA_VERSION, "power_strength": {}, "endurance_strength": {}, "speed_power": {}})
if "history" not in st.session_state:
    st.session_state.history = load_json(WORKOUT_HISTORY_FILE, [])
if "selected_day" not in st.session_state:
    st.session_state.selected_day = get_query_param("day", "power_strength")
if "rest_timer_end" not in st.session_state:
    st.session_state.rest_timer_end = None
if "workout_started_at" not in st.session_state:
    st.session_state.workout_started_at = datetime.utcnow().isoformat()
if "auto_rest" not in st.session_state:
    st.session_state.auto_rest = 60  # Shorter rest for runner training
if "confetti_on_save" not in st.session_state:
    st.session_state.confetti_on_save = True
if "current_10k_pb" not in st.session_state:
    st.session_state.current_10k_pb = "44:00"  # Personal best
if "target_10k" not in st.session_state:
    st.session_state.target_10k = "42:00"  # Target time

def migrate(data):
    if isinstance(data, dict) and data.get("_schema") == SCHEMA_VERSION:
        return data
    # Migrate to new 3-day structure
    migrated = {"_schema": SCHEMA_VERSION, "power_strength": {}, "endurance_strength": {}, "speed_power": {}}
    
    # Try to preserve any existing data
    if isinstance(data, dict):
        for old_day in ["tuesday", "thursday"]:
            if old_day in data:
                # Map old tuesday to power_strength, thursday to endurance_strength
                new_day = "power_strength" if old_day == "tuesday" else "endurance_strength"
                day_data = data[old_day]
                new_day_data = {}
                for ex_key, sets_map in day_data.items():
                    new_day_data[ex_key] = {}
                    for idx, val in sets_map.items():
                        if isinstance(val, dict):
                            slot = {"done": bool(val.get("done")), "weight": val.get("weight"), "reps": val.get("reps"), "rpe": val.get("rpe")}
                        else:
                            slot = {"done": bool(val), "weight": None, "reps": None, "rpe": None}
                        new_day_data[ex_key][str(idx)] = slot
                migrated[new_day] = new_day_data
                
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
            total_sets += sets
            k = ex_key_from(b_i, i_i)
            for s in range(sets):
                if st.session_state.workout_data.get(day, {}).get(k, {}).get(str(s), {}).get("done"):
                    done_sets += 1
    pct = (done_sets / total_sets * 100) if total_sets else 0
    return done_sets, total_sets, round(pct, 1)

def progress_ring(pct):
    # Enhanced progress ring with runner theme
    color = "#EF4444" if pct < 50 else "#F59E0B" if pct < 80 else "#10B981"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number={'suffix': '%', 'font': {'size': 32, 'color': color}},
        gauge={
            'axis': {'range': [0, 100]}, 
            'bar': {'thickness': 0.3, 'color': color}, 
            'bgcolor': 'rgba(0,0,0,0)',
            'borderwidth': 2,
            'bordercolor': color
        }
    ))
    fig.update_layout(height=180, margin=dict(l=5, r=5, t=5, b=5))
    st.plotly_chart(fig, use_container_width=True)

def start_rest(seconds: int):
    st.session_state.rest_timer_end = (datetime.utcnow() + timedelta(seconds=seconds)).isoformat()

def rest_widget():
    if st.session_state.rest_timer_end:
        end = datetime.fromisoformat(st.session_state.rest_timer_end)
        remaining = (end - datetime.utcnow()).total_seconds()
        if remaining <= 0:
            st.success("🔥 Rest complete! Next set ready!")
            st.session_state.rest_timer_end = None
        else:
            mm, ss = divmod(int(remaining), 60)
            st.info(f"⏱️ Rest: {mm:02d}:{ss:02d} remaining")
            safe_rerun()

def elapsed_widget():
    start = datetime.fromisoformat(st.session_state.workout_started_at)
    elapsed = (datetime.utcnow() - start).total_seconds()
    mm = int(elapsed // 60)
    ss = int(elapsed % 60)
    return f"{mm:02d}:{ss:02d}"

# History helpers for auto-progression
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
# Header with Runner Stats
# =============================================================
st.markdown(
    """
<h1 class='main-title'>🏃‍♂️ Elite 10K Runner - Strength Hub</h1>
<p class='sub-title'>Science-based strength training for sub-44 minute 10K performance</p>
""",
    unsafe_allow_html=True,
)

# Runner performance dashboard
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        f"""
        <div class='runner-stats'>
            <div style='font-size: 24px; font-weight: bold;'>{st.session_state.current_10k_pb}</div>
            <div style='font-size: 12px; opacity: 0.9;'>Current 10K PB</div>
        </div>
        """, 
        unsafe_allow_html=True
    )
with col2:
    st.markdown(
        f"""
        <div class='runner-stats'>
            <div style='font-size: 24px; font-weight: bold;'>{st.session_state.target_10k}</div>
            <div style='font-size: 12px; opacity: 0.9;'>Target 10K</div>
        </div>
        """, 
        unsafe_allow_html=True
    )
with col3:
    pace_current = int(st.session_state.current_10k_pb.split(':')[0]) * 60 + int(st.session_state.current_10k_pb.split(':')[1])
    pace_per_km = pace_current / 10
    mm, ss = divmod(int(pace_per_km), 60)
    st.markdown(
        f"""
        <div class='runner-stats'>
            <div style='font-size: 24px; font-weight: bold;'>{mm}:{ss:02d}</div>
            <div style='font-size: 12px; opacity: 0.9;'>Current Pace/km</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

date_label = datetime.now().strftime("%a, %b %d")
elapsed_time = elapsed_widget()
st.markdown(
    f"""
    <div style='text-align: center; margin: 16px 0;'>
        <span class='performance-badge'>📅 {date_label} • ⏱️ Session: {elapsed_time}</span>
    </div>
    """,
    unsafe_allow_html=True
)

# =============================================================
# Tabs
# =============================================================
main_tab, analytics_tab, history_tab, settings_tab = st.tabs([
    "💪 Training",
    "📈 Performance", 
    "📚 Log",
    "⚙️ Settings",
])

# =============================================================
# Main Training Tab
# =============================================================
with main_tab:
    col_day, col_prog = st.columns([2, 1])
    with col_day:
        day = ui_segmented(
            "Training Session",
            options=["power_strength", "endurance_strength", "speed_power"],
            default=st.session_state.selected_day,
            format_func=lambda d: f"{WORKOUT_TEMPLATES[d]['emoji']} {WORKOUT_TEMPLATES[d]['title']}"
        )
        st.session_state.selected_day = day
        set_query_param("day", day)
        
        # Session description
        template = WORKOUT_TEMPLATES[day]
        intensity_class = f"intensity-{template['intensity']}"
        st.markdown(
            f"""
            <div class='ex-card {intensity_class}' style='margin-top: 12px;'>
                <div style='font-weight: 600; color: #374151; margin-bottom: 6px;'>{template['description']}</div>
                <div style='display: flex; gap: 16px; font-size: 12px; color: #6B7280;'>
                    <span>🎯 Duration: {template['duration']}</span>
                    <span>🔥 Intensity: {template['intensity'].upper()}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col_prog:
        done, total, pct = compute_progress(day)
        progress_ring(pct)
        st.caption(f"✅ {done}/{total} sets complete")

    # Render workout blocks
    name_map = {}  # ex_key -> exercise display name for metadata
    
    for b_i, block in enumerate(WORKOUT_TEMPLATES[day]["blocks"]):
        st.markdown(f"<div class='section-head'>{block['name']}</div>", unsafe_allow_html=True)
        
        for i_i, it in enumerate(block["items"]):
            k = ex_key_from(b_i, i_i)
            name_map[k] = it["name"]

            sets_map = st.session_state.workout_data.get(day, {}).get(k, {})
            done_sets = sum(1 for s in range(it["sets"]) if sets_map.get(str(s), {}).get("done"))
            is_done = done_sets == it["sets"]

            # PR badge if applicable
            pr_weight = PRS.get(it["name"])
            pr_html = f"<span class='badge pr'>PR {pr_weight:g}kg</span>" if pr_weight else ""
            
            # Rest recommendation
            rest_time = it.get("rest", "60s")

            # Card with enhanced styling
            intensity_class = f"intensity-{WORKOUT_TEMPLATES[day]['intensity']}"
            with ui_container_border():
                st.markdown(
                    f"""
                    <div class='ex-card {intensity_class} {'done' if is_done else ''}'>
                        <div style='display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom: 8px;'>
                            <div style='min-width:60%;'>
                                <strong>{'✅' if is_done else '⚡'} {it['name']}</strong>
                                <span class='badge {it['cat']}'>{it['cat']}</span>
                                {pr_html}
                            </div>
                            <div style='font-size:12px; color:#6B7280; text-align:right;'>
                                <div>{it['reps']}</div>
                                <div>Rest: {rest_time}</div>
                            </div>
                        </div>
                        <div style='color:#6B7280; font-size:13px; margin-bottom: 12px;'>{it.get('note','')}</div>
                    """,
                    unsafe_allow_html=True,
                )

                # Enhanced action buttons
                q1, q2, q3, q4 = st.columns(4)
                with q1:
                    if st.button("✅ All Sets", key=f"all_{day}_{k}", help="Complete all sets"):
                        for s in range(it["sets"]):
                            set_done(day, k, s, True)
                        if st.session_state.auto_rest:
                            rest_seconds = int(rest_time.replace('s', '').replace('min', '')) * (60 if 'min' in rest_time else 1)
                            start_rest(rest_seconds)
                
                with q2:
                    if st.button("🔄 Reset", key=f"reset_{day}_{k}", help="Reset this exercise"):
                        st.session_state.workout_data.get(day, {}).pop(k, None)
                        save_state()
                
                with q3:
                    if st.button("⏱️ Rest", key=f"rest_{day}_{k}", help=f"Start {rest_time} timer"):
                        rest_seconds = int(rest_time.replace('s', '').replace('min', '')) * (60 if 'min' in rest_time else 1)
                        start_rest(rest_seconds)
                
                with q4:
                    if st.button("📊 RPE", key=f"rpe_{day}_{k}", help="Quick RPE entry"):
                        # This could expand RPE entry or be a quick action
                        pass

                # Set tracking with enhanced UI
                st.markdown("**Set Progress:**")
                set_cols = st.columns(min(it["sets"], 6))
                for s in range(it["sets"]):
                    with set_cols[s % 6]:
                        slot = sets_map.get(str(s), {"done": False, "weight": None, "reps": None, "rpe": None})
                        
                        # Enhanced set button with weight/RPE display
                        weight_display = f" ({slot['weight']}kg)" if slot.get('weight') else ""
                        rpe_display = f" RPE{slot['rpe']}" if slot.get('rpe') else ""
                        button_text = f"{'✅' if slot['done'] else f'Set {s+1}'}{weight_display}{rpe_display}"
                        
                        if st.button(button_text, key=f"btn_{day}_{k}_{s}"):
                            set_done(day, k, s, not slot["done"])
                            if not slot["done"] and st.session_state.auto_rest:
                                rest_seconds = int(rest_time.replace('s', '').replace('min', '')) * (60 if 'min' in rest_time else 1)
                                start_rest(rest_seconds)

                # Enhanced logging with smart defaults
                last_w = LAST_VALUES.get(it["name"], {}).get("weight")
                last_rpe = LAST_VALUES.get(it["name"], {}).get("rpe")
                
                with st.expander("📝 Log Details (Weight/RPE/Notes)"):
                    log_cols = st.columns(2)
                    
                    # Quick-fill buttons for common weights
                    with log_cols[0]:
                        st.markdown("**Quick Fill Weights:**")
                        qw1, qw2, qw3 = st.columns(3)
                        with qw1:
                            if st.button("12kg", key=f"qw12_{day}_{k}"):
                                for s in range(it["sets"]):
                                    set_set_detail(day, k, s, "weight", 12)
                        with qw2:
                            if st.button("15kg", key=f"qw15_{day}_{k}"):
                                for s in range(it["sets"]):
                                    set_set_detail(day, k, s, "weight", 15)
                        with qw3:
                            if st.button("22kg", key=f"qw22_{day}_{k}"):
                                for s in range(it["sets"]):
                                    set_set_detail(day, k, s, "weight", 22)
                    
                    with log_cols[1]:
                        st.markdown("**Quick Fill RPE:**")
                        qr1, qr2, qr3 = st.columns(3)
                        with qr1:
                            if st.button("RPE 7", key=f"qr7_{day}_{k}"):
                                for s in range(it["sets"]):
                                    set_set_detail(day, k, s, "rpe", 7)
                        with qr2:
                            if st.button("RPE 8", key=f"qr8_{day}_{k}"):
                                for s in range(it["sets"]):
                                    set_set_detail(day, k, s, "rpe", 8)
                        with qr3:
                            if st.button("RPE 9", key=f"qr9_{day}_{k}"):
                                for s in range(it["sets"]):
                                    set_set_detail(day, k, s, "rpe", 9)
                    
                    # Individual set logging
                    st.markdown("**Individual Set Details:**")
                    detail_cols = st.columns(min(it["sets"], 3))
                    for s in range(it["sets"]):
                        with detail_cols[s % 3]:
                            slot = sets_map.get(str(s), {"done": False, "weight": None, "reps": None, "rpe": None})
                            
                            w_default = float(slot["weight"]) if slot["weight"] is not None else float(last_w or 0.0)
                            w = st.number_input(
                                f"Weight S{s+1} (kg)",
                                min_value=0.0,
                                max_value=50.0,
                                value=w_default,
                                step=0.5,
                                key=f"w_{day}_{k}_{s}",
                            )
                            set_set_detail(day, k, s, "weight", w if w > 0 else None)

                            r_default = float(slot["rpe"]) if slot["rpe"] is not None else float(last_rpe or 0.0)
                            r = st.number_input(
                                f"RPE S{s+1}",
                                min_value=0.0,
                                max_value=10.0,
                                value=r_default,
                                step=0.5,
                                key=f"rpe_{day}_{k}_{s}",
                                help="Rate of Perceived Exertion (6-10 scale)"
                            )
                            set_set_detail(day, k, s, "rpe", r if r > 0 else None)

                st.markdown("</div><div style='height:12px'></div>", unsafe_allow_html=True)

    # Enhanced Sticky Actions bar
    st.markdown("<div class='sticky-wrap'></div>", unsafe_allow_html=True)
    st.markdown("<div class='sticky-bar'>", unsafe_allow_html=True)
    
    action_cols = st.columns([1, 1, 1, 1, 1])
    
    with action_cols[0]:
        if st.button("🔄 Reset", help="Reset entire session"):
            st.session_state.workout_data[day] = {}
            save_state()
            safe_toast("Session reset!")
    
    with action_cols[1]:
        if st.button("⏱️ 1min", help="1 minute rest"):
            start_rest(60)
    
    with action_cols[2]:
        if st.button("⏱️ 2min", help="2 minute rest"):
            start_rest(120)
    
    with action_cols[3]:
        if st.button("⏱️ 3min", help="3 minute rest"):
            start_rest(180)
    
    with action_cols[4]:
        if st.button("✅ Complete", help="Finish and save session"):
            d, t, p = compute_progress(day)
            if t == 0:
                st.warning("⚠️ No sets completed yet!")
            else:
                session_duration = (datetime.utcnow() - datetime.fromisoformat(st.session_state.workout_started_at)).seconds
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
                        "duration_sec": session_duration,
                        "name_map": name_map,
                        "intensity": WORKOUT_TEMPLATES[day]["intensity"],
                        "target_duration": WORKOUT_TEMPLATES[day]["duration"],
                    },
                }
                st.session_state.history.append(entry)
                save_json(WORKOUT_HISTORY_FILE, st.session_state.history)
                st.session_state.workout_data[day] = {}
                st.session_state.workout_started_at = datetime.utcnow().isoformat()
                save_state()
                
                # Performance feedback
                if p >= 90:
                    feedback = "🔥 Outstanding session! Elite performance!"
                elif p >= 75:
                    feedback = "💪 Strong session! Keep building!"
                elif p >= 50:
                    feedback = "👍 Good work! Consistency is key!"
                else:
                    feedback = "👊 Every rep counts! Progress over perfection!"
                
                try:
                    if st.session_state.confetti_on_save and p >= 75:
                        st.balloons()
                except Exception:
                    pass
                
                st.success(f"✅ Session saved! {feedback}")
    
    st.markdown("</div>", unsafe_allow_html=True)

    # Rest timer with enhanced display
    if st.session_state.rest_timer_end:
        end = datetime.fromisoformat(st.session_state.rest_timer_end)
        remaining = (end - datetime.utcnow()).total_seconds()
        if remaining <= 0:
            st.success("🔥 Rest complete! Time to work!")
            if st.button("Clear Timer"):
                st.session_state.rest_timer_end = None
            safe_rerun()
        else:
            mm, ss = divmod(int(remaining), 60)
            progress_pct = 100 - (remaining / 180 * 100)  # Assuming max 3min rest
            st.progress(min(progress_pct, 100))
            st.info(f"⏱️ Rest Timer: {mm:02d}:{ss:02d} remaining")
            safe_rerun()

# =============================================================
# Performance Analytics Tab
# =============================================================
with analytics_tab:
    if len(st.session_state.history) == 0:
        st.markdown(
            """
            <div class='ex-card' style='text-align: center; padding: 40px;'>
                <h3>📈 Performance Analytics</h3>
                <p>Complete and save your first workout to unlock detailed performance insights!</p>
                <p style='color: #6B7280; font-size: 14px;'>Track strength gains, session consistency, and training load progression.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # Enhanced analytics for runners
        df = pd.DataFrame(st.session_state.history)
        df["date"] = pd.to_datetime(df["date"])
        df["week"] = df["date"].dt.isocalendar().week
        df["year"] = df["date"].dt.year

        st.markdown("<div class='section-head'>🏃‍♂️ Training Load Analysis</div>", unsafe_allow_html=True)
        
        # Training frequency and consistency
        col1, col2 = st.columns(2)
        
        with col1:
            # Weekly training frequency
            weekly_sessions = df.groupby(["year", "week"]).size().reset_index(name='sessions')
            fig_freq = go.Figure(go.Bar(
                x=weekly_sessions["week"], 
                y=weekly_sessions["sessions"],
                marker_color='#FF6B35',
                name='Sessions/Week'
            ))
            fig_freq.update_layout(
                title="Weekly Training Frequency", 
                xaxis_title="Week", 
                yaxis_title="Sessions",
                showlegend=False
            )
            st.plotly_chart(fig_freq, use_container_width=True)
        
        with col2:
            # Completion percentage trend
            completion_trend = df.sort_values("date")
            fig_comp = go.Figure(go.Scatter(
                x=completion_trend["date"], 
                y=completion_trend["completion_percentage"],
                mode="lines+markers",
                marker_color='#10B981',
                name='Completion %'
            ))
            fig_comp.update_layout(
                title="Session Completion Trend", 
                xaxis_title="Date", 
                yaxis_title="Completion %",
                showlegend=False
            )
            st.plotly_chart(fig_comp, use_container_width=True)

        # Training split analysis
        st.markdown("<div class='section-head'>💪 Training Split Performance</div>", unsafe_allow_html=True)
        
        split_performance = df.groupby('day').agg({
            'completion_percentage': 'mean',
            'completed_sets': 'sum',
            'date': 'count'
        }).round(1)
        split_performance.columns = ['Avg Completion %', 'Total Sets', 'Sessions']
        
        # Add session type emoji mapping
        split_performance.index = split_performance.index.map(
            lambda x: f"{WORKOUT_TEMPLATES[x]['emoji']} {WORKOUT_TEMPLATES[x]['title']}"
        )
        
        st.dataframe(split_performance, use_container_width=True)

        # PRs and strength progression
        st.markdown("<div class='section-head'>🏆 Strength Progression & PRs</div>", unsafe_allow_html=True)
        
        if PRS:
            # Create PR visualization
            pr_df = pd.DataFrame(list(PRS.items()), columns=['Exercise', 'Max Weight (kg)'])
            pr_df = pr_df.sort_values('Max Weight (kg)', ascending=True)
            
            fig_pr = go.Figure(go.Bar(
                x=pr_df['Max Weight (kg)'],
                y=pr_df['Exercise'],
                orientation='h',
                marker_color='#8B5CF6',
                text=pr_df['Max Weight (kg)'].astype(str) + 'kg',
                textposition='inside'
            ))
            fig_pr.update_layout(
                title="Personal Records by Exercise",
                xaxis_title="Weight (kg)",
                yaxis_title="Exercise",
                showlegend=False,
                height=400
            )
            st.plotly_chart(fig_pr, use_container_width=True)
            
            # Strength balance analysis
            st.markdown("**Strength Balance Analysis:**")
            key_lifts = {
                'Goblet squat': pr_df[pr_df['Exercise'].str.contains('Goblet squat', case=False, na=False)]['Max Weight (kg)'].max() if not pr_df[pr_df['Exercise'].str.contains('Goblet squat', case=False, na=False)].empty else 0,
                'Romanian deadlift': pr_df[pr_df['Exercise'].str.contains('Romanian deadlift|Single-leg Romanian deadlift', case=False, na=False)]['Max Weight (kg)'].max() if not pr_df[pr_df['Exercise'].str.contains('Romanian deadlift', case=False, na=False)].empty else 0,
                'Bulgarian split squat': pr_df[pr_df['Exercise'].str.contains('Bulgarian split squat', case=False, na=False)]['Max Weight (kg)'].max() if not pr_df[pr_df['Exercise'].str.contains('Bulgarian split squat', case=False, na=False)].empty else 0,
            }
            
            balance_analysis = []
            for lift, weight in key_lifts.items():
                if weight > 0:
                    balance_analysis.append(f"• **{lift}**: {weight}kg")
            
            if balance_analysis:
                st.markdown('\n'.join(balance_analysis))
        else:
            st.info("💡 Start logging weights to track your strength progression and PRs!")

        # Training insights and recommendations
        st.markdown("<div class='section-head'>🎯 Performance Insights</div>", unsafe_allow_html=True)
        
        insights = []
        avg_completion = df['completion_percentage'].mean()
        
        if avg_completion >= 85:
            insights.append("🔥 **Excellent consistency!** You're maintaining high completion rates.")
        elif avg_completion >= 70:
            insights.append("💪 **Good consistency.** Consider focusing on challenging sessions.")
        else:
            insights.append("👊 **Building momentum.** Consistency will unlock your potential.")
        
        # Session duration analysis
        if 'meta' in df.columns:
            durations = []
            for _, row in df.iterrows():
                if isinstance(row['meta'], dict) and 'duration_sec' in row['meta']:
                    durations.append(row['meta']['duration_sec'] / 60)  # Convert to minutes
            
            if durations:
                avg_duration = sum(durations) / len(durations)
                if avg_duration <= 35:
                    insights.append(f"⏱️ **Efficient training!** Average session: {avg_duration:.1f} minutes.")
                else:
                    insights.append(f"⏱️ **Session time:** {avg_duration:.1f} minutes average. Consider time efficiency.")
        
        # Weekly frequency analysis
        recent_weeks = df[df['date'] >= (datetime.now() - timedelta(weeks=4))]
        if len(recent_weeks) > 0:
            weekly_avg = len(recent_weeks) / 4
            if weekly_avg >= 3:
                insights.append("📅 **Optimal frequency!** You're hitting 3+ sessions per week.")
            elif weekly_avg >= 2:
                insights.append("📅 **Good frequency.** Try to add one more session per week.")
            else:
                insights.append("📅 **Opportunity:** Aim for 3 sessions per week for optimal results.")
        
        for insight in insights:
            st.markdown(insight)

# =============================================================
# History/Log Tab
# =============================================================
with history_tab:
    st.markdown("<div class='section-head'>📚 Training History</div>", unsafe_allow_html=True)
    
    if len(st.session_state.history) == 0:
        st.markdown(
            """
            <div class='ex-card' style='text-align: center; padding: 40px;'>
                <h3>📅 Training Log</h3>
                <p>Your training history will appear here after completing sessions.</p>
                <p style='color: #6B7280; font-size: 14px;'>Track your progress, review past workouts, and duplicate successful sessions.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # Enhanced history display
        for i, item in enumerate(sorted(st.session_state.history, key=lambda x: x["date"], reverse=True)[:50]):
            date_obj = pd.to_datetime(item["date"])
            date_str = date_obj.strftime("%a, %b %d • %H:%M")
            
            # Session metrics
            dur = item.get("meta", {}).get("duration_sec", 0)
            dur_str = f"{int(dur//60)}m {int(dur%60)}s" if dur else "N/A"
            
            completion = item["completion_percentage"]
            intensity = item.get("meta", {}).get("intensity", "med")
            
            # Color coding based on completion
            if completion >= 90:
                status_color = "#10B981"
                status_icon = "🔥"
            elif completion >= 75:
                status_color = "#F59E0B" 
                status_icon = "💪"
            else:
                status_color = "#6B7280"
                status_icon = "👊"
                
            # Session card
            with st.expander(f"{status_icon} {item['workout_name']} - {date_str} ({completion}% complete)"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Duration:** {dur_str} • **Intensity:** {intensity.upper()}")
                    st.markdown(f"**Sets:** {item['completed_sets']}/{item['total_sets']}")
                    
                    # Show exercise details if available
                    if 'data' in item and 'meta' in item:
                        name_map = item['meta'].get('name_map', {})
                        exercise_details = []
                        
                        for ex_key, sets_data in item['data'].items():
                            ex_name = name_map.get(ex_key, ex_key)
                            completed_sets = sum(1 for s in sets_data.values() if isinstance(s, dict) and s.get('done'))
                            total_sets = len(sets_data)
                            
                            # Get max weight used
                            weights = [s.get('weight') for s in sets_data.values() if isinstance(s, dict) and s.get('weight')]
                            max_weight = max(weights) if weights else None
                            weight_str = f" @ {max_weight}kg" if max_weight else ""
                            
                            exercise_details.append(f"• {ex_name}: {completed_sets}/{total_sets} sets{weight_str}")
                        
                        if exercise_details:
                            st.markdown("**Exercise Details:**")
                            for detail in exercise_details[:8]:  # Limit display
                                st.markdown(detail, help="Click to expand for full session data")
                
                with col2:
                    # Action buttons
                    if st.button("🔄 Duplicate", key=f"dup_{i}", help="Copy this session structure"):
                        # Copy structure but reset completion status
                        prefill = {}
                        for ex_key, sets_map in item.get("data", {}).items():
                            prefill[ex_key] = {}
                            for s_idx in sets_map.keys():
                                prefill[ex_key][s_idx] = {
                                    "done": False, 
                                    "weight": None, 
                                    "reps": None, 
                                    "rpe": None
                                }
                        st.session_state.workout_data[st.session_state.selected_day] = prefill
                        save_state()
                        safe_toast("🔄 Session structure copied to current workout!")
                    
                    if st.button("📊 Details", key=f"detail_{i}", help="View raw session data"):
                        st.json(item)

# =============================================================
# Settings Tab
# =============================================================
with settings_tab:
    st.markdown("<div class='section-head'>🏃‍♂️ Runner Profile</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_pb = st.text_input(
            "Current 10K PB (mm:ss)", 
            value=st.session_state.current_10k_pb,
            help="Your current personal best 10K time"
        )
        if new_pb != st.session_state.current_10k_pb:
            st.session_state.current_10k_pb = new_pb
    
    with col2:
        new_target = st.text_input(
            "Target 10K Time (mm:ss)", 
            value=st.session_state.target_10k,
            help="Your goal 10K time"
        )
        if new_target != st.session_state.target_10k:
            st.session_state.target_10k = new_target

    # Training preferences
    st.markdown("<div class='section-head'>⚙️ Training Preferences</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.auto_rest = st.selectbox(
            "Auto-rest after sets",
            options=[0, 30, 45, 60, 75, 90, 120],
            index=[0, 30, 45, 60, 75, 90, 120].index(int(st.session_state.auto_rest)),
            help="Automatically start rest timer after completing sets"
        )
        st.caption("Set to 0 to disable auto-rest timers")
    
    with col2:
        st.session_state.confetti_on_save = ui_toggle(
            "🎉 Celebration effects", 
            value=bool(st.session_state.confetti_on_save)
        )

    # Equipment check
    st.markdown("<div class='section-head'>🏋️ Available Equipment</div>", unsafe_allow_html=True)
    
    equipment_list = [
        "✅ Jump ropes (warmup/cardio)",
        "✅ Dumbbells: 12.5kg, 15kg, 22kg", 
        "✅ Kettlebells: 12kg, 24kg",
        "✅ Resistance bands",
        "✅ Ab wheel",
        "✅ Workout bench"
    ]
    
    for equipment in equipment_list:
        st.markdown(equipment)

    st.info("💡 **Training Philosophy:** This program focuses on strength qualities most beneficial for 10K performance: maximal strength, power endurance, and neuromuscular efficiency.")

    # Data management
    st.divider()
    st.markdown("<div class='section-head'>💾 Data Management</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Enhanced download with metadata
        if st.session_state.history:
            export_data = {
                "export_date": datetime.utcnow().isoformat(),
                "runner_profile": {
                    "current_10k_pb": st.session_state.current_10k_pb,
                    "target_10k": st.session_state.target_10k
                },
                "training_history": st.session_state.history,
                "schema_version": SCHEMA_VERSION
            }
            st.download_button(
                label="⬇️ Export Data",
                data=json.dumps(export_data, indent=2),
                file_name=f"runner_training_data_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True,
                help="Download complete training history with profile data"
            )
        else:
            st.button("⬇️ Export Data", disabled=True, use_container_width=True, help="No data to export yet")
    
    with col2:
        if st.button("🗑️ Clear History", use_container_width=True, help="Delete all training history"):
            if st.session_state.history:
                st.session_state.history = []
                save_json(WORKOUT_HISTORY_FILE, [])
                st.success("Training history cleared!")
            else:
                st.info("No history to clear")
    
    with col3:
        if st.button("🧹 Reset Session", use_container_width=True, help="Clear current session data"):
            st.session_state.workout_data[st.session_state.selected_day] = {}
            save_state()
            safe_toast("Current session reset!")

    # Training program information
    st.divider()
    st.markdown("<div class='section-head'>📖 Program Information</div>", unsafe_allow_html=True)
    
    with st.expander("🏃‍♂️ Elite 10K Training Methodology"):
        st.markdown(
            """
            **Program Design Philosophy:**
            
            This 3-day strength training program is specifically designed for 10K runners targeting sub-44 minute performance. 
            The program integrates elite endurance training principles with targeted strength development.
            
            **Session Breakdown:**
            
            **⚡ Power & Max Strength (Day 1)**
            - Focus: Maximal force production and explosive power
            - Key adaptations: Type II fiber recruitment, rate of force development
            - Running benefit: Improved stride power and neuromuscular efficiency
            
            **🎯 Strength Endurance & Stability (Day 2)**  
            - Focus: Muscular endurance and postural control
            - Key adaptations: Force maintenance, core stability
            - Running benefit: Better pace maintenance and form preservation
            
            **🚀 Speed & Reactive Power (Day 3)**
            - Focus: Fast-twitch activation and elastic energy utilization  
            - Key adaptations: Stretch-shortening cycle, reactive strength
            - Running benefit: Improved running economy and finishing speed
            
            **Evidence-Based Principles:**
            - Progressive overload through load and complexity
            - Unilateral training for running-specific strength
            - Plyometric integration for elastic energy development
            - Core stability for energy transfer efficiency
            - Recovery protocols for adaptation optimization
            
            **Expected Outcomes (8-12 weeks):**
            - 2-5% improvement in running economy
            - Enhanced neuromuscular power
            - Reduced injury risk through strength balance
            - Improved 10K performance through strength-speed development
            """
        )
    
    with st.expander("🎯 RPE Scale Guide"):
        st.markdown(
            """
            **Rate of Perceived Exertion (RPE) Scale:**
            
            Use this scale to gauge your effort level for each set:
            
            - **RPE 6-7**: Light to moderate effort, could do many more reps
            - **RPE 8**: Hard effort, could do 2-3 more reps with good form  
            - **RPE 9**: Very hard, could do 1 more rep maximum
            - **RPE 10**: Maximum effort, could not do another rep
            
            **Recommended RPE by Exercise Type:**
            - **Strength exercises**: RPE 7-9 (build strength reserves)
            - **Power exercises**: RPE 7-8 (maintain speed/quality)
            - **Endurance exercises**: RPE 6-8 (volume tolerance)
            - **Stability exercises**: RPE 6-7 (control and form focus)
            
            **For 10K Performance:**
            Training at appropriate RPE levels develops the neuromuscular qualities 
            needed for sustained pace at race intensities (~85-90% max HR).
            """
        )
    
    with st.expander("⏱️ Rest Interval Guidelines"):
        st.markdown(
            """
            **Optimal Rest Periods by Training Goal:**
            
            **Maximum Strength (RPE 8-9):**
            - Heavy compound movements: 2-3 minutes
            - Allows ATP-PC system recovery for maximal force output
            
            **Power Development:**
            - Explosive movements: 75-90 seconds  
            - Maintains power output quality across sets
            
            **Strength Endurance:**
            - Moderate loads: 45-75 seconds
            - Develops fatigue resistance while maintaining force
            
            **Stability/Core:**
            - Control-focused: 30-60 seconds
            - Emphasizes muscular endurance and motor control
            
            **Running Application:**
            Proper rest ensures quality training adaptations that transfer 
            to improved running performance and reduced injury risk.
            """
        )

    st.markdown(
        f"""
        <div style='text-align: center; margin-top: 24px; padding: 16px; background: linear-gradient(135deg, #FF6B35, #8B5CF6); 
        color: white; border-radius: 12px;'>
        <strong>Elite 10K Runner Strength Hub v{SCHEMA_VERSION}</strong><br>
        <small>Science-based training for sub-44 minute 10K performance</small>
        </div>
        """,
        unsafe_allow_html=True
    )

# =============================================================
# Footer - Training Tips
# =============================================================
if st.session_state.selected_day in ["power_strength", "endurance_strength", "speed_power"]:
    with st.container():
        st.markdown("---")
        
        # Rotating training tips based on selected day
        tips = {
            "power_strength": [
                "💡 **Tip:** Focus on explosive concentric (lifting) phase for maximum power development",
                "🏃 **Running connection:** Improved stride power transfers to better hill running and finishing kicks",
                "⚡ **Elite insight:** Olympic lifters average 4:30/mile pace during weightlifting movements"
            ],
            "endurance_strength": [
                "💡 **Tip:** Control the eccentric (lowering) phase to build strength endurance",
                "🏃 **Running connection:** Better form maintenance during fatigue = consistent pacing",
                "🎯 **Elite insight:** Unilateral training addresses the single-leg nature of running"
            ],
            "speed_power": [
                "💡 **Tip:** Focus on landing mechanics and rapid ground contact times",
                "🏃 **Running connection:** Improved elastic energy storage = better running economy",
                "🚀 **Elite insight:** Plyometrics can improve running economy by 2-8%"
            ]
        }
        
        current_tips = tips.get(st.session_state.selected_day, tips["power_strength"])
        tip_index = len(st.session_state.history) % len(current_tips)  # Rotate based on history length
        
        st.info(current_tips[tip_index])
