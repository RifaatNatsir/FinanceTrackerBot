function doPost(e) {
  try {
    // Parsing data JSON yang dikirim oleh Bot Python
    var data = JSON.parse(e.postData.contents);
    var action = data.action;
    var userId = data.user_id;
    
    // Buka Spreadsheet saat ini
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    
    // Dinamis: Buat/Pilih Sheet berdasarkan User ID agar tiap pengguna terpisah
    var sheetName = "Data_" + userId;
    var sheet = ss.getSheetByName(sheetName);
    
    // Jika sheet untuk user tersebut belum ada, buat baru
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
      sheet.appendRow(["Tanggal", "Tipe", "Nominal", "Keterangan"]);
      // Tebalkan header
      sheet.getRange("A1:D1").setFontWeight("bold");
    }
    
    if (action === "append_row") {
      // Manual Text Input
      sheet.appendRow([data.date, data.type, data.amount, data.description]);
    } 
    else if (action === "append_multiple") {
      // Batch mutasi Excel
      var rows = data.rows;
      var values = [];
      for (var i = 0; i < rows.length; i++) {
        values.push([rows[i].date, rows[i].type, rows[i].amount, rows[i].description]);
      }
      var lastRow = sheet.getLastRow();
      // Menyisipkan semuanya sekaligus untuk menghindari limit eksekusi
      sheet.getRange(lastRow + 1, 1, values.length, values[0].length).setValues(values);
    }
    
    // Balas kembali ke bot Python bahwa sukses
    return ContentService.createTextOutput(JSON.stringify({"status": "success"}))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": error.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
