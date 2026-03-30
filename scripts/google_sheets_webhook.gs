/**
 * Google Apps Script webhook bridge for spreadsheet changes.
 *
 * Script properties required:
 * - WEBHOOK_URL:   https://<your-domain>/webhooks/google-sheets
 * - WEBHOOK_TOKEN: must match GOOGLE_SHEETS_WEBHOOK_TOKEN on backend
 *
 * After setting properties, run setupInstallableTriggers() once.
 */

function handleEdit(e) {
  postWebhook_("edit", e);
}

function handleChange(e) {
  postWebhook_("change", e);
}

function testWebhook() {
  postWebhook_("manual_test", {
    source: SpreadsheetApp.getActiveSpreadsheet(),
  });
}

function setupInstallableTriggers() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  if (!spreadsheet) {
    throw new Error("Active spreadsheet is required.");
  }

  const handlers = new Set(["handleEdit", "handleChange"]);
  const existingTriggers = ScriptApp.getProjectTriggers();
  for (const trigger of existingTriggers) {
    if (handlers.has(trigger.getHandlerFunction())) {
      ScriptApp.deleteTrigger(trigger);
    }
  }

  ScriptApp.newTrigger("handleEdit")
    .forSpreadsheet(spreadsheet)
    .onEdit()
    .create();

  ScriptApp.newTrigger("handleChange")
    .forSpreadsheet(spreadsheet)
    .onChange()
    .create();
}

function postWebhook_(eventType, e) {
  const properties = PropertiesService.getScriptProperties();
  const webhookUrl = String(properties.getProperty("WEBHOOK_URL") || "").trim();
  const webhookToken = String(properties.getProperty("WEBHOOK_TOKEN") || "").trim();

  if (!webhookUrl) {
    throw new Error("WEBHOOK_URL is missing in Script Properties.");
  }
  if (!webhookToken) {
    throw new Error("WEBHOOK_TOKEN is missing in Script Properties.");
  }

  const sourceSpreadsheet = e && e.source ? e.source : SpreadsheetApp.getActiveSpreadsheet();
  const spreadsheetId = sourceSpreadsheet ? String(sourceSpreadsheet.getId()) : "";

  const payload = {
    event: String(eventType || "").trim() || "unknown",
    spreadsheetId: spreadsheetId,
    timestamp: new Date().toISOString(),
  };

  if (e && e.changeType) {
    payload.changeType = String(e.changeType);
  }

  if (e && e.range) {
    try {
      payload.sheetName = String(e.range.getSheet().getName() || "");
      payload.rangeA1 = String(e.range.getA1Notation() || "");
    } catch (error) {
      payload.rangeError = String(error);
    }
  }

  const response = UrlFetchApp.fetch(webhookUrl, {
    method: "post",
    contentType: "application/json",
    headers: {
      "X-Webhook-Token": webhookToken,
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
    followRedirects: true,
  });

  const statusCode = Number(response.getResponseCode());
  const responseText = String(response.getContentText() || "");
  if (statusCode < 200 || statusCode >= 300) {
    throw new Error(
      "Webhook call failed with status " + statusCode + ": " + responseText
    );
  }
}
