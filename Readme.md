# Telegram Group Adder from CSV

A robust Python tool to automate adding users to a Telegram group or channel using phone numbers from a CSV file. This script leverages the [Telethon](https://github.com/LonamiWebs/Telethon) library and provides detailed logging, error handling, and reporting.

---

## Features

- **CSV Import:** Reads phone numbers from a CSV file (supports several common column names).
- **Contact Import:** Imports phone numbers as temporary Telegram contacts in batches.
- **Group Addition:** Adds imported users to a specified Telegram group or channel.
- **Error Handling:** Handles Telegram API rate limits, privacy restrictions, and common errors (FloodWait, PeerFlood, etc.).
- **Reporting:** Generates a detailed JSON report and prints a summary to the console.
- **Cleanup:** Optionally removes temporary contacts after the process.
- **Logging:** Logs all actions and errors to `telegram_adder.log`.
- **Interactive:** Prompts for cleanup and provides clear progress updates.

---

## Requirements

- **Python:** 3.7 or higher
- **Telegram API credentials:** [Get from my.telegram.org](https://my.telegram.org)
- **CSV file:** List of phone numbers to add
- **Python packages:**  
  - `telethon`
  - `python-dotenv`
  - `pandas`

---

## Installation

1. **Clone or Download** this repository.

2. **Install dependencies:**
   ```bash
   pip install telethon python-dotenv pandas
   ```

3. **Create a `.env` file** in the project directory:
   ```
   API_ID=your_api_id
   API_HASH=your_api_hash
   PHONE=+1234567890
   GROUP_IDENTIFIER=@your_group_username_or_id
   ```
   - `API_ID` and `API_HASH`: From [my.telegram.org](https://my.telegram.org).
   - `PHONE`: Your Telegram account's phone number (with country code, e.g., `+1234567890`).
   - `GROUP_IDENTIFIER`: The group's username (with `@`) or its numeric ID.

4. **Prepare your CSV file:**
   - Name it `phone_numbers.csv` (or edit the script to use another name).
   - Must have a column for phone numbers. Accepted column names: `phone`, `Phone`, `PHONE`, `phone_number`, `Phone Number`, `number`.
   - Example:
     ```
     phone
     +12345678901
     +19876543210
     ```

---

## Usage

1. **Run the script:**
   ```bash
   python main.py
   ```

2. **Follow the prompts:**
   - The script will:
     - Load and clean phone numbers from the CSV.
     - Import them as temporary contacts (in batches of 50).
     - Add each imported user to the specified group/channel (with delays to avoid bans).
     - Print a summary and save a detailed JSON report.
     - Ask if you want to remove the temporary contacts from your Telegram account.

---

## How It Works

1. **Configuration:** Loads API credentials and group info from `.env`.
2. **CSV Loading:** Reads and deduplicates phone numbers from the CSV.
3. **Contact Import:** Imports phone numbers as Telegram contacts (batch size configurable).
4. **Group Addition:** Adds each imported user to the group/channel, handling rate limits and privacy errors.
5. **Reporting:** Prints a summary and saves a detailed report as `telegram_report_YYYYMMDD_HHMMSS.json`.
6. **Cleanup:** Optionally deletes temporary contacts from your Telegram account.

---

## Customization

- **Batch Size:** Change `batch_size` in the script for contact import (default: 50).
- **Delay:** Adjust the `delay` parameter in `add_users_to_group` (default: 8 seconds per user).
- **CSV Column:** The script auto-detects the phone column; rename your column if needed.

---

## Troubleshooting

- **Missing dependencies:**  
  Install with `pip install telethon python-dotenv pandas`.
- **API errors:**  
  Double-check your `.env` credentials and ensure your Telegram account is active.
- **CSV issues:**  
  Ensure your CSV is UTF-8 encoded and contains valid phone numbers in the correct column.
- **Flood/PeerFlood errors:**  
  Telegram may temporarily limit your account. Wait several hours before retrying.

---

## Notes & Best Practices

- **Respect Telegram's Terms of Service.**  
  Adding users without consent may be considered spam and can result in bans.
- **Account Safety:**  
  Use a dedicated account for bulk operations to avoid risking your main account.
- **Logs:**  
  All actions and errors are logged in `telegram_adder.log`.
- **Reports:**  
  Each run generates a timestamped JSON report with detailed results.

---

## License

This project is provided as-is for educational purposes.  
**Use responsibly.**

