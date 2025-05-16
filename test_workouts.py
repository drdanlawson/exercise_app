from flask import Flask, request, render_template, jsonify
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
            elif response.status_code == 403:
                print(f"[WARNING] Access denied for user {user_id} — skipping.")
                workouts = []
                continue  # Skip this user entirely
            else:
                print(f"[ERROR] Failed to fetch workouts for user {user_id}: {response.status_code}")
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

@app.route("/filter-client-data", methods=["POST"])
def filter_client_data():
    data = request.json
    client_id = data.get("client_id")
    start_date = datetime.datetime.strptime(data.get("start_date"), "%Y-%m-%d")
    end_date = datetime.datetime.strptime(data.get("end_date"), "%Y-%m-%d")

    cache_path = os.path.join("cache", "workouts", ALL_TIME_FOLDER, f"{client_id}.json")
    if not os.path.exists(cache_path):
        return {"error": "No cached workouts found."}, 404

    with open(cache_path, "r") as f:
        workouts = json.load(f)

    summary = {}
    for w in workouts:
        w_date = datetime.datetime.fromtimestamp(w.get("workout_date", 0))
        if not (start_date <= w_date <= end_date):
            continue

        date_str = w_date.strftime("%Y-%m-%d")
        for exercise in w.get("workout_exercises", []):
            for s in exercise.get("workout_exercise_sets", []):
                weight = s.get("weight", 0.0)
                reps = s.get("reps", 0)
                volume = weight * reps

                if date_str not in summary:
                    summary[date_str] = {
                        "volume": 0,
                        "sets": 0,
                        "max_weight": 0,
                        "total_weight": 0
                    }

                summary[date_str]["volume"] += volume
                summary[date_str]["sets"] += 1
                summary[date_str]["max_weight"] = max(summary[date_str]["max_weight"], weight)
                summary[date_str]["total_weight"] += weight

    for date_str in summary:
     sets = summary[date_str]["sets"]
     total_weight = summary[date_str]["total_weight"]
     summary[date_str]["avg_weight"] = total_weight / sets if sets > 0 else 0

    return summary

@app.route("/filter-pre-post-data", methods=["POST"])
def filter_pre_post_data():
    data = request.json
    client_id = data.get("client_id")
    pre_start = datetime.datetime.strptime(data["pre_start"], "%Y-%m-%d")
    pre_end = datetime.datetime.strptime(data["pre_end"], "%Y-%m-%d")
    post_start = datetime.datetime.strptime(data["post_start"], "%Y-%m-%d")
    post_end = datetime.datetime.strptime(data["post_end"], "%Y-%m-%d")

    cache_path = os.path.join("cache", "workouts", ALL_TIME_FOLDER, f"{client_id}.json")
    if not os.path.exists(cache_path):
        return {"error": "No cached workouts found."}, 404

    with open(cache_path, "r") as f:
        workouts = json.load(f)

    def filter_and_aggregate(start, end):
        results = []
        for w in workouts:
            w_date = datetime.datetime.fromtimestamp(w.get("workout_date", 0))
            if not (start <= w_date <= end):
                continue

            summary = {"volume": 0, "sets": 0, "max_weight": 0, "total_weight": 0, "count": 0}
            for exercise in w.get("workout_exercises", []):
                for s in exercise.get("workout_exercise_sets", []):
                    weight = s.get("weight", 0.0)
                    reps = s.get("reps", 0)
                    volume = weight * reps

                    summary["volume"] += volume
                    summary["sets"] += 1
                    summary["max_weight"] = max(summary["max_weight"], weight)
                    summary["total_weight"] += weight
                    summary["count"] += 1

            if summary["count"] > 0:
                summary["avg_weight"] = round(summary["total_weight"] / summary["count"], 1)
            else:
                summary["avg_weight"] = 0

            results.append(summary)
        return results

    pre_data = filter_and_aggregate(pre_start, pre_end)
    post_data = filter_and_aggregate(post_start, post_end)

    comparison = []
    for i in range(min(len(pre_data), len(post_data))):
        comparison.append({
            "label": f"Workout {i+1}",
            "pre": pre_data[i],
            "post": post_data[i]
        })

    return jsonify(comparison)

