import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

DB_FILE = "builtwise.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def create_workout(name, notes):
    now = datetime.now().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO workouts (date, name, auto_start_time, notes)
        VALUES (?, ?, ?, ?)
    """, (now.split("T")[0], name, now, notes))
    conn.commit()
    conn.close()

def get_workouts():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM workouts ORDER BY date DESC", conn)
    conn.close()
    return df

def add_exercise(workout_id, name, order, is_superset, superset_group):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO exercises (workout_id, name, "order", is_superset, superset_group)
        VALUES (?, ?, ?, ?, ?)
    """, (workout_id, name, order, is_superset, superset_group))
    conn.commit()
    conn.close()

def get_exercises(workout_id):
    conn = get_connection()
    df = pd.read_sql(f"""
        SELECT * FROM exercises WHERE workout_id = {workout_id} ORDER BY "order"
    """, conn)
    conn.close()
    return df

def log_set(exercise_id, set_number, weight, reps, notes):
    timestamp = datetime.now().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sets (exercise_id, set_number, weight, reps, timestamp, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (exercise_id, set_number, weight, reps, timestamp, notes))
    conn.commit()
    conn.close()

def get_sets(exercise_id):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM sets WHERE exercise_id = {exercise_id}", conn)
    conn.close()
    return df

# --- Streamlit App UI ---

st.title("🏋️ BuiltWise")

tab1, tab2, tab3 = st.tabs(["📅 New Workout", "📝 Log Sets", "📊 History"])

with tab1:
    st.header("Start a New Workout")
    workout_name = st.text_input("Workout Name")
    notes = st.text_area("Notes (optional)")
    if st.button("Start Workout"):
        create_workout(workout_name, notes)
        st.success("Workout created!")

with tab2:
    st.header("Log Sets")
    workouts = get_workouts()
    workout_options = workouts["name"] + " (" + workouts["date"] + ")"
    selected = st.selectbox("Select a workout", workout_options)
    if selected:
        selected_id = workouts.loc[workout_options == selected, "id"].values[0]
        exercises = get_exercises(selected_id)

        if st.checkbox("Add new exercise"):
            new_ex_name = st.text_input("Exercise Name")
            new_order = st.number_input("Order", min_value=1, step=1)
            is_superset = st.checkbox("Is this part of a superset?")
            superset_group = st.text_input("Superset Group (optional)")
            if st.button("Add Exercise"):
                add_exercise(selected_id, new_ex_name, new_order, is_superset, superset_group)
                st.experimental_rerun()

        for _, row in exercises.iterrows():
            with st.expander(f"Exercise: {row['name']}"):
                st.write("Superset:", "Yes" if row['is_superset'] else "No")
                st.write("Group:", row['superset_group'])
                set_number = st.number_input(f"Set Number for {row['name']}", min_value=1, step=1, key=f"setnum_{row['id']}")
                weight = st.number_input("Weight", min_value=0.0, step=0.5, key=f"weight_{row['id']}")
                reps = st.number_input("Reps", min_value=1, step=1, key=f"reps_{row['id']}")
                notes = st.text_input("Notes (optional)", key=f"note_{row['id']}")
                if st.button(f"Log Set for {row['name']}", key=f"log_{row['id']}"):
                    log_set(row['id'], set_number, weight, reps, notes)
                    st.success("Set logged!")

with tab3:
    st.header("Workout History")
    all_workouts = get_workouts()
    selected_history = st.selectbox("Choose a past workout", all_workouts["name"] + " (" + all_workouts["date"] + ")", key="history")
    if selected_history:
        workout_id = all_workouts.loc[all_workouts["name"] + " (" + all_workouts["date"] + ")" == selected_history, "id"].values[0]
        exercises = get_exercises(workout_id)
        for _, row in exercises.iterrows():
            sets = get_sets(row['id'])
            with st.expander(f"{row['name']} - {len(sets)} sets logged"):
                st.dataframe(sets[["set_number", "weight", "reps", "timestamp", "notes"]])

