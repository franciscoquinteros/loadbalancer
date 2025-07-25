# Google Sheets Integration Setup Guide

This guide explains how to set up Google Sheets logging for the Balance Loader Bot.

## 🚀 Quick Setup (For Your Current Configuration)

**Your service account is already configured!** Follow these steps:

1. **Create a Google Spreadsheet** and copy its ID from the URL
2. **Share the spreadsheet** with: `balanceloader2025@balanceloader-467002.iam.gserviceaccount.com` (Editor permissions)
3. **Add to your .env file**:
   ```env
   GOOGLE_SHEETS_ID=your_spreadsheet_id_here
   GOOGLE_CREDENTIALS_PATH=balanceloader-467002-4124a1ff41d8.json
   ```
4. **Test with** `/test_sheets` command in your bot

---

## Prerequisites

1. A Google account with access to Google Sheets
2. A Google Cloud Platform (GCP) project

## Step 1: Create a Google Sheets Spreadsheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new spreadsheet
3. Rename it to something like "Balance Loader Bot Logs"
4. Copy the Spreadsheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit
   ```

## Step 2: Set Up Google Cloud Service Account

✅ **Already completed for your project!**

Your service account details:

- **Project ID**: `balanceloader-467002`
- **Service Account Email**: `balanceloader2025@balanceloader-467002.iam.gserviceaccount.com`
- **Credentials File**: `balanceloader-467002-4124a1ff41d8.json` (already provided)

The Google Sheets API is already enabled for your project.

## Step 3: Share the Spreadsheet

1. Open your Google Sheets spreadsheet
2. Click "Share" button
3. Add the service account email as an editor: `balanceloader2025@balanceloader-467002.iam.gserviceaccount.com`
4. Make sure to give "Editor" permissions

## Step 4: Configure Environment Variables

Add these variables to your `.env` file:

```env
# Google Sheets Configuration
GOOGLE_SHEETS_ID=your_google_spreadsheet_id_here
GOOGLE_CREDENTIALS_PATH=balanceloader-467002-4124a1ff41d8.json
```

**Note:** The credentials file `balanceloader-467002-4124a1ff41d8.json` should be placed in the same directory as your bot files (the root project directory).

## Step 5: Install Dependencies

Run this command to install the required packages:

```bash
pip install -r requirements.txt
```

## Step 6: Test the Connection

Use the bot command `/test_sheets` to verify the setup is working correctly.

## Sheet Structure

The bot will automatically create two sheets:

### Sheet 1: "New Users"

- **Timestamp**: When the user was created
- **Username**: The username that was created
- **Operator**: Telegram user who initiated the action

### Sheet 2: "Chip Loads"

- **Timestamp**: When the deposit was made
- **Username**: The target username
- **Operator**: Telegram user who initiated the action
- **Amount**: Chip amount deposited
- **Bonus %**: Bonus percentage (only for bonus deposits)
- **Type**: "normal" or "bonus"

## Example Entries

### New Users Sheet:

| Timestamp           | Username | Operator   |
| ------------------- | -------- | ---------- |
| 2025-01-23 10:15:00 | juan100  | @operatorA |

### Chip Loads Sheet:

| Timestamp           | Username | Operator   | Amount | Bonus % | Type   |
| ------------------- | -------- | ---------- | ------ | ------- | ------ |
| 2025-01-23 10:15:00 | juan100  | @operatorA | 2000   |         | normal |
| 2025-01-23 10:15:05 | juan100  | @operatorA | 600    | 30      | bonus  |

## Troubleshooting

1. **Permission denied**: Make sure the service account email is added to the spreadsheet with editor permissions
2. **File not found**: Check the `GOOGLE_CREDENTIALS_PATH` points to the correct JSON file
3. **API not enabled**: Ensure Google Sheets API is enabled in your GCP project
4. **Invalid spreadsheet ID**: Verify the ID is correctly copied from the URL

## Security Notes

- Keep your service account credentials file secure
- Never commit the credentials file to version control
- Use environment variables for sensitive configuration
- Regularly rotate service account keys if needed
