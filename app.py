from flask import Flask, request, render_template
import requests
import os
import datetime
import time
import json
import pandas as pd

app = Flask(__name__)

# === Exercise.com API Credentials ===
EXERCISE_API_TOKEN = "tkn_org_oavPgfwXVm1pfJqSSfJ9itUNaK9zDh"
EXERCISE_API_BASE_URL = "https://program.fitomics.org/api/v4"
EXERCISE_EMAIL = "admin@fitomics.org"
EXERCISE_PASSWORD = "Fitdrhaun23!"

# === Authenticate ===
def login_to_api():
    login_url = f"{EXERCISE_API_BASE_URL}/users/sign_in"
    response = requests.post(
        login_url,
        json={"email": EXERCISE_EMAIL, "password": EXERCISE_PASSWORD},
        headers={"Authorization": EXERCISE_API_TOKEN, "Content-Type": "application/json"}
    )
    response.raise_for_status()
    return response.json().get("auth_token")

# === Fetch Workouts ===
def fetch_all_workouts(auth_token, user_id=None, start_date="2024-01-01", end_date="2024-12-31"):
    all_workouts = []
    page = 1
    has_more = True

    while has_more:
        response = requests.get(
            f"{EXERCISE_API_BASE_URL}/workouts",
            params={
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "page": page,
                "per": 100,
                "all_fields": "true"
            },
            headers={
                "Authorization": f"Bearer {auth_token}",
                "API-TOKEN": EXERCISE_API_TOKEN
            }
        )
        response.raise_for_status()
        data = response.json()

        workouts = data.get("workouts", [])
        all_workouts.extend(workouts)

        meta = data.get("meta", {})
        has_more = meta.get("current_page", 1) < meta.get("total_pages", 1)
        page += 1

    return all_workouts

# === Flatten to DataFrame ===
def flatten_workouts(workouts):
    flat_rows = []
    for workout in workouts:
        exercises = workout.get("exercises", [])
        for ex in exercises:
            flat_rows.append({
                "workout_id": workout.get("id"),
                "user_id": workout.get("user_id"),
                "workout_name": workout.get("name"),
                "date": workout.get("date"),
                "exercise_name": ex.get("name"),
                "sets": ex.get("sets"),
                "reps": ex.get("reps"),
                "weight": ex.get("weight")
            })
    return pd.DataFrame(flat_rows)

# === Flask route for dashboard ===
@app.route("/dashboard", methods=["GET"])
def dashboard():
    try:
        auth_token = login_to_api()
        selected_exercise = request.args.get("exercise", default="Deadlift")
        start_date = request.args.get("start", default="2024-01-01")
        end_date = request.args.get("end", default="2024-12-31")

        workouts_raw = fetch_all_workouts(auth_token, start_date=start_date, end_date=end_date)
        df = flatten_workouts(workouts_raw)

        # Filter by selected exercise
        filtered = df[df["exercise_name"].str.lower().str.contains(selected_exercise.lower())]
        filtered["date"] = pd.to_datetime(filtered["date"])
        filtered.sort_values("date", inplace=True)

        # Calculate PR (max weight by week)
        filtered["week"] = filtered["date"].dt.to_period("W").astype(str)
        pr_by_week = filtered.groupby("week")["weight"].max().reset_index()

        # Weekly volume = sets * reps * weight summed per week
        filtered["volume"] = filtered["sets"] * filtered["reps"] * filtered["weight"]
        volume_by_week = filtered.groupby("week")["volume"].sum().reset_index()

        return render_template("dashboard.html",
                               exercise=selected_exercise,
                               table=filtered.to_dict(orient="records"),
                               pr_data=pr_by_week.to_dict(orient="records"),
                               volume_data=volume_by_week.to_dict(orient="records"),
                               start=start_date,
                               end=end_date)

    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)
