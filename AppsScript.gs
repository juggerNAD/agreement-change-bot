/**
 * Agreement Change Request Bot — Sheet backend
 * -----------------------------------------------
 * Paste this into Extensions > Apps Script (in the Google Sheet),
 * then deploy as a Web App. See README for full steps.
 */

const SHEET_TAB = "Submissions";

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(SHEET_TAB);

    if (!sheet) {
      sheet = ss.insertSheet(SHEET_TAB);
      sheet.appendRow([
        "Timestamp",
        "Submitted By",
        "Username",
        "Client Name",
        "Agreement Sent",
        "Changes Requested",
      ]);
    }

    sheet.appendRow([
      data.timestamp || new Date().toISOString(),
      data.submitted_by || "",
      data.username || "",
      data.client_name || "",
      data.agreement_sent || "",
      data.changes_requested || "",
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({ status: "ok" }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({ status: "Agreement Change Request backend is live" }))
    .setMimeType(ContentService.MimeType.JSON);
}
