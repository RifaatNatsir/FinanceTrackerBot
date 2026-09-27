function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var action = data.action;
    var userId = data.user_id.toString();
    
    var props = PropertiesService.getScriptProperties();
    var ssId = props.getProperty(userId);
    var ss;
    var sheet;
    
    if (!ssId) {
      // Buat file Spreadsheet BARU khusus untuk User ID ini
      ss = SpreadsheetApp.create("Catatan_Keuangan_" + userId);
      ssId = ss.getId();
      props.setProperty(userId, ssId);
      
      sheet = ss.getActiveSheet();
      sheet.setName("Mutasi");
      
      // Header
      sheet.appendRow(["Tanggal", "Tipe", "Nominal", "Keterangan"]);
      sheet.getRange("A1:D1").setFontWeight("bold").setBackground("#f3f3f3");
      
      // Conditional Formatting (Warna Latar untuk Tipe)
      var rule1 = SpreadsheetApp.newConditionalFormatRule()
        .whenTextEqualTo("Pemasukan")
        .setBackground("#CCFFCC") // Hijau
        .setRanges([sheet.getRange("B2:B")])
        .build();
      var rule2 = SpreadsheetApp.newConditionalFormatRule()
        .whenTextEqualTo("Pengeluaran")
        .setBackground("#FFCCCC") // Merah
        .setRanges([sheet.getRange("B2:B")])
        .build();
      sheet.setConditionalFormatRules([rule1, rule2]);
      
      // Format Angka Ribuan
      sheet.getRange("C2:C").setNumberFormat("#,##0");
      
      // Format Tanggal
      sheet.getRange("A2:A").setNumberFormat("dd MMM yyyy (HH:mm)");
      
      // Lebarkan kolom
      sheet.setColumnWidth(1, 160);
      sheet.setColumnWidth(2, 100);
      sheet.setColumnWidth(3, 120);
      sheet.setColumnWidth(4, 300);
    } else {
      // Buka Spreadsheet yang sudah ada milik user
      ss = SpreadsheetApp.openById(ssId);
      sheet = ss.getActiveSheet();
    }
    
    if (action === "append_row") {
      sheet.appendRow([data.date, data.type, data.amount, data.description]);
    } 
    else if (action === "append_multiple") {
      var rows = data.rows;
      var values = [];
      for (var i = 0; i < rows.length; i++) {
        values.push([rows[i].date, rows[i].type, rows[i].amount, rows[i].description]);
      }
      var lastRow = sheet.getLastRow();
      sheet.getRange(lastRow + 1, 1, values.length, values[0].length).setValues(values);
    }
    
    // Sortir secara Kronologis berdasarkan Kolom 1 (Tanggal)
    var lastRowAfter = sheet.getLastRow();
    if (lastRowAfter > 1) {
      var dataRange = sheet.getRange(2, 1, lastRowAfter - 1, sheet.getLastColumn());
      dataRange.sort({column: 1, ascending: true});
    }
    
    // Kembalikan URL dari spreadsheet pribadi user
    return ContentService.createTextOutput(JSON.stringify({
      "status": "success",
      "url": ss.getUrl()
    })).setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      "status": "error", 
      "message": error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
