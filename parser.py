import pandas as pd
import io
from datetime import datetime
import re

MONTH_MAP = {
    'Jan': 'Jan', 'Feb': 'Feb', 'Mar': 'Mar', 'Apr': 'Apr', 'Mei': 'May', 'May': 'May',
    'Jun': 'Jun', 'Jul': 'Jul', 'Agu': 'Aug', 'Aug': 'Aug', 'Agt': 'Aug', 'Sep': 'Sep',
    'Okt': 'Oct', 'Oct': 'Oct', 'Nov': 'Nov', 'Des': 'Dec', 'Dec': 'Dec'
}

def format_date(dt):
    # Output: DD Mmm YYYY (HH:MM) -> contoh: 01 Aug 2026 (10:46)
    return dt.strftime("%d %b %Y (%H:%M)")

def parse_manual_input(text):
    parts = text.strip().split(" ", 2)
    if len(parts) < 3:
        raise ValueError("Format tidak sesuai. Gunakan: [Pemasukan/Pengeluaran] [Nominal] [Deskripsi]")
        
    tipe = parts[0].capitalize()
    if tipe not in ["Pemasukan", "Pengeluaran"]:
        raise ValueError("Tipe harus 'Pemasukan' atau 'Pengeluaran'.")
        
    try:
        amount_str = parts[1].replace('.', '').replace(',', '')
        amount = float(amount_str)
    except ValueError:
        raise ValueError("Nominal harus berupa angka.")
        
    description = parts[2]
    date_str = format_date(datetime.now())
    
    return [date_str, tipe, amount, description]

def parse_bni_statement(file_bytes, filename):
    if filename.endswith('.csv'):
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), sep=';', skiprows=4)
            if len(df.columns) < 4:
                df = pd.read_csv(io.BytesIO(file_bytes), sep=',', skiprows=4)
        except Exception:
            df = pd.read_csv(io.BytesIO(file_bytes))
    elif filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(io.BytesIO(file_bytes), header=None)
    else:
        raise ValueError("Format file tidak didukung. Harap unggah file CSV atau Excel.")

    rows_to_append = []
    
    for idx, row in df.iterrows():
        row_strs = [str(x).strip() for x in row.values if not pd.isna(x) and str(x).strip() not in ('nan', '')]
        if not row_strs: 
            continue
            
        full_text = ' '.join(row_strs)
        
        date_match = re.search(r'(\d{2})\s+([A-Za-z]{3})\s+(\d{4})', full_text)
        if not date_match: 
            continue
            
        day, month_str, year = date_match.groups()
        month_eng = MONTH_MAP.get(month_str, month_str)
        
        time_match = re.search(r'(\d{2}):(\d{2}):(\d{2})', full_text)
        if time_match:
            hour, minute, sec = time_match.groups()
        else:
            hour, minute, sec = "00", "00", "00"
            
        try:
            dt = datetime.strptime(f"{year}-{month_eng}-{day} {hour}:{minute}:{sec}", "%Y-%b-%d %H:%M:%S")
            tanggal = format_date(dt)
        except Exception:
            tanggal = f"{day} {month_eng} {year} ({hour}:{minute})"
        
        amount = 0.0
        tipe = ''
        keterangan = ''
        
        nums = [x for x in row.values if isinstance(x, (int, float)) and not pd.isna(x)]
        if len(nums) >= 2:
            amt_raw = nums[-2]
            tipe = 'Pemasukan' if amt_raw > 0 else 'Pengeluaran'
            amount = abs(float(amt_raw))
            
            desc_strs = [str(x) for x in row.values if isinstance(x, str) and not pd.isna(x)]
            desc_part = ' '.join(desc_strs).replace(date_match.group(0), '').strip()
            desc_part = re.sub(r'\d{2}:\d{2}:\d{2}\s*(WIB|WITA|WIT)?', '', desc_part).strip()
            keterangan = desc_part.replace('\n', ' ')
        else:
            matches = re.findall(r'([+-])\s*([\d,]+(?:\.\d+)?)', full_text)
            valid_matches = [m for m in matches if not (len(m[1].replace(',', '')) > 8 and ',' not in m[1])]
            
            if valid_matches:
                last_match = valid_matches[-1]
                sign = last_match[0]
                amount = float(last_match[1].replace(',', ''))
                tipe = 'Pemasukan' if sign == '+' else 'Pengeluaran'
                
                split_str = last_match[0] + last_match[1]
                if split_str in full_text:
                    desc_part = full_text.split(split_str)[0]
                else:
                    desc_part = full_text.split(last_match[0] + ' ' + last_match[1])[0]
                    
                desc_part = desc_part.replace(date_match.group(0), '').strip()
                desc_part = re.sub(r'\d{2}:\d{2}:\d{2}\s*(WIB|WITA|WIT)?', '', desc_part).strip()
                keterangan = desc_part.replace('\n', ' ')
                
        if amount > 0:
            keterangan = keterangan.strip(' -').strip()
            rows_to_append.append([tanggal, tipe, amount, keterangan])

    return rows_to_append
