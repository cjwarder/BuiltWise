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
SUPERSETS_TAB = 'Supersets'

# --- CONNECT TO GOOGLE SHEET ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = st.secrets["google_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME)

# --- HELPERS ---
def load_data(tab):
    return pd.DataFrame(sheet.worksheet(tab).get_all_records())

def append_row(tab, row):
    sheet.worksheet(tab).append_row(row)

# --- STREAMLIT SETUP ---
st.set_page_config(page_title="BuiltWise", layout="wide")
st.title("🏋️ BuiltWise – Cloud-Connected Workout Logger")

tab1, tab2, tab3, tab4 = st.tabs(["📅 Dashboard", "📝 Log Sets", "📊 Progress Tracker", "📚 Exercise Library"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("Dashboard", divider="gray")
    workouts_df = load_data(WORKOUTS_TAB)
    sets_df = load_data(SETS_TAB)

    if not workouts_df.empty:
        most_recent_workout = workouts_df.sort_values("Date", ascending=False).iloc[0]
        st.subheader(f"Most Recent Workout – {most_recent_workout['Workout Name']} ({most_recent_workout['Date']})")

        if 'Workout ID' in sets_df.columns and 'Total Volume' in sets_df.columns:
            recent_sets = sets_df[sets_df['Workout ID'] == most_recent_workout['Workout ID']]
            total_volume = recent_sets['Total Volume'].sum()
            st.metric("Total Volume", f"{total_volume:.0f} lbs")
        else:
            st.warning("Missing 'Workout ID' or 'Total Volume' in Sets data.")

        if 'Timestamp' in sets_df.columns and 'Weight' in sets_df.columns:
            sets_df['Timestamp'] = pd.to_datetime(sets_df['Timestamp'], errors='coerce')
            progress_data = sets_df.dropna(subset=['Timestamp'])
            if not progress_data.empty:
                grouped = progress_data.groupby('Timestamp')['Weight'].max().reset_index()
                st.plotly_chart(px.line(grouped, x='Timestamp', y='Weight', title="Max Weight Over Time"))
            else:
                st.info("No timestamped sets available to plot.")
    else:
        st.info("No workouts found.")

# --- TAB 2: LOG SETS ---
with tab2:
    st.header("Log Sets", divider="gray")
    exercises_df = load_data(EXERCISES_TAB)
    workouts_df = load_data(WORKOUTS_TAB)

    workout_options = workouts_df["Workout Name"] + " (" + workouts_df["Date"] + ")"
    selected_workout = st.selectbox("Select Workout", workout_options, key="select_workout")
    workout_row = workouts_df[workout_options == selected_workout].iloc[0]
    workout_id = workout_row["Workout ID"]

    st.subheader("Add New Exercise")
    exercise_name = st.text_input("Exercise Name", key="exercise_name")
    order = st.number_input("Order", min_value=1, step=1, key="order")
    is_superset = st.checkbox("Is Superset?", key="is_superset")
    superset_group = st.text_input("Superset Group (optional)", key="superset_group")

    if st.button("Add Exercise", key="add_exercise_btn"):
        exercise_id = f"ex_{int(datetime.now().timestamp())}"
        category = "Uncategorized"
        append_row(EXERCISES_TAB, [exercise_id, workout_id, exercise_name, order, int(is_superset), superset_group, category])
        st.success(f"Added exercise '{exercise_name}'.")

    st.divider()
    st.subheader("Log Set")
    filtered_exs = exercises_df[exercises_df["Workout ID"] == workout_id]
    selected_exercise = st.selectbox("Select Exercise", filtered_exs["Exercise Name"], key="select_exercise")
    selected_ex = filtered_exs[filtered_exs["Exercise Name"] == selected_exercise].iloc[0]
    exercise_id = selected_ex["Exercise ID"]

    set_number = st.number_input("Set #", min_value=1, step=1, key="set_number")
    weight = st.number_input("Weight", min_value=0.0, step=0.5, key="weight")
    reps = st.number_input("Reps", min_value=1, step=1, key="reps")
    notes = st.text_input("Notes", key="notes")

    if st.button("Log Set", key="log_set_btn"):
        set_id = f"set_{int(datetime.now().timestamp())}"
        timestamp = datetime.now().isoformat()
        append_row(SETS_TAB, [set_id, exercise_id, set_number, weight, reps, timestamp, notes])
        st.success("Set logged successfully.")

# --- TAB 3: PROGRESS TRACKER ---
with tab3:
    st.header("Progress Tracker", divider="gray")
    sets_df = load_data(SETS_TAB)
    exercises_df = load_data(EXERCISES_TAB)

    if not sets_df.empty and not exercises_df.empty:
        merged = sets_df.merge(exercises_df, on="Exercise ID")
        all_ex_names = merged["Exercise Name"].unique()
        ex_selected = st.selectbox("Choose Exercise", all_ex_names, key="progress_exercise")

        df_filtered = merged[merged["Exercise Name"] == ex_selected]
        df_filtered["Timestamp"] = pd.to_datetime(df_filtered["Timestamp"], errors='coerce')
        df_filtered = df_filtered.dropna(subset=["Timestamp"]).sort_values("Timestamp")

        st.subheader("Set History")
        st.dataframe(df_filtered[["Set Number", "Weight", "Reps", "Timestamp", "Notes"]], use_container_width=True)

        st.subheader("Weight Progress")
        st.plotly_chart(px.line(df_filtered, x='Timestamp', y='Weight', title="Weight Over Time"))

        st.subheader("Reps Progress")
        st.plotly_chart(px.line(df_filtered, x='Timestamp', y='Reps', title="Reps Over Time"))

        st.subheader("Personal Records")
        st.metric("Max Weight", f"{df_filtered['Weight'].max()} lbs")
        st.metric("Max Reps", f"{df_filtered['Reps'].max()} reps")
    else:
        st.info("Not enough data to display progress.")

# --- TAB 4: EXERCISE LIBRARY ---
with tab4:
    st.header("Exercise Library", divider="gray")
    exercises_df = load_data(EXERCISES_TAB)

    search_term = st.text_input("Search exercises", key="search_exercise")
    filtered = exercises_df[exercises_df["Exercise Name"].str.contains(search_term, case=False, na=False)]

    st.dataframe(filtered[["Exercise Name", "Category", "Order"]], use_container_width=True)

    st.subheader("Add New Exercise to Library")
    new_ex_name = st.text_input("Exercise Name", key="new_ex_name")
    new_category = st.text_input("Category", key="new_category")

    if st.button("Add to Library", key="add_library_btn"):
        new_ex_id = f"ex_{int(datetime.now().timestamp())}"
        append_row(EXERCISES_TAB, [new_ex_id, "", new_ex_name, 1, 0, "", new_category])
        st.success(f"'{new_ex_name}' added to library.")
