def get_access_token():
    # TEMP STUB: Replace this with real logic if needed
    return "your-token-here"

def prepare_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "API-TOKEN": token,
        "Content-Type": "application/json"
    }

def calculate_averages(summary, keys):
    if not summary or not keys:
        return {}
    averages = {}
    for key in keys:
        values = [day["macros"].get(key, 0) for day in summary if "macros" in day]
        if values:
            averages[key] = sum(values) / len(values)
        else:
            averages[key] = 0
    return averages

def fetch_diary_summary(token, client_id, start, end, include_food=False):
    # TEMP STUB: Not needed for workout dashboard
    return {}
