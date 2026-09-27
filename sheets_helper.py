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
        return True
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
        return True
    else:
        raise Exception(f"Gagal mengirim batch ke Google Apps Script: {response.text}")
