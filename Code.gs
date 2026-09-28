function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var action = data.action;
    var userId = data.user_id.toString();
    
    var props = PropertiesService.getScriptProperties();
    var ssId = props.getProperty(userId);
    var ss;
    
    // Fungsi untuk membuat Spreadsheet baru dari nol
    function createNewSpreadsheet() {
      var newSs = SpreadsheetApp.create("Catatan_Keuangan_" + userId);
      var newSsId = newSs.getId();
      props.setProperty(userId, newSsId);
      
      // Buka akses (Sharing) agar "Siapa saja yang memiliki link" bisa mengedit/melihat
      try {
        var file = DriveApp.getFileById(newSsId);
        file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.EDIT);
      } catch (e) {
        // Abaikan jika ada error permission, tapi biasanya berhasil
      }
      
      // Ubah nama sheet default menjadi "Ringkasan Total"
      var defaultSheet = newSs.getSheets()[0];
      defaultSheet.setName("Ringkasan Total");
      defaultSheet.appendRow(["Bulan", "Total Pemasukan", "Total Pengeluaran", "Total Bersih"]);
      defaultSheet.getRange("A1:D1").setFontWeight("bold").setBackground("#f3f3f3");
      defaultSheet.setColumnWidth(1, 150);
      defaultSheet.setColumnWidth(2, 150);
      defaultSheet.setColumnWidth(3, 150);
      defaultSheet.setColumnWidth(4, 150);
      return newSs;
    }
    
    if (!ssId) {
      ss = createNewSpreadsheet();
    } else {
      try {
        ss = SpreadsheetApp.openById(ssId);
      } catch (err) {
        // Jika file sudah dihapus permanen oleh pengguna dari Google Drive
        props.deleteProperty(userId);
        ss = createNewSpreadsheet();
      }
    }
    
    function getMonthYear(dateStr) {
      var parts = dateStr.split(" ");
      if (parts.length >= 3) {
        return parts[1] + " " + parts[2];
      }
      return "Umum";
    }
    
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
      
      // Hapus baris total lama jika ada di akhir baris
      var dataRange = sheet.getDataRange().getValues();
      var isDuplicate = false;
      var rowsToDelete = [];
      
      // Cek dari bawah ke atas
      for (var j = dataRange.length - 1; j >= 1; j--) {
        if (dataRange[j][1] == "Pemasukan:" || dataRange[j][1] == "Pengeluaran:") {
          rowsToDelete.push(j + 1); // 1-based index
        }
        else if (dataRange[j][0] == rowDate && dataRange[j][1] == rowType && dataRange[j][2] == rowAmount && dataRange[j][3] == rowDesc) {
          isDuplicate = true;
        }
      }
      
      // Hapus baris total lama (harus dari bawah ke atas agar index baris tidak bergeser)
      for (var k = 0; k < rowsToDelete.length; k++) {
        sheet.deleteRow(rowsToDelete[k]);
      }
      
      if (!isDuplicate) {
        sheet.appendRow([rowDate, rowType, rowAmount, rowDesc]);
        
        if (isNewSheet) {
          var summarySheet = ss.getSheetByName("Ringkasan Total");
          if (summarySheet) {
            var formulaIn = "=SUMIF('" + sheetName + "'!B:B, \"Pemasukan\", '" + sheetName + "'!C:C)";
            var formulaOut = "=SUMIF('" + sheetName + "'!B:B, \"Pengeluaran\", '" + sheetName + "'!C:C)";
            var lr = summarySheet.getLastRow() + 1;
            var formulaSaldo = "=B" + lr + "-C" + lr;
            
            summarySheet.appendRow([sheetName, formulaIn, formulaOut, formulaSaldo]);
            summarySheet.getRange("B2:D").setNumberFormat("#,##0");
          }
        }
        return sheetName;
      }
      return sheetName;
    }
    
    var modifiedSheets = {};
    var addedCount = 0;
    
    if (action === "append_row") {
      var sName = processRow(data.date, data.type, data.amount, data.description);
      if (sName) { modifiedSheets[sName] = true; addedCount++; }
    } 
    else if (action === "append_multiple") {
      var rows = data.rows;
      for (var i = 0; i < rows.length; i++) {
        var sName = processRow(rows[i].date, rows[i].type, rows[i].amount, rows[i].description);
        if (sName) { modifiedSheets[sName] = true; addedCount++; }
      }
    }
    
    if (action === "set_setting") {
      var budget = data.budget;
      var reminder_time = data.reminder_time;
      var settingKey = "settings_" + userId;
      props.setProperty(settingKey, JSON.stringify({
        budget: budget,
        reminder_time: reminder_time
      }));
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    if (action === "get_reminders") {
      var hour = data.hour.toString();
      var allProps = props.getProperties();
      var reminders = [];
      
      var now = new Date();
      var monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      var currentMonthName = monthNames[now.getMonth()] + " " + now.getFullYear();
      
      for (var key in allProps) {
        if (key.indexOf("settings_") === 0) {
          var uId = key.split("_")[1];
          var settingsStr = allProps[key];
          try {
            var settings = JSON.parse(settingsStr);
            if (settings.reminder_time === hour) {
               var userSsId = allProps[uId];
               if (userSsId) {
                  var userSs = SpreadsheetApp.openById(userSsId);
                  var summarySheet = userSs.getSheetByName("Ringkasan Total");
                  var pengeluaran = 0;
                  
                  if (summarySheet) {
                    var summaryData = summarySheet.getDataRange().getValues();
                    for (var i = 1; i < summaryData.length; i++) {
                      if (summaryData[i][0] === currentMonthName) {
                        pengeluaran = parseFloat(summaryData[i][2]) || 0;
                        break;
                      }
                    }
                  }
                  
                  reminders.push({
                    user_id: uId,
                    budget: settings.budget,
                    pengeluaran: pengeluaran
                  });
               }
            }
          } catch(e) {}
        }
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "reminders": reminders
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Tambahkan kembali baris TOTAL di akhir setiap sheet yang dimodifikasi
    for (var s in modifiedSheets) {
      var sheet = ss.getSheetByName(s);
      if (sheet) {
        // Tentukan kata TOTAL SEMENTARA atau TOTAL KESELURUHAN berdasarkan apakah bulan tersebut sudah terlewat
        var isPastMonth = false;
        var dateParts = s.split(" "); // cth: ["Aug", "2026"]
        if (dateParts.length == 2) {
          var monthNames = {"Jan":0, "Feb":1, "Mar":2, "Apr":3, "May":4, "Jun":5, "Jul":6, "Aug":7, "Sep":8, "Oct":9, "Nov":10, "Dec":11};
          var sheetMonth = monthNames[dateParts[0]];
          var sheetYear = parseInt(dateParts[1], 10);
          
          var now = new Date();
          var currentMonth = now.getMonth();
          var currentYear = now.getFullYear();
          
          // Jika tahun sudah lewat, atau tahun sama tapi bulan sudah lewat, berarti bulan tersebut sudah berakhir
          if (sheetYear < currentYear || (sheetYear == currentYear && sheetMonth < currentMonth)) {
            isPastMonth = true;
          }
        }
        
        var labelTotal = isPastMonth ? "TOTAL KESELURUHAN" : "TOTAL SEMENTARA";
        
        var lr = sheet.getLastRow();
        // Menggunakan spesifik range (misal B2:B100) untuk menghindari error Circular Dependency
        var formulaIn = "=SUMIF(B2:B" + lr + ", \"Pemasukan\", C2:C" + lr + ")";
        var formulaOut = "=SUMIF(B2:B" + lr + ", \"Pengeluaran\", C2:C" + lr + ")";
        
        // Buat 2 baris terpisah agar sangat rapi dan nilai nominalnya bisa diformat angka otomatis
        sheet.appendRow(["", "Pemasukan:", formulaIn, ""]);
        sheet.appendRow([labelTotal, "Pengeluaran:", formulaOut, ""]);
        
        var newLr = sheet.getLastRow();
        sheet.getRange(newLr - 1, 1, 2, 4).setBackground("#ffffcc").setFontWeight("bold");
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

// JALANKAN FUNGSI INI SEKALI SAJA DARI EDITOR UNTUK MEMANCING IZIN GOOGLE DRIVE
function OtorisasiGoogleDrive() {
  DriveApp.getFiles();
  Logger.log("Izin Google Drive berhasil diberikan!");
}