@app.route("/filter-exercise-pre-post-data", methods=["POST"])
def filter_exercise_pre_post_data():
    data = request.json
    client_id = data.get("client_id")
    pre_start = datetime.datetime.strptime(data.get("pre_start"), "%Y-%m-%d")
    pre_end = datetime.datetime.strptime(data.get("pre_end"), "%Y-%m-%d")
    post_start = datetime.datetime.strptime(data.get("post_start"), "%Y-%m-%d")
    post_end = datetime.datetime.strptime(data.get("post_end"), "%Y-%m-%d")

    cache_path = os.path.join("cache", "workouts", ALL_TIME_FOLDER, f"{client_id}.json")
    if not os.path.exists(cache_path):
        return jsonify({"error": "No cached workouts found."}), 404

    with open(cache_path, "r") as f:
        workouts = json.load(f)

    def summarize_by_exercise(start, end):
        summary = {}
        for w in workouts:
            w_date = datetime.datetime.fromtimestamp(w.get("workout_date", 0))
            if not (start <= w_date <= end):
                continue
            for exercise in w.get("workout_exercises", []):
                name = exercise.get("name", "Unnamed")
                for s in exercise.get("workout_exercise_sets", []):
                    reps = s.get("reps", 0)
                    weight = s.get("weight", 0.0)
                    volume = reps * weight

                    if name not in summary:
                        summary[name] = {"volume": 0, "max_weight": 0, "weight_sum": 0, "set_count": 0}
                    summary[name]["volume"] += volume
                    summary[name]["max_weight"] = max(summary[name]["max_weight"], weight)
                    summary[name]["weight_sum"] += weight
                    summary[name]["set_count"] += 1
        for val in summary.values():
            val["avg_weight"] = round(val["weight_sum"] / val["set_count"], 2) if val["set_count"] else 0
        return summary

    pre_summary = summarize_by_exercise(pre_start, pre_end)
    post_summary = summarize_by_exercise(post_start, post_end)

    common_exercises = list(set(pre_summary.keys()) & set(post_summary.keys()))
    comparison = {
        "volume": {"labels": [], "pre": [], "post": []},
        "max_weight": {"labels": [], "pre": [], "post": []},
        "avg_weight": {"labels": [], "pre": [], "post": []}
    }

    for ex in common_exercises:
        comparison["volume"]["labels"].append(ex)
        comparison["volume"]["pre"].append(pre_summary[ex]["volume"])
        comparison["volume"]["post"].append(post_summary[ex]["volume"])
        comparison["max_weight"]["labels"].append(ex)
        comparison["max_weight"]["pre"].append(pre_summary[ex]["max_weight"])
        comparison["max_weight"]["post"].append(post_summary[ex]["max_weight"])
        comparison["avg_weight"]["labels"].append(ex)
        comparison["avg_weight"]["pre"].append(pre_summary[ex]["avg_weight"])
        comparison["avg_weight"]["post"].append(post_summary[ex]["avg_weight"])

    return jsonify(comparison)

@app.route("/filter-pre-post-exercise-data", methods=["POST"])
def filter_pre_post_exercise_data():
    data = request.json
    client_id = data.get("client_id")
    pre_start = datetime.datetime.strptime(data.get("pre_start"), "%Y-%m-%d")
    pre_end = datetime.datetime.strptime(data.get("pre_end"), "%Y-%m-%d")
    post_start = datetime.datetime.strptime(data.get("post_start"), "%Y-%m-%d")
    post_end = datetime.datetime.strptime(data.get("post_end"), "%Y-%m-%d")

    cache_path = os.path.join("cache", "workouts", ALL_TIME_FOLDER, f"{client_id}.json")
    if not os.path.exists(cache_path):
        return jsonify([])

    with open(cache_path, "r") as f:
        workouts = json.load(f)

    def extract_sets(start, end, phase_label):
        result = []
        for w in workouts:
            w_date = datetime.datetime.fromtimestamp(w.get("workout_date", 0))
            if not (start <= w_date <= end):
                continue
            date_str = w_date.strftime("%Y-%m-%d")
            for ex in w.get("workout_exercises", []):
                name = ex.get("name", "Unnamed Exercise")
                for s in ex.get("workout_exercise_sets", []):
                    result.append({
                        "exercise": name,
                        "date": date_str,
                        "reps": s.get("reps", 0),
                        "weight": s.get("weight", 0.0),
                        "phase": phase_label
                    })
        return result

    pre_sets = extract_sets(pre_start, pre_end, "Pre")
    post_sets = extract_sets(post_start, post_end, "Post")
    all_sets = pre_sets + post_sets

    grouped = {}
    for s in all_sets:
        key = (s["exercise"], s["phase"])
        grouped.setdefault(key, []).append(s)

    response_data = []
    for (exercise, phase), sets in grouped.items():
        total_sets = len(sets)
        total_reps = sum(s["reps"] for s in sets)
        avg_reps = total_reps / total_sets if total_sets else 0
        avg_weight = sum(s["weight"] for s in sets) / total_sets if total_sets else 0
        max_weight = max(s["weight"] for s in sets) if sets else 0
        response_data.append({
            "exercise": exercise,
            "phase": phase,
            "total_sets": total_sets,
            "total_reps": total_reps,
            "avg_reps": avg_reps,
            "avg_weight": avg_weight,
            "max_weight": max_weight,
            "sets": sets
        })

    return jsonify(response_data)


if __name__ == "__main__":
    app.run(debug=True)



