# Agreement Change Request Bot

Sales reps DM the bot `/request`, answer 3 questions, and the bot:
1. Logs the submission to a Google Sheet (via an Apps Script webhook — no GCP service account needed)
2. Posts a clean summary into the **Agreement Change Requests** Telegram group

✅ Group: already created (`Agreement Change Requests`, chat_id `-1003904330593`)

## 1. Create the bot (if not done yet)
1. Message **@BotFather** on Telegram → `/newbot` → follow prompts → save the **bot token**
2. Add the bot to the **Agreement Change Requests** group as a normal member

## 2. Set up the Google Sheet backend (Apps Script — no service account)
1. Create a new Google Sheet (any name)
2. In the Sheet: **Extensions → Apps Script**
3. Delete any starter code, paste in the contents of `AppsScript.gs` from this folder
4. Click **Deploy → New deployment**
   - Type: **Web app**
   - Execute as: **Me**
   - Who has access: **Anyone**
5. Click **Deploy** → authorize with your Google account when prompted
6. Copy the **Web app URL** it gives you (looks like `https://script.google.com/macros/s/AKfycb.../exec`) — that's your `APPS_SCRIPT_URL`

That's it — no Cloud project, no service account, no key file. The org policy you hit doesn't apply here since this runs as your own Google account, not a service account.

The "Submissions" tab and its header row get created automatically the first time someone submits the form.

## 3. Deploy to Render
1. Push this folder to a new GitHub repo (e.g. `juggerNAD/agreement-change-bot`)
2. Render → New → Blueprint → connect the repo (uses `render.yaml`)
3. When prompted, set the env vars:
   - `BOT_TOKEN` — from step 1
   - `GROUP_CHAT_ID` — `-1003904330593`
   - `APPS_SCRIPT_URL` — from step 2
4. Deploy — runs as a background worker (polling, no public URL needed)

## 4. Test it
- DM the bot `/request`
- Answer the 3 questions
- Check the Sheet for the new row and the group for the summary post

## Local testing (optional)
```bash
cp .env.example .env   # fill in real values
pip install -r requirements.txt
export $(cat .env | xargs)  # or use python-dotenv
python bot.py
```
