import os
import telebot
import traceback
import threading
from flask import Flask
from parser import parse_manual_input, parse_bni_statement
from sheets_helper import append_row, append_multiple_rows

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set. Please set it in Koyeb/Render.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Keuangan BNI is running 24/7!"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "Halo! 👋 Saya bot pencatat keuangan cloud (Koyeb).\n\n"
        "1️⃣ *Manual Input:*\n"
        "Ketik: `[Pemasukan/Pengeluaran] [Nominal] [Deskripsi]`\n"
        "Contoh: `Pengeluaran 50000 Makan`\n\n"
        "2️⃣ *Upload Mutasi BNI:*\n"
        "Kirim file CSV/Excel mutasi rekening Anda."
    )
    bot.reply_to(message, text, parse_mode='Markdown')

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
        success = append_multiple_rows(rows, message.from_user.id)
        
        if success:
            bot.edit_message_text(f"✅ Berhasil memproses {len(rows)} transaksi & menyimpannya ke Google Sheets Anda!",
                                  chat_id=message.chat.id, message_id=msg.message_id)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Terjadi kesalahan: {str(e)}")
        traceback.print_exc()

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        # Parsing teks
        row_data = parse_manual_input(message.text)
        
        # Kirim data ke Google Apps Script
        append_row(row_data[0], row_data[1], row_data[2], row_data[3], message.from_user.id)
        
        bot.reply_to(message, f"✅ *Berhasil dicatat di Cloud!*\n\n"
                              f"📌 Tipe: {row_data[1]}\n"
                              f"💵 Nominal: {row_data[2]:,.0f}\n"
                              f"📝 Keterangan: {row_data[3]}",
                              parse_mode='Markdown')
    except ValueError as e:
        bot.reply_to(message, f"⚠️ {str(e)}")
    except Exception as e:
        bot.reply_to(message, f"❌ Terjadi kesalahan sistem: {str(e)}")
        traceback.print_exc()

def run_bot():
    print("Bot is running continuously in Cloud (Long Polling)...")
    bot.infinity_polling()

if __name__ == "__main__":
    # Jalankan bot di thread latar belakang
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Jalankan server web palsu (Flask) agar Render tidak mematikan aplikasi kita
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
