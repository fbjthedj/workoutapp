import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# --------------------------
# Page config (mobile-first)
# --------------------------
st.set_page_config(
    page_title="10K Speed – Strength Tracker",
    page_icon="🏃‍♂️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --------------------------
# Global constants & files
# --------------------------
DATA_DIR = "."
WORKOUT_DATA_FILE = os.path.join(DATA_DIR, "workout_data.json")
WORKOUT_HISTORY_FILE = os.path.join(DATA_DIR, "workout_history.json")
SCHEMA_VERSION = 2

# --------------------------
# Styles – touch-friendly
# --------------------------
st.markdown(
    """
    <style>
      :root { --radius: 14px; }
      .main-title { text-align:center; margin: 0.6rem 0 0.2rem 0; }
      .sub-title { text-align:center; color:#5b6573; margin-bottom:0.8rem; }

      /* Make buttons large and easy to tap */
      .stButton>button { width: 100%; padding: 14px 16px; border-radius: var(--radius); font-weight: 600; }
      .chip-row { display:flex; gap:8px; flex-wrap: wrap; }
      .chip { flex: 1 1 80px; min-width: 80px; border:1px solid #E5E7EB; padding: 10px 12px; border-radius: 9999px; text-align:center; cursor:pointer; background:#fff; }
      .chip.done { background:#DCFCE7; border-color:#86EFAC; }

      .ex-card { background:#fff; border:1.5px solid #E5E7EB; border-radius: var(--radius); padding:14px; }
      .ex-card.done { border-color:#10B981; background: #F0FDF4; }
      .badge { display:inline-block; padding:4px 10px; border-radius:9999px; font-size:12px; font-weight:600; margin-left:8px; }
      .warmup { background:#FFEAD5; color:#9A3412; }
      .strength { background:#FEE2E2; color:#991B1B; }
      .power { background:#EDE9FE; color:#6D28D9; }
      .core { background:#DBEAFE; color:#1E40AF; }
      .accessory { background:#F1F5F9; color:#0F172A; }
      .cooldown { background:#DCFCE7; color:#166534; }

      .sticky-bar { position: sticky; bottom: 6px; z-index: 100; background: rgba(255,255,255,0.9); backdrop-filter: blur(6px); border:1px solid #E5E7EB; padding:10px; border-radius: var(--radius); display:flex; gap:10px; }

      @media (prefers-color-scheme: dark) {
        .ex-card { background:#0B1220; border-color:#263041; }
        .ex-card.done { background:#0f1b12; border-color:#14532d; }
        .chip { background:#0B1220; border-color:#263041; }
        .chip.done { background:#0f1b12; border-color:#14532d; }
        .sticky-bar { background: rgba(9,13,22,0.85); border-color:#263041; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------
# Utilities – load/save/migrate
# --------------------------
@st.cache_data
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
        st.error(f"Could not save to {path}: {e}")


# Workout templates – tuned for sub-45 10K (strength + power)
# Rep ranges emphasize max strength (3–6), speed-strength, and ankle stiffness.
WORKOUT_TEMPLATES = {
    "tuesday": {
        "title": "Max Strength + Plyo",
        "emoji": "🔵",
        "blocks": [
            {
                "name": "Warm-up",
                "items": [
                    {"name": "Jump rope – quick contacts (¼ lb)", "sets": 1, "reps": "2–3 min", "cat": "warmup", "note": "Light, bouncy. Nose-breath if possible."},
                    {"name": "Leg swings + inchworms", "sets": 1, "reps": "10/dir + 6", "cat": "warmup", "note": "Open hips, prime hamstrings."},
                    {"name": "Ankle pogos", "sets": 2, "reps": "20s", "cat": "power", "note": "Stiff ankles, quick cycles."},
                ],
            },
            {
                "name": "Strength A",
                "items": [
                    {"name": "Goblet squat (DB 22.5kg / KB 24kg)", "sets": 5, "reps": "3–5", "cat": "strength", "note": "2–3 min rest. RPE 8–9."},
                    {"name": "Romanian deadlift (2×15kg)", "sets": 4, "reps": "5–6", "cat": "strength", "note": "Hinge hard. 2 min rest."},
                    {"name": "Standing calf raise (load as able)", "sets": 4, "reps": "8–10 @ 2-1-2", "cat": "accessory", "note": "Tempo: 2s up, 1s hold, 2s down."},
                ],
            },
            {
                "name": "Power",
                "items": [
                    {"name": "Box/step jumps (mid-shin)", "sets": 4, "reps": "3–4", "cat": "power", "note": "Full reset. Max intent."},
                    {"name": "KB swings (24kg)", "sets": 3, "reps": "8–10", "cat": "power", "note": "Explosive hips. 90s rest."},
                ],
            },
            {
                "name": "Core / Anti-extension",
                "items": [
                    {"name": "Ab wheel rollouts", "sets": 3, "reps": "6–10", "cat": "core", "note": "Tight ribs–pelvis."},
                    {"name": "Side plank", "sets": 3, "reps": "30–45s/side", "cat": "core", "note": "Long line, no sag."},
                ],
            },
            {
                "name": "Cooldown",
                "items": [
                    {"name": "Hamstring + hip flexor stretch", "sets": 1, "reps": "45–60s", "cat": "cooldown", "note": "Easy breathing."},
                ],
            },
        ],
    },
    "thursday": {
        "title": "Unilateral Strength + Elastic Power",
        "emoji": "🟢",
        "blocks": [
            {
                "name": "Warm-up",
                "items": [
                    {"name": "Light jog or rope", "sets": 1, "reps": "2–3 min", "cat": "warmup", "note": "Heat up joints."},
                    {"name": "Deep lunges + hip openers", "sets": 1, "reps": "8/leg + 8/side", "cat": "warmup", "note": "Find end range."},
                ],
            },
            {
                "name": "Strength B (unilateral)",
                "items": [
                    {"name": "Bulgarian split squat (15kg)", "sets": 4, "reps": "6/leg", "cat": "strength", "note": "2–3 min rest."},
                    {"name": "Single-leg RDL (12.5–15kg)", "sets": 3, "reps": "6/leg", "cat": "strength", "note": "Own the balance."},
                    {"name": "1-arm DB row (22.5kg)", "sets": 3, "reps": "6–8/arm", "cat": "strength", "note": "Stable torso."},
                ],
            },
            {
                "name": "Power / Elastic",
                "items": [
                    {"name": "Lateral bounds to stick", "sets": 3, "reps": "5–6/side", "cat": "power", "note": "Hold 2s on landing."},
                    {"name": "Jump-rope high-knee sprints", "sets": 4, "reps": "20–30s", "cat": "power", "note": "Pop off the ground."},
                ],
            },
            {
                "name": "Carries + Anti-rotation",
                "items": [
                    {"name": "Farmer carry heavy (KB 24kg + DB 22.5kg)", "sets": 3, "reps": "30–40m", "cat": "accessory", "note": "Tall. Don’t sway."},
                    {"name": "Suitcase carry (24kg)", "sets": 2, "reps": "20–30m/side", "cat": "accessory", "note": "Resist side-bend."},
                ],
            },
            {
                "name": "Core / Rotation",
                "items": [
                    {"name": "Russian twists (load light/mod)", "sets": 3, "reps": "10–12/side", "cat": "core", "note": "Rotate ribs, not elbows."},
                    {"name": "Bird-dog slow", "sets": 2, "reps": "8/side", "cat": "core", "note": "3s hold."},
                ],
            },
            {
                "name": "Cooldown",
                "items": [
                    {"name": "Calf + T-spine + hip flexor", "sets": 1, "reps": "45–60s/each", "cat": "cooldown", "note": "Downshift."},
                ],
            },
        ],
    },
}

# --------------------------
# Session state
# --------------------------
if "schema" not in st.session_state:
    st.session_state.schema = SCHEMA_VERSION
if "workout_data" not in st.session_state:
    st.session_state.workout_data = load_json(WORKOUT_DATA_FILE, {"_schema": SCHEMA_VERSION, "tuesday": {}, "thursday": {}})
if "history" not in st.session_state:
    st.session_state.history = load_json(WORKOUT_HISTORY_FILE, [])
if "selected_day" not in st.session_state:
    st.session_state.selected_day = "tuesday"
if "rest_timer_end" not in st.session_state:
    st.session_state.rest_timer_end = None

# --------------------------
# Data migration v1 -> v2
# --------------------------
# v2 stores per-set dict: {done:bool, weight:float|None, reps:int|str, rpe:float|None}

def migrate_to_v2(data):
    if isinstance(data, dict) and data.get("_schema") == SCHEMA_VERSION:
        return data

    migrated = {"_schema": SCHEMA_VERSION, "tuesday": {}, "thursday": {}}
    for day in ("tuesday", "thursday"):
        day_data = (data or {}).get(day, {})
        new_day = {}
        for ex_key, sets_map in day_data.items():
            new_day[ex_key] = {}
            for idx, val in sets_map.items():
                done = bool(val) if isinstance(val, (bool, int)) else False
                new_day[ex_key][str(idx)] = {"done": done, "weight": None, "reps": None, "rpe": None}
        migrated[day] = new_day
    return migrated

st.session_state.workout_data = migrate_to_v2(st.session_state.workout_data)

# --------------------------
# Helpers
# --------------------------

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


def ex_key_from(block_i, item_i):
    return f"b{block_i}_i{item_i}"


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
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number={'suffix': '%', 'font': {'size': 36}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'thickness': 0.28},
            'bgcolor': 'rgba(0,0,0,0)',
        }
    ))
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)


def start_rest(seconds=90):
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
            st.experimental_rerun()

# --------------------------
# Header
# --------------------------
st.markdown("""
<h1 class='main-title'>🏃‍♂️ 10K Speed – Strength</h1>
<p class='sub-title'>Mobile-optimised tracking for max strength, power, and elastic stiffness.</p>
""", unsafe_allow_html=True)

# --------------------------
# Tabs
# --------------------------
main_tab, analytics_tab, history_tab, settings_tab = st.tabs([
    "🏋️ Workout",
    "📊 Analytics",
    "📅 History",
    "⚙️ Settings",
])

# --------------------------
# Workout tab
# --------------------------
with main_tab:
    col_day, col_prog = st.columns([1,1])
    with col_day:
        day = st.segmented_control("Day", options=["tuesday", "thursday"], default=st.session_state.selected_day, format_func=lambda d: f"{WORKOUT_TEMPLATES[d]['emoji']} {d.title()}")
        st.session_state.selected_day = day
    with col_prog:
        done, total, pct = compute_progress(day)
        progress_ring(pct)
        st.caption(f"{done}/{total} sets complete")

    # Render blocks
    for b_i, block in enumerate(WORKOUT_TEMPLATES[day]["blocks"]):
        st.subheader(block["name"])  # simple, readable sectioning
        for i_i, it in enumerate(block["items"]):
            k = ex_key_from(b_i, i_i)
            # Determine completion
            sets_map = st.session_state.workout_data.get(day, {}).get(k, {})
            done_sets = sum(1 for s in range(it["sets"]) if sets_map.get(str(s), {}).get("done"))
            is_done = done_sets == it["sets"]

            # Card
            with st.container(border=True):
                st.markdown(
                    f"<div class='ex-card {'done' if is_done else ''}'>"
                    f"<div style='display:flex; align-items:center; justify-content:space-between;'>"
                    f"<div><strong>{'✅' if is_done else '⭕'} {it['name']}</strong>"
                    f"<span class='badge {it['cat']}'>{it['cat']}</span></div>"
                    f"<div style='font-size:12px; color:#64748b;'>{it['reps']}</div>"
                    f"</div>"
                    f"<div style='color:#64748b; margin:6px 0 10px 0;'>{it.get('note','')}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Set chips (tap to toggle) + per-set detail
                cols = st.columns(min(it["sets"], 6))
                for s in range(it["sets"]):
                    with cols[s % 6]:
                        slot = sets_map.get(str(s), {"done": False, "weight": None, "reps": None, "rpe": None})
                        label = f"Set {s+1}"
                        if st.button(f"{'✅' if slot['done'] else label}", key=f"{day}_{k}_{s}"):
                            set_done(day, k, s, not slot["done"])

                with st.expander("Log load / RPE (optional)"):
                    dcols = st.columns(3)
                    for s in range(it["sets"]):
                        slot = sets_map.get(str(s), {"done": False, "weight": None, "reps": None, "rpe": None})
                        with dcols[s % 3]:
                            w = st.number_input(f"Wgt (s{s+1})", min_value=0.0, value=float(slot["weight"]) if slot["weight"] is not None else 0.0, step=0.5, key=f"w_{day}_{k}_{s}")
                            set_set_detail(day, k, s, "weight", w if w>0 else None)
                            r = st.number_input(f"RPE (s{s+1})", min_value=0.0, max_value=10.0, value=float(slot["rpe"]) if slot["rpe"] is not None else 0.0, step=0.5, key=f"rpe_{day}_{k}_{s}")
                            set_set_detail(day, k, s, "rpe", r if r>0 else None)

                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Sticky actions
    with st.container():
        st.markdown("<div class='sticky-bar'>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([1,1,1,1])
        with c1:
            if st.button("🔄 Reset Day"):
                st.session_state.workout_data[day] = {}
                save_state()
                st.success("Reset – fresh start.")
        with c2:
            if st.button("⏱️ 90s Rest"):
                start_rest(90)
        with c3:
            if st.button("⏱️ 2m Rest"):
                start_rest(120)
        with c4:
            if st.button("✅ Save to History"):
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
                    }
                    st.session_state.history.append(entry)
                    save_json(WORKOUT_HISTORY_FILE, st.session_state.history)
                    # Clear the day after saving
                    st.session_state.workout_data[day] = {}
                    save_state()
                    st.success("Saved to history.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Rest timer feedback
    rest_widget()

# --------------------------
# Analytics tab
# --------------------------
with analytics_tab:
    st.subheader("Weekly Output")
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

        st.subheader("Completion % over Time")
        comp = df.sort_values("date")
        fig2 = go.Figure(go.Scatter(x=comp["date"], y=comp["completion_percentage"], mode="lines+markers"))
        fig2.update_layout(yaxis_title="Completion %", xaxis_title="Date")
        st.plotly_chart(fig2, use_container_width=True)

# --------------------------
# History tab
# --------------------------
with history_tab:
    st.subheader("Recent Workouts")
    if len(st.session_state.history) == 0:
        st.info("No history yet.")
    else:
        for item in sorted(st.session_state.history, key=lambda x: x["date"], reverse=True)[:20]:
            d = pd.to_datetime(item["date"]).strftime("%b %d, %Y – %H:%M")
            st.markdown(
                f"**{item['workout_name']}** ({item['day'].title()}) — {d}  "+
                f"Completion: {item['completed_sets']}/{item['total_sets']} ({item['completion_percentage']}%)"
            )
            with st.expander("Details"):
                st.json(item.get("data", {}))

# --------------------------
# Settings tab
# --------------------------
with settings_tab:
    st.subheader("Data")
    colA, colB = st.columns(2)
    with colA:
        if st.button("⬇️ Download History JSON"):
            st.download_button(
                label="Download history.json",
                data=json.dumps(st.session_state.history, indent=2),
                file_name="workout_history.json",
                mime="application/json",
            )
    with colB:
        if st.button("🗑️ Clear History"):
            st.session_state.history = []
            save_json(WORKOUT_HISTORY_FILE, [])
            st.success("History cleared.")

    st.divider()
    st.caption("Schema v2 – per-set weight & RPE logging. Mobile-first UI with large tap targets, sticky actions, and rest timer.")


    
