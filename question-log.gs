// Pioneer DataLabs question log: Google Apps Script web app.
//
// What it does: receives every question the ask engine handles and appends it
// to the spreadsheet this script is bound to. All questions land on the
// "All questions" tab; questions the engine could not answer also land on
// their own "Unanswered" tab, which is the research agenda input.
//
// Setup (once, about five minutes; full walkthrough in SETUP.md Step 6):
//   1. sheets.new  ->  name the spreadsheet, e.g. "DataLabs question log"
//   2. Extensions > Apps Script  ->  delete the sample code, paste this file
//   3. Deploy > New deployment > Web app
//        Execute as: Me        Who has access: Anyone
//   4. Copy the web app URL into Netlify as QUESTION_LOG_URL and redeploy
//
// The sheet is Excel-compatible: File > Download > Microsoft Excel (.xlsx),
// or open it directly in Excel via Google Drive.

function doPost(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var entry = JSON.parse(e.postData.contents);
  var when = entry.at || new Date().toISOString();

  var all = ss.getSheetByName('All questions') || ss.insertSheet('All questions');
  if (all.getLastRow() === 0) {
    all.appendRow(['When (UTC)', 'Question', 'Outcome', 'Tool', 'Engine note']);
    all.setFrozenRows(1);
  }
  all.appendRow([when, entry.q || '', entry.type || '', entry.tool || '', entry.note || '']);

  if (entry.type === 'none') {
    var gaps = ss.getSheetByName('Unanswered') || ss.insertSheet('Unanswered');
    if (gaps.getLastRow() === 0) {
      gaps.appendRow(['When (UTC)', 'Question', 'Engine note']);
      gaps.setFrozenRows(1);
    }
    gaps.appendRow([when, entry.q || '', entry.note || '']);
  }

  return ContentService.createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
