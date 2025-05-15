from flask import Flask, request, render_template
import requests
import os
import datetime
import time
import json

app = Flask(__name__)

# Constants for the exercise API
EXERCISE_API_TOKEN = "tkn_org_oavPgfwXVm1pfJqSSfJ9itUNaK9zDh"
EXERCISE_API_BASE_URL = "https://program.fitomics.org/api/v4"
EXERCISE_EMAIL = "admin@fitomics.org"
EXERCISE_PASSWORD = "Fitdrhaun23!"

# Shared cache folder
ALL_TIME_FOLDER = "all_time"
START_DATE = 1640995200  # 2022-01-01
END_DATE = int(time.time())

@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

def read_from_cache(filepath):
    try:
        with open(filepath, 'r') as cache_file:
            return json.load(cache_file)
    except:
        return None

def write_to_cache(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as cache_file:
        json.dump(data, cache_file)

@app.route("/")
def index():
    return """
    <h1>Welcome to the Exercise.com Dashboard</h1>
    <p>Go to <a href='/workouts'>/workouts</a> to load the workout data.</p>
    """

@app.route("/workouts")
def workouts():
    cache_dir = os.path.join("cache", "workouts", ALL_TIME_FOLDER)
    os.makedirs(cache_dir, exist_ok=True)
    users_cache_file = os.path.join("cache", f"users_all_time.json")
    user_workout_data = {}

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {EXERCISE_API_TOKEN}",
        "Api-Token": EXERCISE_API_TOKEN,
        "Content-Type": "application/json"
    })

    if os.path.exists(users_cache_file):
        user_list = read_from_cache(users_cache_file)
    else:
        signin_url = f"{EXERCISE_API_BASE_URL}/users/sign_in"
        auth = session.post(signin_url, json={"email": EXERCISE_EMAIL, "password": EXERCISE_PASSWORD})
        if auth.status_code != 200:
            return f"Authentication failed: {auth.text}", 401

        users_url = f"{EXERCISE_API_BASE_URL}/users"
        response = session.get(users_url, params={"per": 200})
        user_list = response.json().get("user", [])
        write_to_cache(users_cache_file, user_list)

    for user in user_list:
        user_id = user.get("id")
        if not user_id:
            continue

        cache_file = os.path.join(cache_dir, f"{user_id}.json")
        if os.path.exists(cache_file):
            workouts = read_from_cache(cache_file)
        else:
            workouts_url = f"{EXERCISE_API_BASE_URL}/workouts"
            params = {
                "user_id": user_id,
                "start_date": START_DATE,
                "end_date": END_DATE,
                "all_fields": "true",
                "per": 1000
            }
            response = session.get(workouts_url, params=params)
            if response.status_code == 200:
                workouts = response.json()
                write_to_cache(cache_file, workouts)
            else:
                workouts = []

        user_workout_data[user_id] = {
            "user_info": {
                "id": user_id,
                "first_name": user.get("first_name", "N/A"),
                "last_name": user.get("last_name", "N/A"),
                "email": user.get("email", "N/A")
            },
            "workouts": workouts
        }

    sorted_users = sorted(user_workout_data.items(), key=lambda x: len(x[1]['workouts']), reverse=True)
    report_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render_template("workout_report.html",
                           sorted_users=sorted_users,
                           report_date=report_date,
                           period_start="2022-01-01",
                           period_end=datetime.datetime.now().strftime("%Y-%m-%d"))

@app.route("/client-dashboard", methods=["GET"])
def client_dashboard():
    client_id = request.args.get("client_id")
    if not client_id:
        return "Client ID not provided", 400

    cache_path = os.path.join("cache", "workouts", ALL_TIME_FOLDER, f"{client_id}.json")
    if not os.path.exists(cache_path):
        return f"No cached workouts found for client ID {client_id}", 404

    with open(cache_path, "r") as f:
        workouts = json.load(f)

    unique_dates = sorted(set([
        datetime.datetime.fromtimestamp(w.get("workout_date", 0)).strftime("%Y-%m-%d")
        for w in workouts if w.get("workout_date")
    ]), reverse=True)

    all_exercises = []
    for w in workouts:
        workout_date = datetime.datetime.fromtimestamp(w.get("workout_date", 0)).strftime("%Y-%m-%d")
        for exercise in w.get("workout_exercises", []):
            exercise_name = exercise.get("name", "Unnamed Exercise")
            for s in exercise.get("workout_exercise_sets", []):
                reps = s.get("reps", 0)
                weight = s.get("weight", 0.0)
                volume = reps * weight
                all_exercises.append({
                    "workout_date": workout_date,
                    "exercise_name": exercise_name,
                    "sets": 1,
                    "reps": reps,
                    "weight": weight,
                    "volume": volume
                })

    return render_template("client_dashboard.html",
                           client_id=client_id,
                           dates=unique_dates,
                           exercises=all_exercises)

if __name__ == "__main__":
    app.run(debug=True)



