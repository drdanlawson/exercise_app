import requests
import json
import os

EXERCISE_API_TOKEN = "tkn_org_oavPgfwXVm1pfJqSSfJ9itUNaK9zDh"
EXERCISE_API_BASE_URL = "https://program.fitomics.org/api/v4"
HEADERS = {
    "Authorization": f"Bearer {EXERCISE_API_TOKEN}",
    "Api-Token": EXERCISE_API_TOKEN,
    "Content-Type": "application/json"
}

CACHE_DIR = "cache/workouts/all_time"

def get_all_exercise_ids():
    """Extract all unique exercise IDs from cached workouts"""
    unique_ids = set()
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(CACHE_DIR, filename), "r") as f:
                workouts = json.load(f)
                for workout in workouts:
                    for ex in workout.get("workout_exercises", []):
                        if "exercise_id" in ex:
                            unique_ids.add(ex["exercise_id"])
    return sorted(unique_ids)

def fetch_exercise_metadata(exercise_ids):
    exercise_metadata = {}
    for ex_id in exercise_ids:
        url = f"{EXERCISE_API_BASE_URL}/exercises/{ex_id}"
        res = requests.get(url, headers=HEADERS)
        if res.status_code != 200:
            print(f"❌ Failed to fetch exercise {ex_id}: {res.status_code}")
            continue
        ex = res.json()
        exercise_metadata[ex_id] = {
            "name": ex.get("name", ""),
            "primary_muscle_group": ex.get("muscle_group", None),
            "secondary_muscle_groups": [mg["name"] for mg in ex.get("secondary_muscle_groups", [])],
            "all_muscle_groups": ex.get("muscle_groups", [])
        }
    return exercise_metadata

def save_to_cache(metadata):
    os.makedirs("cache", exist_ok=True)
    with open("cache/exercise_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"✅ Saved metadata for {len(metadata)} exercises")

if __name__ == "__main__":
    ids = get_all_exercise_ids()
    print(f"🔍 Found {len(ids)} unique exercise IDs in cached workouts")
    meta = fetch_exercise_metadata(ids)
    save_to_cache(meta)

