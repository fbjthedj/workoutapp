import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os

# Page configuration
st.set_page_config(
    page_title="Workout Tracker",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 2rem;
    }
    
    .workout-card {
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    
    .workout-card-completed {
        background: #f0fdf4;
        border-color: #bbf7d0;
    }
    
    .exercise-header {
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    
    .exercise-details {
        color: #6b7280;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    
    .category-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    
    .warm-up { background: #fed7aa; color: #9a3412; }
    .strength { background: #fecaca; color: #991b1b; }
    .power { background: #e9d5ff; color: #7c2d92; }
    .accessory { background: #bfdbfe; color: #1e40af; }
    .cooldown { background: #bbf7d0; color: #166534; }
    
    .progress-container {
        background: #f1f5f9;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        text-align: center;
    }
    
    .completion-message {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        margin: 2rem 0;
    }
    
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .workout-history-item {
        background: white;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# File paths for data persistence
WORKOUT_DATA_FILE = "workout_data.json"
WORKOUT_HISTORY_FILE = "workout_history.json"

# Initialize session state
if 'workout_data' not in st.session_state:
    st.session_state.workout_data = {
        'tuesday': {},
        'thursday': {}
    }

if 'selected_day' not in st.session_state:
    st.session_state.selected_day = 'tuesday'

if 'workout_history' not in st.session_state:
    st.session_state.workout_history = []

# Load data functions
@st.cache_data
def load_workout_history():
    if os.path.exists(WORKOUT_HISTORY_FILE):
        try:
            with open(WORKOUT_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_workout_history(history):
    try:
        with open(WORKOUT_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        st.error(f"Could not save workout history: {e}")

def load_current_workout_data():
    if os.path.exists(WORKOUT_DATA_FILE):
        try:
            with open(WORKOUT_DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'tuesday': {}, 'thursday': {}}
    return {'tuesday': {}, 'thursday': {}}

def save_current_workout_data(data):
    try:
        with open(WORKOUT_DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Could not save workout data: {e}")

# Load data on startup
if not st.session_state.workout_history:
    st.session_state.workout_history = load_workout_history()

if not any(st.session_state.workout_data.values()):
    st.session_state.workout_data = load_current_workout_data()

# Workout data
workouts = {
    'tuesday': {
        'title': "Full-body Strength & Power",
        'day': "Tuesday",
        'color': "🔵",
        'exercises': [
            {
                'id': 1,
                'name': "Jump-rope warm-up (1/4-lb rope)",
                'sets': 1,
                'reps': "3 min",
                'notes': "Light, quick foot contacts",
                'category': "warm-up"
            },
            {
                'id': 2,
                'name': "Leg swings",
                'sets': 1,
                'reps': "10 each",
                'notes': "Dynamic leg swings forward/back and side to side",
                'category': "warm-up"
            },
            {
                'id': 3,
                'name': "Lunges",
                'sets': 1,
                'reps': "10 each",
                'notes': "Dynamic walking lunges or reverse lunges",
                'category': "warm-up"
            },
            {
                'id': 4,
                'name': "Kettlebell halos (12 kg)",
                'sets': 1,
                'reps': "10 each",
                'notes': "Slow controlled circles around head",
                'category': "warm-up"
            },
            {
                'id': 5,
                'name': "Goblet squats (dumbbell 22.5 kg or KB 24 kg)",
                'sets': 4,
                'reps': "8",
                'notes': "Heavy strength; 2 min rest",
                'category': "strength"
            },
            {
                'id': 6,
                'name': "Romanian deadlifts (two 15 kg DBs)",
                'sets': 4,
                'reps': "8",
                'notes': "Neutral spine, hinge at hips",
                'category': "strength"
            },
            {
                'id': 7,
                'name': "Single-arm DB push press",
                'sets': 4,
                'reps': "8",
                'notes': "Alternate arms, explosive drive",
                'category': "strength"
            },
            {
                'id': 8,
                'name': "Kettlebell swings (24 kg)",
                'sets': 3,
                'reps': "12",
                'notes': "Power; 90 s rest",
                'category': "power"
            },
            {
                'id': 9,
                'name': "Jump-rope double-unders / high-speed singles",
                'sets': 3,
                'reps': "30 s",
                'notes': "Use heavier ½-lb rope",
                'category': "power"
            },
            {
                'id': 10,
                'name': "Box/step jumps",
                'sets': 3,
                'reps': "6",
                'notes': "Mid-shin height, soft landings",
                'category': "power"
            },
            {
                'id': 11,
                'name': "Bent-over row (12.5 kg DBs)",
                'sets': 3,
                'reps': "12",
                'notes': "Control movement",
                'category': "strength"
            },
            {
                'id': 12,
                'name': "Single-leg glute bridge",
                'sets': 3,
                'reps': "12",
                'notes': "Focus on hip drive",
                'category': "core"
            },
            {
                'id': 13,
                'name': "Ab-roller roll-outs",
                'sets': 3,
                'reps': "8",
                'notes': "Keep core tight",
                'category': "core"
            },
            {
                'id': 14,
                'name': "Plank with shoulder taps",
                'sets': 3,
                'reps': "20 taps",
                'notes': "Stability-focused",
                'category': "accessory"
            },
            {
                'id': 15,
                'name': "Hamstring stretch",
                'sets': 1,
                'reps': "30-45 sec each",
                'notes': "Standing forward fold or seated reach",
                'category': "cooldown"
            },
            {
                'id': 16,
                'name': "Quad stretch",
                'sets': 1,
                'reps': "30-45 sec each",
                'notes': "Standing quad pull or couch stretch",
                'category': "cooldown"
            },
            {
                'id': 17,
                'name': "Hip flexor stretch",
                'sets': 1,
                'reps': "30-45 sec each",
                'notes': "Low lunge or 90/90 hip stretch",
                'category': "cooldown"
            },
            {
                'id': 18,
                'name': "Goblet March",
                'sets': 3,
                'reps': "30-60 sec",
                'notes': "Hold KB at chest, drive knees up, maintain posture",
                'category': "accessory"
            },
            {
                'id': 19,
                'name': "Single Arm Rack March or Carry",
                'sets': 3,
                'reps': "30-60 sec each side",
                'notes': "Stabilize through the torso, keep KB upright",
                'category': "accessory"
            },
            {
                'id': 20,
                'name': "Single Arm Overhead March",
                'sets': 3,
                'reps': "30-45 sec each side",
                'notes': "If shoulder mobility allows; strict overhead control",
                'category': "accessory"
            },
            {
                'id': 21,
                'name': "Kettlebell Oblique Side Bends",
                'sets': 3,
                'reps': "10 each side",
                'notes': "Deep side bend, then strong contraction on the way up",
                'category': "accessory"
            },
            {
                'id': 22,
                'name': "Reverse Crunches (Kettlebell Anchor)",
                'sets': 3,
                'reps': "10",
                'notes': "Slow tempo, roll up from spine, core-controlled",
                'category': "accessory"
            },
            {
                'id': 23,
                'name': "Russian Twists (with KB)",
                'sets': 3,
                'reps': "20 total reps (slow)",
                'notes': "Focus on upper-body rotation, controlled movement",
                'category': "accessory"
            }
        ]
    },
    'thursday': {
        'title': "Unilateral Strength & Stability",
        'day': "Thursday",
        'color': "🟢",
        'exercises': [
            {
                'id': 1,
                'name': "Jump-rope warm-up / light jog",
                'sets': 1,
                'reps': "3 min",
                'notes': "Prepare joints and heart rate",
                'category': "warm-up"
            },
            {
                'id': 2,
                'name': "Deep lunges",
                'sets': 1,
                'reps': "8 each",
                'notes': "Deep static lunges with hip opener focus",
                'category': "warm-up"
            },
            {
                'id': 3,
                'name': "Hip openers",
                'sets': 1,
                'reps': "8 each",
                'notes': "Dynamic hip circles and 90/90 transitions",
                'category': "warm-up"
            },
            {
                'id': 4,
                'name': "Inchworms",
                'sets': 1,
                'reps': "8",
                'notes': "Walk hands out to plank, walk back up",
                'category': "warm-up"
            },
            {
                'id': 5,
                'name': "Bulgarian split squat (15 kg DB)",
                'sets': 4,
                'reps': "8",
                'notes': "Each leg; goblet position",
                'category': "strength"
            },
            {
                'id': 6,
                'name': "Single-arm DB row (22.5 kg)",
                'sets': 4,
                'reps': "8",
                'notes': "Support with opposite hand",
                'category': "strength"
            },
            {
                'id': 7,
                'name': "Floor or KB chest press (12 kg KBs)",
                'sets': 4,
                'reps': "8",
                'notes': "Control the lowering phase",
                'category': "strength"
            },
            {
                'id': 8,
                'name': "Kettlebell clean & push press",
                'sets': 3,
                'reps': "8",
                'notes': "Moderate weight; alternate arms",
                'category': "power"
            },
            {
                'id': 9,
                'name': "Lateral bounds to single-leg hold",
                'sets': 3,
                'reps': "8",
                'notes': "Hold landing 2 s each bound",
                'category': "power"
            },
            {
                'id': 10,
                'name': "Jump-rope high-knee sprints",
                'sets': 3,
                'reps': "30 s",
                'notes': "Emphasise knee lift",
                'category': "power"
            },
            {
                'id': 11,
                'name': "Russian twist (12.5 kg DB)",
                'sets': 3,
                'reps': "12",
                'notes': "Rotational core strength",
                'category': "accessory"
            },
            {
                'id': 12,
                'name': "Suitcase carry (24 kg KB)",
                'sets': 3,
                'reps': "20 m",
                'notes': "Carry per side; stay upright",
                'category': "accessory"
            },
            {
                'id': 13,
                'name': "Bird-dog",
                'sets': 3,
                'reps': "10/side",
                'notes': "Slow, controlled",
                'category': "accessory"
            },
            {
                'id': 14,
                'name': "Hamstring stretch",
                'sets': 1,
                'reps': "45-60 sec each",
                'notes': "Standing forward fold or seated reach",
                'category': "cooldown"
            },
            {
                'id': 15,
                'name': "Calf stretch",
                'sets': 1,
                'reps': "45-60 sec each",
                'notes': "Wall push or downward dog focus",
                'category': "cooldown"
            },
            {
                'id': 16,
                'name': "Hip flexor stretch",
                'sets': 1,
                'reps': "45-60 sec each",
                'notes': "Low lunge or couch stretch",
                'category': "cooldown"
            },
            {
                'id': 17,
                'name': "Thoracic spine stretch",
                'sets': 1,
                'reps': "45-60 sec",
                'notes': "Cat-cow or thoracic extension over foam roller",
                'category': "cooldown"
            }
        ]
    }
}

def get_category_class(category):
    return category.replace('-', '')

def calculate_progress(day):
    current_workout = workouts[day]
    total_sets = sum(exercise['sets'] for exercise in current_workout['exercises'])
    
    completed_sets = 0
    for exercise_id, sets_data in st.session_state.workout_data[day].items():
        if isinstance(sets_data, dict):
            completed_sets += sum(1 for completed in sets_data.values() if completed)
    
    return completed_sets, total_sets

def toggle_set(day, exercise_id, set_index):
    if day not in st.session_state.workout_data:
        st.session_state.workout_data[day] = {}
    if exercise_id not in st.session_state.workout_data[day]:
        st.session_state.workout_data[day][exercise_id] = {}
    
    current_state = st.session_state.workout_data[day][exercise_id].get(set_index, False)
    st.session_state.workout_data[day][exercise_id][set_index] = not current_state
    
    # Save current workout data
    save_current_workout_data(st.session_state.workout_data)

def reset_workout(day):
    st.session_state.workout_data[day] = {}
    save_current_workout_data(st.session_state.workout_data)

def is_set_completed(day, exercise_id, set_index):
    return st.session_state.workout_data[day].get(exercise_id, {}).get(set_index, False)

def get_exercise_completed_sets(day, exercise_id):
    exercise_sets = st.session_state.workout_data[day].get(exercise_id, {})
    return sum(1 for completed in exercise_sets.values() if completed)

def complete_workout(day):
    """Save completed workout to history and reset current workout"""
    completed_sets, total_sets = calculate_progress(day)
    
    if completed_sets == total_sets and total_sets > 0:
        workout_entry = {
            'date': datetime.now().isoformat(),
            'day': day,
            'workout_name': workouts[day]['title'],
            'completed_sets': completed_sets,
            'total_sets': total_sets,
            'completion_percentage': 100.0,
            'exercises_completed': {}
        }
        
        # Record individual exercise completion
        for exercise in workouts[day]['exercises']:
            exercise_id = exercise['id']
            completed = get_exercise_completed_sets(day, exercise_id)
            workout_entry['exercises_completed'][exercise['name']] = {
                'completed_sets': completed,
                'total_sets': exercise['sets'],
                'completion_percentage': (completed / exercise['sets']) * 100
            }
        
        st.session_state.workout_history.append(workout_entry)
        save_workout_history(st.session_state.workout_history)
        
        # Reset the current workout
        reset_workout(day)
        
        return True
    return False

def show_progress_analytics():
    """Display workout history and analytics"""
    st.markdown("## 📊 Progress Analytics")
    
    if not st.session_state.workout_history:
        st.info("Complete some workouts to see your progress analytics!")
        return
    
    # Convert history to DataFrame for analysis
    df_history = pd.DataFrame(st.session_state.workout_history)
    df_history['date'] = pd.to_datetime(df_history['date'])
    df_history['week'] = df_history['date'].dt.isocalendar().week
    df_history['month'] = df_history['date'].dt.to_period('M')
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🏋️ Total Workouts</h3>
            <h2>{}</h2>
        </div>
        """.format(len(df_history)), unsafe_allow_html=True)
    
    with col2:
        total_sets = df_history['completed_sets'].sum()
        st.markdown("""
        <div class="metric-card">
            <h3>💪 Total Sets</h3>
            <h2>{}</h2>
        </div>
        """.format(total_sets), unsafe_allow_html=True)
    
    with col3:
        avg_completion = df_history['completion_percentage'].mean()
        st.markdown("""
        <div class="metric-card">
            <h3>📈 Avg Completion</h3>
            <h2>{:.1f}%</h2>
        </div>
        """.format(avg_completion), unsafe_allow_html=True)
    
    with col4:
        streak = calculate_current_streak()
        st.markdown("""
        <div class="metric-card">
            <h3>🔥 Current Streak</h3>
            <h2>{} days</h2>
        </div>
        """.format(streak), unsafe_allow_html=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Workout frequency over time
        weekly_counts = df_history.groupby(['week', 'day']).size().reset_index(name='count')
        fig_freq = px.bar(weekly_counts, x='week', y='count', color='day',
                         title="Weekly Workout Frequency",
                         labels={'week': 'Week Number', 'count': 'Workouts Completed'})
        st.plotly_chart(fig_freq, use_container_width=True)
    
    with col2:
        # Completion percentage over time
        fig_completion = px.line(df_history, x='date', y='completion_percentage', color='day',
                               title="Workout Completion % Over Time",
                               labels={'completion_percentage': 'Completion %'})
        st.plotly_chart(fig_completion, use_container_width=True)
    
    # Exercise-specific progress
    st.markdown("### 🎯 Exercise-Specific Progress")
    
    # Get all unique exercise names
    all_exercises = set()
    for workout in st.session_state.workout_history:
        all_exercises.update(workout.get('exercises_completed', {}).keys())
    
    selected_exercise = st.selectbox("Select Exercise to Analyze", sorted(all_exercises))
    
    if selected_exercise:
        exercise_data = []
        for workout in st.session_state.workout_history:
            if selected_exercise in workout.get('exercises_completed', {}):
                exercise_info = workout['exercises_completed'][selected_exercise]
                exercise_data.append({
                    'date': pd.to_datetime(workout['date']),
                    'completed_sets': exercise_info['completed_sets'],
                    'total_sets': exercise_info['total_sets'],
                    'completion_percentage': exercise_info['completion_percentage']
                })
        
        if exercise_data:
            df_exercise = pd.DataFrame(exercise_data)
            
            fig_exercise = go.Figure()
            fig_exercise.add_trace(go.Scatter(
                x=df_exercise['date'],
                y=df_exercise['completed_sets'],
                mode='lines+markers',
                name='Sets Completed',
                line=dict(color='#10b981', width=3)
            ))
            
            fig_exercise.update_layout(
                title=f"Progress: {selected_exercise}",
                xaxis_title="Date",
                yaxis_title="Sets Completed",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_exercise, use_container_width=True)

def calculate_current_streak():
    """Calculate current consecutive workout streak"""
    if not st.session_state.workout_history:
        return 0
    
    # Sort by date (most recent first)
    sorted_history = sorted(st.session_state.workout_history, 
                          key=lambda x: x['date'], reverse=True)
    
    streak = 0
    current_date = datetime.now().date()
    
    for workout in sorted_history:
        workout_date = pd.to_datetime(workout['date']).date()
        days_diff = (current_date - workout_date).days
        
        if days_diff <= 2:  # Within 2 days counts as maintaining streak
            streak += 1
            current_date = workout_date
        else:
            break
    
    return streak

def show_workout_history():
    """Display workout history log"""
    st.markdown("## 📅 Workout History")
    
    if not st.session_state.workout_history:
        st.info("No workout history yet! Complete some workouts to see them here.")
        return
    
    # Sort by date (most recent first)
    sorted_history = sorted(st.session_state.workout_history, 
                          key=lambda x: x['date'], reverse=True)
    
    for i, workout in enumerate(sorted_history[:20]):  # Show last 20 workouts
        workout_date = pd.to_datetime(workout['date'])
        
        st.markdown(f"""
        <div class="workout-history-item">
            <h4>{workouts[workout['day']]['color']} {workout['workout_name']}</h4>
            <p><strong>Date:</strong> {workout_date.strftime('%B %d, %Y at %I:%M %p')}</p>
            <p><strong>Completion:</strong> {workout['completed_sets']}/{workout['total_sets']} sets ({workout['completion_percentage']:.1f}%)</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show exercise breakdown in expander
        with st.expander(f"Exercise Details - {workout_date.strftime('%m/%d/%Y')}"):
            for exercise_name, details in workout.get('exercises_completed', {}).items():
                completion_pct = details['completion_percentage']
                color = "🟢" if completion_pct == 100 else "🟡" if completion_pct >= 50 else "🔴"
                st.write(f"{color} **{exercise_name}**: {details['completed_sets']}/{details['total_sets']} sets ({completion_pct:.1f}%)")

# Sidebar navigation
with st.sidebar:
    st.markdown("## 🎯 Navigation")
    page = st.radio("Choose Page", ["🏋️ Current Workout", "📊 Progress Analytics", "📅 Workout History"])

# Main app content based on page selection
if page == "🏋️ Current Workout":
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>💪 Workout Tracker</h1>
        <p>Track your sets and get ripped!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Day selector
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        selected_day = st.selectbox(
            "Select Workout Day",
            options=['tuesday', 'thursday'],
            format_func=lambda x: f"{workouts[x]['color']} {workouts[x]['day']} - {workouts[x]['title']}",
            index=0 if st.session_state.selected_day == 'tuesday' else 1,
            key='day_selector'
        )
        st.session_state.selected_day = selected_day
    
    current_workout = workouts[selected_day]
    completed_sets, total_sets = calculate_progress(selected_day)
    progress_percentage = (completed_sets / total_sets) * 100 if total_sets > 0 else 0
    
    # Progress section
    st.markdown(f"""
    <div class="progress-container">
        <h3>{current_workout['color']} {current_workout['title']}</h3>
        <p><strong>{completed_sets}</strong> of <strong>{total_sets}</strong> sets completed</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Progress bar and buttons
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.progress(progress_percentage / 100)
        st.write(f"{progress_percentage:.0f}% complete")
    with col2:
        if st.button("🔄 Reset", help="Reset all sets for this workout"):
            reset_workout(selected_day)
            st.success("Workout reset!")
    with col3:
        if completed_sets == total_sets and total_sets > 0:
            if st.button("✅ Complete", help="Save workout to history"):
                if complete_workout(selected_day):
                    st.success("Workout saved to history!")
    
    # Completion message
    if completed_sets == total_sets and total_sets > 0:
        st.markdown(f"""
        <div class="completion-message">
            <h2>🎉 Workout Complete!</h2>
            <p>Great job finishing your {current_workout['day']} session!</p>
            <p>Completed {completed_sets} sets total</p>
            <p>Click "Complete" to save this workout to your history!</p>
        </div>
        """, unsafe_allow_html=True)
        st.balloons()
    
    # Exercise list
    st.markdown("---")
    
    for exercise in current_workout['exercises']:
        exercise_id = exercise['id']
        completed_sets_for_exercise = get_exercise_completed_sets(selected_day, exercise_id)
        is_complete = completed_sets_for_exercise == exercise['sets']
        
        # Exercise card
        card_class = "workout-card-completed" if is_complete else "workout-card"
        
        with st.container():
            st.markdown(f"""
            <div class="{card_class}">
                <div class="exercise-header">
                    {'✅' if is_complete else '⭕'} {exercise['name']}
                    <span class="category-badge {get_category_class(exercise['category'])}">{exercise['category']}</span>
                </div>
                <div class="exercise-details">
                    <strong>{exercise['sets']} sets × {exercise['reps']} reps</strong><br>
                    {exercise['notes']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Progress for this exercise
            exercise_progress = (completed_sets_for_exercise / exercise['sets']) * 100 if exercise['sets'] > 0 else 0
            st.progress(exercise_progress / 100)
            st.write(f"{completed_sets_for_exercise}/{exercise['sets']} sets complete")
            
            # Set buttons
            cols = st.columns(min(exercise['sets'], 6))  # Max 6 columns to prevent overflow
            
            for set_index in range(exercise['sets']):
                col_index = set_index % 6  # Wrap to next row if more than 6 sets
                if set_index >= 6 and set_index % 6 == 0:
                    cols = st.columns(min(exercise['sets'] - set_index, 6))
                
                with cols[col_index]:
                    is_completed = is_set_completed(selected_day, exercise_id, set_index)
                    button_text = "✅" if is_completed else f"Set {set_index + 1}"
                    button_type = "secondary" if is_completed else "primary"
                    
                    if st.button(
                        button_text,
                        key=f"{selected_day}_{exercise_id}_{set_index}",
                        type=button_type,
                        use_container_width=True
                    ):
                        toggle_set(selected_day, exercise_id, set_index)
            
            st.markdown("---")

elif page == "📊 Progress Analytics":
    show_progress_analytics()

elif page == "📅 Workout History":
    show_workout_history()

    
