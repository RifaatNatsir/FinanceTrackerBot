import os
import requests

# URL Google Apps Script Web App (diperoleh setelah deploy GAS)
GAS_URL = os.environ.get("GAS_WEBAPP_URL")

def append_row(date_str, type_str, amount, description, user_id):
    if not GAS_URL:
        raise ValueError("Variabel lingkungan 'GAS_WEBAPP_URL' belum disetel di Koyeb.")
    
    payload = {
        "action": "append_row",
        "user_id": user_id,
        "date": date_str,
        "type": type_str,
        "amount": amount,
        "description": description
    }
    
    response = requests.post(GAS_URL, json=payload)
    if response.status_code == 200:
        resp_data = response.json()
        if resp_data.get("status") == "success":
            return True, resp_data.get("url")
        else:
            raise Exception(f"GAS Error: {resp_data.get('message')}")
    else:
        raise Exception(f"Gagal mengirim ke Google Apps Script: {response.text}")

def append_multiple_rows(rows, user_id):
    if not GAS_URL:
        raise ValueError("Variabel lingkungan 'GAS_WEBAPP_URL' belum disetel di Koyeb.")
        
    if not rows:
        return True
        
    formatted_rows = []
    for r in rows:
        formatted_rows.append({
            "date": r[0],
            "type": r[1],
            "amount": r[2],
            "description": r[3]
        })
        
    payload = {
        "action": "append_multiple",
        "user_id": user_id,
        "rows": formatted_rows
    }
    
    response = requests.post(GAS_URL, json=payload)
    if response.status_code == 200:
        resp_data = response.json()
        if resp_data.get("status") == "success":
            return True, resp_data.get("url")
        else:
            raise Exception(f"GAS Error: {resp_data.get('message')}")
    else:
        raise Exception(f"Gagal mengirim batch ke Google Apps Script: {response.text}")

def set_setting(user_id, budget, reminder_time):
    if not GAS_URL:
        raise ValueError("GAS_WEBAPP_URL is not set.")
    payload = {
        "action": "set_setting",
        "user_id": user_id,
        "budget": budget,
        "reminder_time": reminder_time
    }
    response = requests.post(GAS_URL, json=payload)
    if response.status_code == 200:
        return True
    return False

def get_reminders(hour):
    if not GAS_URL:
        raise ValueError("GAS_WEBAPP_URL is not set.")
    payload = {
        "action": "get_reminders",
        "hour": str(hour)
    }
    response = requests.post(GAS_URL, json=payload)
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "success":
            return data.get("reminders", [])
    return []

def get_summary_data(user_id):
    if not GAS_URL:
        raise ValueError("GAS_WEBAPP_URL is not set.")
    payload = {
        "action": "get_summary_data",
        "user_id": user_id
    }
    response = requests.post(GAS_URL, json=payload)
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "success":
            return data.get("data", [])
        else:
            raise Exception(data.get("message", "Unknown error"))
    return []

def get_export_info(user_id, bulan):
    if not GAS_URL:
        raise ValueError("GAS_WEBAPP_URL is not set.")
    payload = {
        "action": "get_export_info",
        "user_id": user_id,
        "bulan": bulan
    }
    response = requests.post(GAS_URL, json=payload)
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "success":
            return data.get("ss_id"), data.get("gid")
        else:
            raise Exception(data.get("message", "Unknown error"))
    raise Exception("Failed to contact GAS")
