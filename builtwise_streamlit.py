import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- CONFIG ---
SHEET_NAME = 'BuiltWise'
WORKOUTS_TAB = 'Workouts'
EXERCISES_TAB = 'Exercises'
SETS_TAB = 'Sets'
CREDENTIALS_FILE = 'builtwise-credentials.json'  # Your renamed JSON key file

# --- CONNECT TO GOOGLE SHEET ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = st.secrets["google_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
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

tab1, tab2, tab3, tab4 = st.tabs(["📅 Dashboard", "📝 Log Sets", "📊 Progress Tracker", "📚 Exercise Library"])

# --- Tab 1: Dashboard ---
with tab1:
    st.header("Dashboard")
    workouts_df = load_data(WORKOUTS_TAB)
    sets_df = load_data(SETS_TAB)

    # Show the most recent workout summary
    most_recent_workout = workouts_df.sort_values("Date", ascending=False).iloc[0]
    st.subheader(f"Most Recent Workout - {most_recent_workout['Workout Name']} on {most_recent_workout['Date']}")
    
    total_volume = sets_df[sets_df['Workout ID'] == most_recent_workout['Workout ID']]['Total Volume'].sum()
    st.write(f"**Total Volume:** {total_volume} lbs")
    
    # Display Progress (bar chart for weight over time)
    sets_df['Timestamp'] = pd.to_datetime(sets_df['Timestamp'])
    progress_data = sets_df.groupby('Timestamp').agg({'Weight': 'max'}).reset_index()
    
    st.subheader("Progress Over Time")
    st.plotly_chart(px.line(progress_data, x='Timestamp', y='Weight', title="Max Weight Over Time"))

# --- Tab 2: Log Sets ---
with tab2:
    st.header("Log Sets")
    exercises_df = load_data(EXERCISES_TAB)
    workouts_df = load_data(WORKOUTS_TAB)
    
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
    filtered_exercises = exercises_df[exercises_df["Workout ID"] == workout_id]
    selected_exercise = st.selectbox("Select Exercise", filtered_exercises["Exercise Name"])
    selected_ex = filtered_exercises[filtered_exercises["Exercise Name"] == selected_exercise].iloc[0]
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

# --- Tab 3: Progress Tracker ---
with tab3:
    st.header("Progress Tracker")
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
        st.plotly_chart(px.line(df_filtered, x='Timestamp', y='Weight', title="Weight Over Time"))

        st.subheader("🔁 Reps Over Time")
        st.plotly_chart(px.line(df_filtered, x='Timestamp', y='Reps', title="Reps Over Time"))

        st.subheader("🏆 Personal Records")
        max_weight = df_filtered["Weight"].max()
        max_reps = df_filtered["Reps"].max()
        st.metric("Max Weight", f"{max_weight} lbs")
        st.metric("Max Reps", f"{max_reps} reps")
    else:
        st.info("Log some sets to see stats.")

# --- Tab 4: Exercise Library ---
with tab4:
    st.header("Exercise Library")
    exercises_df = load_data(EXERCISES_TAB)
    
    search_term = st.text_input("Search for an exercise")
    filtered_exercises = exercises_df[exercises_df["Exercise Name"].str.contains(search_term, case=False, na=False)]
    
    st.dataframe(filtered_exercises[["Exercise Name", "Category", "Order"]])

    st.subheader("Add New Exercise")
    new_exercise_name = st.text_input("Exercise Name (New)")
    new_exercise_category = st.text_input("Category (e.g., Chest, Legs, etc.)")
    if st.button("Add Exercise"):
        new_exercise_id = f"ex_{int(datetime.now().timestamp())}"
        append_row(EXERCISES_TAB, [new_exercise_id, "", new_exercise_name, 1, 0, new_exercise_category])
        st.success(f"Exercise '{new_exercise_name}' added.")

