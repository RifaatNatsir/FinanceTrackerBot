import os
import telebot
import traceback
import threading
import time
from datetime import datetime, timezone, timedelta
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from parser import parse_manual_input, parse_bni_statement
from sheets_helper import append_row, append_multiple_rows, set_setting, get_reminders, get_summary_data, get_export_info
import io
import requests
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set. Please set it in Koyeb/Render.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)
user_budget_temp = {}

@app.route('/')
def home():
    return "Bot Keuangan BNI is running 24/7!"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "Halo! 👋 Saya bot pencatat keuangan cloud (Render).\n\n"
        "1️⃣ <b>Manual Input:</b>\n"
        "Ketik: <code>[Pemasukan/Pengeluaran] [Nominal] [Deskripsi]</code>\n"
        "Contoh: <code>Pengeluaran 50000 Makan</code>\n\n"
        "2️⃣ <b>Upload Mutasi BNI:</b>\n"
        "Kirim file CSV/Excel mutasi rekening Anda.\n\n"
        "3️⃣ <b>Atur Budget & Pengingat:</b>\n"
        "Ketik /atur untuk menyetel batas pengeluaran bulanan."
    )
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['atur', 'setting'])
def command_atur(message):
    msg = bot.reply_to(message, "Silakan masukkan maksimal budget pengeluaran Anda untuk bulan ini (contoh: 5000000):")
    bot.register_next_step_handler(msg, process_budget_step)

def process_budget_step(message):
    try:
        budget = float(message.text.replace('.', '').replace(',', ''))
        user_budget_temp[message.from_user.id] = budget
        
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Pagi (08:00 WIB)", callback_data="time_08"),
            InlineKeyboardButton("Siang (12:00 WIB)", callback_data="time_12"),
            InlineKeyboardButton("Malam (20:00 WIB)", callback_data="time_20"),
            InlineKeyboardButton("Matikan Pengingat", callback_data="time_off")
        )
        bot.reply_to(message, f"Budget Anda diatur ke <b>Rp {budget:,.0f}</b>.\n\nKapan Anda ingin diingatkan mengenai sisa budget setiap harinya?", reply_markup=markup, parse_mode='HTML')
    except Exception:
        bot.reply_to(message, "Nominal tidak valid. Harap masukkan angka saja. Ketik /atur untuk mengulang.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
def callback_time(call):
    time_val = call.data.split('_')[1] # '08', '12', '20', or 'off'
    budget = user_budget_temp.get(call.from_user.id, 0)
    
    success = set_setting(str(call.from_user.id), budget, time_val)
    
    if success:
        if time_val == 'off':
            text = "✅ Pengingat harian berhasil <b>dimatikan</b>."
        else:
            text = f"✅ <b>Berhasil!</b> Anda akan diingatkan setiap jam {time_val}:00 WIB mengenai sisa budget Anda."
    else:
        text = "❌ Gagal menyimpan pengaturan ke Google Sheets."
        
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode='HTML')

user_summary_temp = {}

