import firebase_admin
from firebase_admin import credentials, firestore, auth
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json
import tempfile

# Retrieve the Firebase credentials as a string from Streamlit secrets
firebase_creds = st.secrets["firebase"]["credentials"]

# Create a temporary file for the Firebase credentials
with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json', dir='./') as temp_file:
    temp_file.write(firebase_creds)  # Write the credentials JSON to the file
    temp_file_path = temp_file.name

# Initialize Firebase with the temporary credentials file
if not firebase_admin._apps:
    cred = credentials.Certificate(temp_file_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Nutritionix API credentials
API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"
API_KEY = "01cdcf515d8e7813ca086b9a1c673891"
APP_ID = "5ed53420"

# Function to fetch calories from Nutritionix API
def fetch_calories_from_nutritionix(food_item):
    headers = {
        "x-app-id": APP_ID,
        "x-app-key": API_KEY,
    }
    data = {
        "query": food_item
    }
    response = requests.post(API_URL, headers=headers, json=data)
    if response.status_code == 200:
        nutrients = response.json()["foods"][0]
        return nutrients["nf_calories"]
    else:
        st.error("Failed to fetch data from Nutritionix API")
        return None

# Function to save data to Firebase
def save_log_to_firebase(log, user_id):
    db.collection("users").document(user_id).collection("food_logs").add(log)

# Function to save user profile data to Firebase
def save_user_profile_to_firebase(user_id, name, age, weight, daily_calorie_goal):
    user_profile = {
        "Name": name,
        "Age": age,
        "Weight": weight,
        "Daily Calorie Goal": daily_calorie_goal
    }
    db.collection("users").document(user_id).set(user_profile, merge=True)

# Function to fetch user profile from Firebase
def fetch_user_profile_from_firebase(user_id):
    user_profile_ref = db.collection("users").document(user_id)
    user_profile = user_profile_ref.get().to_dict()
    return user_profile
from datetime import datetime

def save_feedback_to_firebase(feedback, email):
    """Save user feedback to Firebase Firestore."""
    feedback_entry = {
        "feedback": feedback,
        "email": email,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        db.collection("feedback").add(feedback_entry)  # Add the feedback to the feedback collection
        return True
    except Exception as e:
        print(f"Error saving feedback: {e}")
        return False


# Function for user authentication
def user_authentication():
    # Add image and title in the center of the page
    col1, col2, col3 = st.columns([1, 2, 1])  # Create three columns
    with col2:
        st.image("lg2.png", width=300)
        st.title("Fitness Tracker")

    # Center the radio buttons (New User / Existing User)
    col1, col2, col3 = st.columns([1, 2, 1])  # Create three columns for centering
    with col2:
        user_type = st.radio("Are you a new user or do you already have an account?", ("New User", "Existing User"))

    # Existing User form in center layout
    if user_type == "Existing User":
        col1, col2, col3 = st.columns([1, 2, 1])  # Create three columns for centering the form
        with col2:
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Sign In"):
                try:
                    user = auth.get_user_by_email(email)
                    st.success(f"Welcome back, {user.email}!")
                    user_id = user.uid
                    st.session_state.user_id = user_id
                    st.rerun()

                except auth.UserNotFoundError:
                    st.error("User not found. Please check your credentials or sign up.")
                except Exception as e:
                    st.error(f"Error during sign-in: {e}")

    # New User form in center layout
    else:
        col1, col2, col3 = st.columns([1, 2, 1])  # Create three columns for centering the form
        with col2:
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            password_confirmation = st.text_input("Confirm Password", type="password")
            name, age = st.columns(2)  # Name and Age in one line
            with name:
                name = st.text_input("Name")
            with age:
                age = st.number_input("Age", min_value=0, max_value=150)
            weight, daily_calorie_goal = st.columns(2)  # Weight and Calorie Goal in one line
            with weight:
                weight = st.number_input("Weight (kg)", min_value=0)
            with daily_calorie_goal:
                daily_calorie_goal = st.number_input("Daily Calorie Goal", min_value=0)

            if st.button("Sign Up"):
                if password != password_confirmation:
                    st.error("Passwords do not match")
                else:
                    try:
                        user = auth.create_user(email=email, password=password)
                        st.success(f"User created: {user.email}")
                        user_id = user.uid
                        st.session_state.user_id = user_id
                        save_user_profile_to_firebase(user_id, name, age, weight, daily_calorie_goal)
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error during sign-up: {e}") 

# Function to allow users to update their profile information
def update_user_profile(user_id):
    st.header("Update Profile")

    user_profile = fetch_user_profile_from_firebase(user_id)

    if user_profile:
        current_age = user_profile.get('Age', '')
        current_weight = user_profile.get('Weight', '')
        current_daily_calorie_goal = user_profile.get('Daily Calorie Goal', '')

        new_age = st.number_input("Age", value=current_age, min_value=0, max_value=150)
        new_weight = st.number_input("Weight (kg)", value=current_weight, min_value=0)
        new_daily_calorie_goal = st.number_input("Daily Calorie Goal", value=current_daily_calorie_goal, min_value=0)

        if st.button("Update Profile"):
            try:
                save_user_profile_to_firebase(user_id, user_profile.get('Name', ''), new_age, new_weight, new_daily_calorie_goal)
                st.success("Profile updated successfully")
                st.rerun()

            except Exception as e:
                st.error(f"Error updating profile: {e}")
    else:
        st.error("User profile not found")

# Function to allow users to delete a specific log
def delete_log_from_firebase(log_id, user_id):
    db.collection("users").document(user_id).collection("food_logs").document(log_id).delete()

# Function to allow users to clear all logs
def clear_logs_from_firebase(user_id):
    logs_ref = db.collection("users").document(user_id).collection("food_logs")
    batch = db.batch()
    for doc in logs_ref.stream():
        batch.delete(doc.reference)
    batch.commit()

# Function to fetch daily summary
def fetch_daily_summary(user_id):
    food_logs = db.collection("users").document(user_id).collection("food_logs").stream()
    daily_summary = {}
    for log in food_logs:
        log_data = log.to_dict()
        log_date = log_data["Date"].split(" ")[0]
        if log_date in daily_summary:
            daily_summary[log_date] += log_data["Calories"]
        else:
            daily_summary[log_date] = log_data["Calories"]
    return daily_summary

# Function to save exercise log to Firebase
def save_exercise_log_to_firebase(log, user_id):
    db.collection("users").document(user_id).collection("exercise_logs").add(log)

# Function to save water intake log to Firebase
def save_water_intake_to_firebase(intake, user_id):
    db.collection("users").document(user_id).collection("water_intake").add(intake)

# Function to save sleep log to Firebase
def save_sleep_log_to_firebase(log, user_id):
    db.collection("users").document(user_id).collection("sleep_logs").add(log)

# Function to allow users to log exercise
def log_exercise(user_id):
    st.header("Log Exercise")

    exercise_type_options = ["Cardio", "Strength Training", "Yoga"]
    exercise_type = st.selectbox("Exercise Type", exercise_type_options + ["Other"])

    if exercise_type == "Other":
        exercise_type = st.text_input("Enter Exercise Type")

    duration = st.number_input("Duration (minutes)", min_value=1)
    intensity = st.slider("Intensity", min_value=1, max_value=10, step=1)

    if st.button("Log Exercise"):
        new_log = {"Date": datetime.today().strftime('%Y-%m-%d %H:%M:%S'), "Exercise Type": exercise_type,
                   "Duration (minutes)": duration, "Intensity": intensity}
        save_exercise_log_to_firebase(new_log, user_id)
        st.success("Exercise logged successfully")

# Function to allow users to log water intake
def log_water_intake(user_id):
    st.header("Log Water Intake")

    amount_ml = st.number_input("Amount (ml)", min_value=1)

    if st.button("Log Water Intake"):
        intake = {"Date": datetime.today().strftime('%Y-%m-%d %H:%M:%S'), "Amount (ml)": amount_ml}
        save_water_intake_to_firebase(intake, user_id)
        st.success("Water intake logged successfully")

# Function to allow users to log sleep
def log_sleep(user_id):
    st.header("Log Sleep")

    sleep_duration = st.number_input("Sleep Duration (hours)", min_value=1)
    sleep_quality = st.slider("Sleep Quality", min_value=1, max_value=10, step=1)

    if st.button("Log Sleep"):
        new_log = {"Date": datetime.today().strftime('%Y-%m-%d %H:%M:%S'), "Sleep Duration (hours)": sleep_duration,
                   "Sleep Quality": sleep_quality}
        save_sleep_log_to_firebase(new_log, user_id)
        st.success("Sleep logged successfully")
# Function to fetch exercise logs from Firebase
def fetch_exercise_logs(user_id):
    exercise_logs_ref = db.collection("users").document(user_id).collection("exercise_logs")
    exercise_logs = exercise_logs_ref.stream()
    logs = [log.to_dict() for log in exercise_logs]
    return pd.DataFrame(logs)

# Function to fetch water intake logs from Firebase
def fetch_water_intake(user_id):
    water_intake_ref = db.collection("users").document(user_id).collection("water_intake")
    water_intake = water_intake_ref.stream()
    intake = [intake.to_dict() for intake in water_intake]
    return pd.DataFrame(intake)

# Function to fetch sleep logs from Firebase
def fetch_sleep_logs(user_id):
    sleep_logs_ref = db.collection("users").document(user_id).collection("sleep_logs")
    sleep_logs = sleep_logs_ref.stream()
    logs = [log.to_dict() for log in sleep_logs]
    return pd.DataFrame(logs)

# Function to display exercise statistics
def display_exercise_statistics(user_id):
    st.header("Exercise Statistics")

    exercise_logs_df = fetch_exercise_logs(user_id)

    if not exercise_logs_df.empty:
        st.subheader("Exercise Logs")
        st.dataframe(exercise_logs_df)

        st.subheader("Exercise Summary")
        st.write("Total Duration (minutes):", exercise_logs_df["Duration (minutes)"].sum())
        st.write("Average Intensity:", exercise_logs_df["Intensity"].mean())
        st.write("Most Common Exercise Type:", exercise_logs_df["Exercise Type"].mode().iloc[0])
    else:
        st.write("No exercise logs available")

# Function to display water intake statistics
def display_water_intake_statistics(user_id):
    st.header("Water Intake Statistics")

    water_intake_df = fetch_water_intake(user_id)

    if not water_intake_df.empty:
        st.subheader("Water Intake Logs")
        st.dataframe(water_intake_df)

        st.subheader("Water Intake Summary")
        st.write("Total Amount (ml):", water_intake_df["Amount (ml)"].sum())
        # Additional statistics can be added as needed
    else:
        st.write("No water intake logs available")

# Function to display sleep statistics
def display_sleep_statistics(user_id):
    st.header("Sleep Statistics")

    sleep_logs_df = fetch_sleep_logs(user_id)

    if not sleep_logs_df.empty:
        st.subheader("Sleep Logs")
        st.dataframe(sleep_logs_df)

        st.subheader("Sleep Summary")
        st.write("Total Sleep Duration (hours):", sleep_logs_df["Sleep Duration (hours)"].sum())
        st.write("Average Sleep Quality:", sleep_logs_df["Sleep Quality"].mean())
        # Additional statistics can be added as needed
    else:
        st.write("No sleep logs available")

        # Function to fetch weekly summary
def fetch_weekly_summary(user_id):
    food_logs = db.collection("users").document(user_id).collection("food_logs").stream()
    weekly_summary = {}
    for log in food_logs:
        log_data = log.to_dict()
        log_date = log_data["Date"].split(" ")[0]
        week = datetime.strptime(log_date, "%Y-%m-%d").isocalendar()[1]
        year = datetime.strptime(log_date, "%Y-%m-%d").year
        week_year = f"{year}-W{week}"
        if week_year in weekly_summary:
            weekly_summary[week_year] += log_data["Calories"]
        else:
            weekly_summary[week_year] = log_data["Calories"]
    return weekly_summary

# Function to fetch monthly summary
def fetch_monthly_summary(user_id):
    food_logs = db.collection("users").document(user_id).collection("food_logs").stream()
    monthly_summary = {}
    for log in food_logs:
        log_data = log.to_dict()
        log_date = log_data["Date"].split(" ")[0]
        month = datetime.strptime(log_date, "%Y-%m-%d").strftime("%Y-%m")
        if month in monthly_summary:
            monthly_summary[month] += log_data["Calories"]
        else:
            monthly_summary[month] = log_data["Calories"]
    return monthly_summary

# Main Streamlit app
# Main Streamlit app
def main():
    if "user_id" not in st.session_state:
        user_authentication()
        return

    st.set_page_config(page_title="Fitness Tracker", layout="wide")
    st.title("Fitness Tracker")

    user_id = st.session_state.user_id

    user_profile = fetch_user_profile_from_firebase(user_id)
    if user_profile:
        st.write(f"*Name:* {user_profile.get('Name', '')}")
        st.write(f"*Age:* {user_profile.get('Age', '')}")
        st.write(f"*Weight:* {user_profile.get('Weight', '')} kg")
        st.write(f"*Daily Calorie Goal:* {user_profile.get('Daily Calorie Goal', '')} calories")

    update_user_profile(user_id)
    log_exercise(user_id)
    log_water_intake(user_id)
    log_sleep(user_id)

    display_exercise_statistics(user_id)
    display_water_intake_statistics(user_id)
    display_sleep_statistics(user_id)

 
      # Display calorie goal and progress
    st.header("Calorie Goal Progress")
    daily_summary = fetch_daily_summary(user_id)
    daily_summary_df = pd.DataFrame(list(daily_summary.items()), columns=["Date", "Calories"])
    if not daily_summary_df.empty:
        daily_calorie_goal = user_profile.get('Daily Calorie Goal', 0)
        total_calories_consumed = daily_summary_df["Calories"].sum()
        progress_percentage = min(100, int((total_calories_consumed / daily_calorie_goal) * 100))
        
        st.write(f"*Daily Calorie Goal:* {daily_calorie_goal} calories")
        st.write(f"*Total Calories Consumed:* {total_calories_consumed} calories")
        st.write(f"*Progress:* {progress_percentage}%")
        
        # Display progress bar
        st.progress(progress_percentage / 100)
# Sidebar
    st.sidebar.title("Welcome to Fitness Tracker")
    st.sidebar.image("lg2.png", use_container_width=True)

    st.sidebar.header("About")
    st.sidebar.write("Welcome to Fitness Tracker, your personal fitness companion!")
    st.sidebar.write("Track your workouts, monitor your progress, and achieve your fitness goals with ease.")
    st.sidebar.write("We provide a user-friendly interface for logging food intake, workouts, water intake, and sleep. You can also track your progress and set fitness goals.")

    st.sidebar.subheader("Features")
    st.sidebar.write("- Log workouts, water intake, and sleep")
    st.sidebar.write("- View personalized fitness statistics and insights")
    st.sidebar.write("- Set and track your fitness goals")
    st.sidebar.write("- Access a user-friendly and responsive interface")
    st.sidebar.write("- Nutrition tracking using the Nutritionix API for detailed food logs and calorie tracking")

# Improved call to action with icon and link
    st.sidebar.subheader("Want to level up your fitness journey?")
    st.sidebar.write("Discover our advanced gym workout planner designed to help you maximize your results!")
    link = "https://musclemate-app.netlify.app/"
    st.sidebar.write(f"Check out MuscleMate: [Click here]({link})")

    st.sidebar.subheader("API Integration: Nutritionix API")
    st.sidebar.markdown("""
    - *Frontend:* Streamlit - A Python library for creating interactive web applications quickly and easily. Streamlit allows for a user-friendly interface with minimal coding effort.
    - *Backend:* Firebase - Google's cloud-hosted platform for mobile and web app development. Firebase provides functionalities like user authentication, data storage with a real-time database, and secure backend services.
    - *API Integration:* Nutritionix API - This API allows the Health Tracker app to retrieve nutritional information for food items entered by users. This simplifies calorie tracking and empowers users to make informed dietary decisions.
    """)
    st.sidebar.subheader("Architecture and Design")

    st.sidebar.markdown("""
    The Fitness Tracker application leverages a Service-Oriented Architecture (SOA) to promote scalability and reusability. In SOA, functionalities are encapsulated as independent services that communicate with each other through well-defined interfaces (APIs). This project implements a simple SOA with two key components:
    - *Publisher App:* This app (in this case, the Nutritionix API) exposes services through APIs. The Health Tracker application consumes these APIs to access specific functionalities. For example, the Nutritionix API provides an API for retrieving calorie information based on a food item search.
    - *Consumer App:* This is your Health Tracker application. It utilizes APIs exposed by the publisher app to deliver its features. By consuming the Nutritionix API, the Health Tracker empowers users to track their calorie intake seamlessly.
    *Benefits of using SOA:*

    - *Scalability:* SOA allows for independent scaling of publisher and consumer apps. If the user base for Health Tracker grows significantly, the backend infrastructure can be scaled without affecting the Nutritionix API.
    - *Reusability:* APIs exposed by the publisher app can be consumed by various consumer applications. This promotes code reuse and reduces development time for future apps requiring similar functionalities.
    - *Loose Coupling:* Consumer apps are not tightly coupled to the implementation details of the publisher app. This allows for flexibility and easier maintenance in the future.
    """)

    st.sidebar.subheader("We value your feedback!")
    st.sidebar.write("Your insights help us improve Fitness Tracker to better serve your fitness needs.")
    
    feedback_paragraph = st.sidebar.text_area("Your feedback", height=150, placeholder="Enter your feedback here...")
    user_email = st.sidebar.text_input("Your email", placeholder="Enter your email here...")

    if st.sidebar.button("Submit Feedback"):
        if not feedback_paragraph.strip():
            st.sidebar.error("Feedback cannot be empty. Please enter your feedback.")
        elif not user_email.strip():
            st.sidebar.error("Email cannot be empty. Please enter your email.")
        else:
            success = save_feedback_to_firebase(feedback_paragraph.strip(), user_email.strip())
            if success:
                st.sidebar.success("Thank you for your feedback! It has been submitted successfully.")
            # Clear inputs after submission
                st.session_state["feedback_paragraph"] = ""
                st.session_state["user_email"] = ""
                st.rerun()

            else:
                st.sidebar.error("There was an error submitting your feedback. Please try again.")

            
          
    st.title("Calorie Tracker")
    st.header("Add a new food log")
    option = st.radio("How do you want to add your log?", ("Manually", " Automatically (Using Nutritionix API)"))

    if option == "Manually":
        food = st.text_input("Food")
        calories = st.number_input("Calories", min_value=0)
        if st.button("Add Log"):
            if food and calories is not None:
                new_log = {"Date": datetime.today().strftime('%Y-%m-%d %H:%M:%S'), "Food": food, "Calories": calories}
                save_log_to_firebase(new_log, user_id)
                st.success(f"Log added: {food} - {calories} calories")
            else:
                st.error("Please enter both food item and calories")
    else:
        food = st.text_input("Food")
        if st.button("Add Log"):
            if food:
                calories = fetch_calories_from_nutritionix(food)
                if calories is not None:
                    new_log = {"Date": datetime.today().strftime('%Y-%m-%d %H:%M:%S'), "Food": food, "Calories": calories}
                    save_log_to_firebase(new_log, user_id)
                    st.success(f"Log added: {food} - {calories} calories")
            else:
                st.error("Please enter a food item")


# Modify the section for displaying food logs and deletion logic
    st.header("Food Logs")
    food_logs = db.collection("users").document(user_id).collection("food_logs").stream()
    logs = [{"Log ID": log.id, "Date": log.to_dict()["Date"], "Food": log.to_dict()["Food"], "Calories": log.to_dict()["Calories"]} for log in food_logs]
    food_log_df = pd.DataFrame(logs)

    if not food_log_df.empty:
        st.dataframe(food_log_df)

        log_to_delete = st.selectbox("Select log to delete", options=[""] + food_log_df["Log ID"].tolist(), format_func=lambda log_id: food_log_df[food_log_df["Log ID"] == log_id]["Food"].iloc[0] if log_id != "" else "")
        if log_to_delete:
            if st.button("Delete Log"):
                delete_log_from_firebase(log_to_delete, user_id)
                st.success("Log deleted successfully")
                st.rerun()

    if st.button("Clear All Logs"):
            if st.checkbox("Confirm Clear All Logs"):
                clear_logs_from_firebase(user_id)
                st.success("All logs cleared successfully")
                st.rerun()

    else:
        st.write("No logs available")

    if not food_log_df.empty:
        st.header("Calorie Intake")
        st.line_chart(food_log_df.set_index("Date")["Calories"])


    st.header("Daily Calorie Consumption")
    daily_summary = fetch_daily_summary(user_id)
    daily_summary_df = pd.DataFrame(list(daily_summary.items()), columns=["Date", "Calories"])
    st.bar_chart(daily_summary_df.set_index("Date"))


# Display weekly and monthly summaries
    st.header("Weekly and Monthly Trends")

    weekly_summary = fetch_weekly_summary(user_id)
    monthly_summary = fetch_monthly_summary(user_id)
    if weekly_summary:
        weekly_summary_df = pd.DataFrame(list(weekly_summary.items()), columns=["Week", "Calories"])
        st.subheader("Weekly Calorie Consumption")
        st.line_chart(weekly_summary_df.set_index("Week")["Calories"])

    if monthly_summary:
        monthly_summary_df = pd.DataFrame(list(monthly_summary.items()), columns=["Month", "Calories"])
        st.subheader("Monthly Calorie Consumption")
        st.line_chart(monthly_summary_df.set_index("Month")["Calories"])

    if st.button("Logout", key="logout_button"):
        del st.session_state["user_id"]
        st.rerun()


if __name__ == "__main__":
    main()