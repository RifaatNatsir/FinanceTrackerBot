function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var action = data.action;
    var userId = data.user_id.toString();
    
    var props = PropertiesService.getScriptProperties();
    var ssId = props.getProperty(userId);
    var ss;
    
    if (!ssId) {
      ss = SpreadsheetApp.create("Catatan_Keuangan_" + userId);
      ssId = ss.getId();
      props.setProperty(userId, ssId);
      
      // Ubah nama sheet default menjadi "Ringkasan Total"
      var defaultSheet = ss.getSheets()[0];
      defaultSheet.setName("Ringkasan Total");
      defaultSheet.appendRow(["Bulan", "Total Pemasukan", "Total Pengeluaran", "Total Bersih"]);
      defaultSheet.getRange("A1:D1").setFontWeight("bold").setBackground("#f3f3f3");
      defaultSheet.setColumnWidth(1, 150);
      defaultSheet.setColumnWidth(2, 150);
      defaultSheet.setColumnWidth(3, 150);
      defaultSheet.setColumnWidth(4, 150);
    } else {
      ss = SpreadsheetApp.openById(ssId);
    }
    
    // Fungsi untuk mendapatkan nama sheet berdasarkan bulan/tahun (cth: "Aug 2026")
    function getMonthYear(dateStr) {
      // Format dari Python: "01 Aug 2026 (16:45)"
      var parts = dateStr.split(" ");
      if (parts.length >= 3) {
        return parts[1] + " " + parts[2];
      }
      return "Umum";
    }
    
    // Fungsi memproses satu baris (membuat sheet bulanan, duplikat, dll)
    function processRow(rowDate, rowType, rowAmount, rowDesc) {
      var sheetName = getMonthYear(rowDate);
      var sheet = ss.getSheetByName(sheetName);
      var isNewSheet = false;
      
      if (!sheet) {
        sheet = ss.insertSheet(sheetName);
        sheet.appendRow(["Tanggal", "Tipe", "Nominal", "Keterangan"]);
        sheet.getRange("A1:D1").setFontWeight("bold").setBackground("#f3f3f3");
        
        var rule1 = SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("Pemasukan").setBackground("#CCFFCC").setRanges([sheet.getRange("B2:B")]).build();
        var rule2 = SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("Pengeluaran").setBackground("#FFCCCC").setRanges([sheet.getRange("B2:B")]).build();
        sheet.setConditionalFormatRules([rule1, rule2]);
        
        sheet.getRange("C2:C").setNumberFormat("#,##0");
        sheet.setColumnWidth(1, 160);
        sheet.setColumnWidth(2, 100);
        sheet.setColumnWidth(3, 120);
        sheet.setColumnWidth(4, 300);
        isNewSheet = true;
      }
      
      // Cek Duplikat
      var dataRange = sheet.getDataRange().getValues();
      var isDuplicate = false;
      for (var j = 1; j < dataRange.length; j++) {
        if (dataRange[j][0] == rowDate && dataRange[j][1] == rowType && dataRange[j][2] == rowAmount && dataRange[j][3] == rowDesc) {
          isDuplicate = true;
          break;
        }
      }
      
      if (!isDuplicate) {
        sheet.appendRow([rowDate, rowType, rowAmount, rowDesc]);
        
        // Daftarkan ke sheet "Ringkasan Total" secara Real-Time (hanya sekali saat sheet baru dibuat)
        if (isNewSheet) {
          var summarySheet = ss.getSheetByName("Ringkasan Total");
          if (summarySheet) {
            var formulaIn = "=SUMIF('" + sheetName + "'!B:B; \"Pemasukan\"; '" + sheetName + "'!C:C)";
            var formulaOut = "=SUMIF('" + sheetName + "'!B:B; \"Pengeluaran\"; '" + sheetName + "'!C:C)";
            var lr = summarySheet.getLastRow() + 1;
            var formulaSaldo = "=B" + lr + "-C" + lr;
            
            summarySheet.appendRow([sheetName, formulaIn, formulaOut, formulaSaldo]);
            summarySheet.getRange("B2:D").setNumberFormat("#,##0");
          }
        }
        return true;
      }
      return false;
    }
    
    var addedCount = 0;
    
    if (action === "append_row") {
      if (processRow(data.date, data.type, data.amount, data.description)) addedCount++;
    } 
    else if (action === "append_multiple") {
      var rows = data.rows;
      for (var i = 0; i < rows.length; i++) {
        if (processRow(rows[i].date, rows[i].type, rows[i].amount, rows[i].description)) addedCount++;
      }
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      "status": "success",
      "url": ss.getUrl(),
      "added": addedCount
    })).setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      "status": "error", 
      "message": error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