@bot.message_handler(commands=['pemasukan', 'pengeluaran'])
def command_check_summary(message):
    cmd = message.text.replace('/', '').lower().split('@')[0]
    try:
        msg = bot.reply_to(message, "⏳ Mengambil data dari Cloud...")
        data = get_summary_data(str(message.from_user.id))
        
        if not data:
            bot.edit_message_text("Belum ada data keuangan yang tercatat.", chat_id=message.chat.id, message_id=msg.message_id)
            return
            
        user_summary_temp[message.from_user.id] = data
        
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        buttons = []
        for row in data:
            bulan = row['bulan']
            cb_data = f"sum_{'in' if cmd == 'pemasukan' else 'out'}_{bulan}"
            buttons.append(InlineKeyboardButton(bulan, callback_data=cb_data))
        markup.add(*buttons)
        
        bot.edit_message_text(f"Pilih bulan untuk melihat total <b>{cmd.capitalize()}</b>:", 
                              chat_id=message.chat.id, message_id=msg.message_id, reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        bot.edit_message_text(f"❌ Terjadi kesalahan: {str(e)}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('sum_'))
def callback_summary(call):
    parts = call.data.split('_', 2)
    if len(parts) < 3: return
    tipe_short = parts[1]
    bulan = parts[2]
    
    tipe_str = "Pemasukan" if tipe_short == 'in' else "Pengeluaran"
    data = user_summary_temp.get(call.from_user.id, [])
    
    nominal = 0
    found = False
    for row in data:
        if row['bulan'] == bulan:
            nominal = row['pemasukan'] if tipe_short == 'in' else row['pengeluaran']
            found = True
            break
            
    if not found:
        bot.answer_callback_query(call.id, "Data sudah kadaluarsa. Silakan ketik perintah lagi.")
        return
        
    is_current_month = False
    try:
        now = datetime.now(timezone(timedelta(hours=7)))
        parts_b = bulan.split(" ")
        month_names = {"Jan":1, "Feb":2, "Mar":3, "Apr":4, "May":5, "Jun":6, "Jul":7, "Aug":8, "Sep":9, "Oct":10, "Nov":11, "Dec":12}
        if len(parts_b) == 2:
            m_num = month_names.get(parts_b[0], 0)
            y_num = int(parts_b[1])
            if now.year == y_num and now.month == m_num:
                is_current_month = True
    except:
        pass
        
    label = "Sementara" if is_current_month else "Total"
    text = f"📊 <b>{label} {tipe_str}</b> Anda untuk bulan <b>{bulan}</b> adalah:\n\n<b>Rp {nominal:,.0f}</b>"
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode='HTML')

@bot.message_handler(commands=['unduh', 'export'])
def command_unduh(message):
    try:
        msg = bot.reply_to(message, "⏳ Mengambil daftar bulan dari Cloud...")
        data = get_summary_data(str(message.from_user.id))
        
        if not data:
            bot.edit_message_text("Belum ada data keuangan yang tercatat.", chat_id=message.chat.id, message_id=msg.message_id)
            return
            
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        buttons = []
        for row in data:
            bulan = row['bulan']
            cb_data = f"dl_{bulan}"
            buttons.append(InlineKeyboardButton(bulan, callback_data=cb_data))
        markup.add(*buttons)
        
        bot.edit_message_text("Pilih bulan yang ingin Anda unduh laporannya:", 
                              chat_id=message.chat.id, message_id=msg.message_id, reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        bot.edit_message_text(f"❌ Terjadi kesalahan: {str(e)}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))
def callback_dl_bulan(call):
    bulan = call.data.split('_', 1)[1]
    
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("📄 PDF", callback_data=f"fmt_pdf_{bulan}"),
        InlineKeyboardButton("📊 Excel (.xlsx)", callback_data=f"fmt_xlsx_{bulan}")
    )
    
    bot.edit_message_text(f"Pilih format file untuk laporan bulan <b>{bulan}</b>:", 
                          chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('fmt_'))
def callback_dl_format(call):
    parts = call.data.split('_', 2)
    fmt = parts[1] # 'pdf' or 'xlsx'
    bulan = parts[2]
    
    bot.edit_message_text(f"⏳ Sedang membuat file {fmt.upper()} untuk {bulan}...", chat_id=call.message.chat.id, message_id=call.message.message_id)
    
    try:
        ss_id, gid = get_export_info(str(call.from_user.id), bulan)
        
        if not ss_id or gid is None:
            raise ValueError("Gagal mendapatkan ID Spreadsheet. PASTIKAN Anda sudah meng-update dan DEPLOY ulang Google Apps Script ke versi terbaru!")
            
        if fmt == "pdf":
            url = f"https://docs.google.com/spreadsheets/export?id={ss_id}&exportFormat=pdf&gid={gid}"
            filename = f"Laporan_Keuangan_{bulan}.pdf"
        else:
            url = f"https://docs.google.com/spreadsheets/export?id={ss_id}&exportFormat=xlsx&gid={gid}"
            filename = f"Laporan_Keuangan_{bulan}.xlsx"
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, allow_redirects=True)
        
        if response.status_code == 200:
            if 'text/html' in response.headers.get('Content-Type', '').lower():
                bot.edit_message_text("❌ Gagal mengunduh. Akses file Spreadsheet Anda masih <b>Terkunci (Private)</b>.\n\nSilakan buka file Spreadsheet Anda, klik tombol <b>Bagikan (Share)</b>, lalu ubah akses menjadi <b>'Siapa saja yang memiliki link' (Anyone with the link)</b>.", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')
                return
                
            file_stream = io.BytesIO(response.content)
            file_stream.name = filename
            
            bot.send_document(call.message.chat.id, file_stream, caption=f"✅ Laporan <b>{bulan}</b> berhasil diunduh!", parse_mode='HTML')
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text(f"❌ Gagal mengunduh file dari Google Sheets. (Error {response.status_code})\nPastikan akses file adalah 'Siapa saja yang memiliki link'.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ Terjadi kesalahan: {str(e)}", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.message_handler(content_types=['document'])
def handle_document(message):
    try:
        msg = bot.reply_to(message, "⏳ Mengunduh dan memproses file di Cloud...")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        filename = message.document.file_name
        
        # Simpan sementara (Koyeb ephemeral storage)
        temp_path = f"/tmp/{filename}"
        with open(temp_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        # Parse data mutasi menggunakan Pandas
        with open(temp_path, 'rb') as f:
            file_bytes = f.read()
            
        rows = parse_bni_statement(file_bytes, filename)
        
        # PENTING: Segera hapus file setelah diproses agar tidak memenuhi storage
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        if not rows:
            bot.edit_message_text("⚠️ Tidak ada transaksi valid yang ditemukan dalam file.",
                                  chat_id=message.chat.id, message_id=msg.message_id)
            return
            
        # Kirim data ke Google Apps Script (Webhook pengganti Google Cloud Console)
        success, url = append_multiple_rows(rows, message.from_user.id)
        
        if success:
            bot.edit_message_text(f"✅ Berhasil memproses {len(rows)} transaksi!\n\n"
                                  f"📂 <b>Akses file pribadi Anda di sini:</b>\n<a href='{url}'>Buka File</a>",
                                  chat_id=message.chat.id, message_id=msg.message_id, parse_mode='HTML', disable_web_page_preview=True)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Terjadi kesalahan: {str(e)}")
        traceback.print_exc()

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        # Parsing teks dengan mengirimkan waktu asli pengguna mengirim pesan
        row_data = parse_manual_input(message.text, message_timestamp=message.date)
        
        # Kirim data ke Google Apps Script
        success, url = append_row(row_data[0], row_data[1], row_data[2], row_data[3], message.from_user.id)
        
        if success:
            desc = str(row_data[3]).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            bot.reply_to(message, f"✅ <b>Berhasil dicatat di Cloud!</b>\n\n"
                                  f"📌 Tipe: {row_data[1]}\n"
                                  f"💵 Nominal: {row_data[2]:,.0f}\n"
                                  f"📝 Keterangan: {desc}\n\n"
                                  f"📂 <b>File Sheets Anda:</b>\n<a href='{url}'>Buka File</a>",
                                  parse_mode='HTML', disable_web_page_preview=True)
    except ValueError as e:
        bot.reply_to(message, f"⚠️ {str(e)}")
    except Exception as e:
        bot.reply_to(message, f"❌ Terjadi kesalahan sistem: {str(e)}")
        traceback.print_exc()

def run_bot():
    print("Menghapus webhook lama (jika ada)...")
    bot.remove_webhook()
    print("Bot is running continuously in Cloud (Long Polling)...")
    bot.infinity_polling()
    
def reminder_loop():
    last_notified_hour = -1
    while True:
        try:
            now = datetime.now(timezone(timedelta(hours=7))) # WIB
            if now.minute == 0 and now.hour != last_notified_hour:
                last_notified_hour = now.hour
                current_hour_str = now.strftime("%H")
                
                reminders = get_reminders(current_hour_str)
                for rem in reminders:
                    uid = rem['user_id']
                    budget = float(rem.get('budget', 0))
                    pengeluaran = float(rem.get('pengeluaran', 0))
                    sisa = budget - pengeluaran
                    
                    if sisa < 0:
                        msg = f"🚨 <b>PERINGATAN BUDGET</b> 🚨\n\nAnda telah melebihi batas budget bulan ini!\nBudget: Rp {budget:,.0f}\nPengeluaran: Rp {pengeluaran:,.0f}\n<b>Overbudget: Rp {abs(sisa):,.0f}</b>"
                    elif sisa < (0.2 * budget):
                        msg = f"⚠️ <b>HAMPIR HABIS</b> ⚠️\n\nSisa budget Anda mulai menipis!\nBudget: Rp {budget:,.0f}\nPengeluaran: Rp {pengeluaran:,.0f}\n<b>Sisa: Rp {sisa:,.0f}</b>"
                    else:
                        msg = f"📊 <b>Laporan Budget Harian</b>\n\nBudget: Rp {budget:,.0f}\nPengeluaran: Rp {pengeluaran:,.0f}\n<b>Sisa: Rp {sisa:,.0f}</b>"
                        
                    bot.send_message(uid, msg, parse_mode='HTML')
        except Exception as e:
            print("Error in reminder_loop:", e)
            
        time.sleep(30) # Cek setiap 30 detik

if __name__ == "__main__":
    # Jalankan bot di thread latar belakang
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Jalankan background job pengingat budget
    reminder_thread = threading.Thread(target=reminder_loop)
    reminder_thread.start()
    
    # Jalankan server web palsu (Flask) agar Render tidak mematikan aplikasi kita
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
