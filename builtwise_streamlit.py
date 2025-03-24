import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- CONFIG ---
SHEET_NAME = 'BuiltWise'
WORKOUTS_TAB = 'Workouts'
EXERCISES_TAB = 'Exercises'
SETS_TAB = 'Sets'
CREDENTIALS_FILE = 'builtwise-credentials.json'  # Your renamed JSON key file

# --- CONNECT TO GOOGLE SHEET ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME)

# Helper to load tab as DataFrame
def load_data(tab):
    return pd.DataFrame(sheet.worksheet(tab).get_all_records())

# Helper to append row
def append_row(tab, row):
    sheet.worksheet(tab).append_row(row)

# --- Streamlit UI ---
st.set_page_config(page_title="BuiltWise", layout="wide")
st.title("🏋️ BuiltWise – Cloud-Connected Workout Logger")

tab1, tab2, tab3 = st.tabs(["📅 New Workout", "📝 Log Sets", "📊 View Stats"])

# --- Tab 1: New Workout ---
with tab1:
    st.header("Start a New Workout")
    workout_name = st.text_input("Workout Name")
    notes = st.text_area("Notes")
    if st.button("Start Workout"):
        workout_id = f"wo_{int(datetime.now().timestamp())}"
        date = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().isoformat()
        append_row(WORKOUTS_TAB, [workout_id, date, workout_name, now, "", "", "", notes])
        st.success(f"Workout '{workout_name}' started!")

# --- Tab 2: Log Sets ---
with tab2:
    st.header("Log Sets")
    workouts_df = load_data(WORKOUTS_TAB)
    if len(workouts_df) == 0:
        st.info("Start a workout first.")
    else:
        selected_workout = st.selectbox("Select Workout", workouts_df["Workout Name"] + " (" + workouts_df["Date"] + ")")
        workout_row = workouts_df[workouts_df["Workout Name"] + " (" + workouts_df["Date"] + ")" == selected_workout].iloc[0]
        workout_id = workout_row["Workout ID"]

        st.subheader("Add Exercise")
        exercise_name = st.text_input("Exercise Name")
        order = st.number_input("Order", min_value=1, step=1)
        is_superset = st.checkbox("Is part of a superset?")
        superset_group = st.text_input("Superset Group (optional)")
        if st.button("Add Exercise"):
            exercise_id = f"ex_{int(datetime.now().timestamp())}"
            append_row(EXERCISES_TAB, [exercise_id, workout_id, exercise_name, order, int(is_superset), superset_group])
            st.success(f"Exercise '{exercise_name}' added.")

        st.subheader("Log a Set")
        exercises_df = load_data(EXERCISES_TAB)
        if len(exercises_df) > 0:
            filtered = exercises_df[exercises_df["Workout ID"] == workout_id]
            ex = st.selectbox("Select Exercise", filtered["Exercise Name"])
            selected_ex = filtered[filtered["Exercise Name"] == ex].iloc[0]
            exercise_id = selected_ex["Exercise ID"]
            set_number = st.number_input("Set #", min_value=1, step=1)
            weight = st.number_input("Weight", min_value=0.0, step=0.5)
            reps = st.number_input("Reps", min_value=1, step=1)
            notes = st.text_input("Set Notes")
            if st.button("Log Set"):
                set_id = f"set_{int(datetime.now().timestamp())}"
                timestamp = datetime.now().isoformat()
                append_row(SETS_TAB, [set_id, exercise_id, set_number, weight, reps, timestamp, notes])
                st.success("Set logged!")

# --- Tab 3: View Stats ---
with tab3:
    st.header("📊 Stats Viewer")
    sets_df = load_data(SETS_TAB)
    exercises_df = load_data(EXERCISES_TAB)
    if len(sets_df) > 0 and len(exercises_df) > 0:
        merged = sets_df.merge(exercises_df, left_on="Exercise ID", right_on="Exercise ID")
        all_ex_names = merged["Exercise Name"].unique()
        ex_selected = st.selectbox("Choose Exercise to View", all_ex_names)

        df_filtered = merged[merged["Exercise Name"] == ex_selected]
        df_filtered["Timestamp"] = pd.to_datetime(df_filtered["Timestamp"])
        df_filtered = df_filtered.sort_values("Timestamp")

        st.subheader(f"📅 History for {ex_selected}")
        st.dataframe(df_filtered[["Set Number", "Weight", "Reps", "Timestamp", "Notes"]])

        st.subheader("📈 Weight Over Time")
        st.line_chart(df_filtered.set_index("Timestamp")[["Weight"]])

        st.subheader("🔁 Reps Over Time")
        st.line_chart(df_filtered.set_index("Timestamp")[["Reps"]])

        st.subheader("🏆 Personal Records")
        max_weight = df_filtered["Weight"].max()
        max_reps = df_filtered["Reps"].max()
        st.metric("Max Weight", f"{max_weight} lbs")
        st.metric("Max Reps", f"{max_reps} reps")
    else:
        st.info("Log some sets to see stats.")
