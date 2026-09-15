# InboxIQ — READY Gmail Edition

## What is already integrated

Your supplied trained model is included as `inboxiq_model.pkl`.

The existing InboxIQ two-stage pipeline is preserved:
1. Stage 1: HAM vs SPAM using the trained pipeline.
2. Stage 2: category + user preference similarity for detected spam.
3. Matching spam -> `INBOXIQ`.
4. Other spam -> `SPAM`.

The Gmail integration adds:
- Google OAuth 2.0
- Gmail API
- automatic processing of unread messages delivered to Gmail Inbox
- persistent preferences in `preferences.json`
- Gmail label `InboxIQ`
- Gmail label `InboxIQ/Spam`
- automatic background processing every 20 seconds
- web UI buttons for Connect Gmail and Process New Mail
- Flask serves the UI, so you do not need to open `index.html` separately

## You still have ONE Google setup step

I cannot create Google's OAuth client for your Google account. You must create/download the OAuth Desktop App JSON from Google Cloud and put it in this folder as:

    credentials.json

Do not send `credentials.json` or `token.json` to anyone.

## Exact setup

### 1. Create a Google Cloud project
Go to Google Cloud Console.

Create a new project, for example:

    InboxIQ Gmail

### 2. Enable Gmail API
In the project, open APIs & Services -> Library.
Search for:

    Gmail API

Click Enable.

### 3. Configure Google Auth Platform / OAuth
Open Google Auth Platform (or OAuth consent screen).

Configure the app. For a personal/student local test, External is normally appropriate.

If Google asks for an app name, use:

    InboxIQ

If it asks for your email, use your Google account email.

If the app is in Testing mode, add your Gmail account as a Test User.

### 4. Create OAuth credentials
Open APIs & Services -> Credentials.

Create Credentials -> OAuth client ID.

Application type:

    Desktop app

Download the JSON.

Rename the downloaded file:

    credentials.json

Put it beside `app.py`.

Your folder should look like:

    InboxIQ_READY/
        app.py
        gmail_integration.py
        index.html
        inboxiq_model.pkl
        MAINproject.ipynb
        requirements.txt
        credentials.json
        START_INBOXIQ.command

### 5. Start InboxIQ

#### macOS
Double-click:

    START_INBOXIQ.command

Or in Terminal:

    cd /path/to/InboxIQ_READY
    python3 -m pip install -r requirements.txt
    python3 app.py

#### Windows
Double-click:

    START_INBOXIQ.bat

Or:

    py -m pip install -r requirements.txt
    py app.py

### 6. Open InboxIQ

Go to:

    http://127.0.0.1:5000

### 7. Select preferences FIRST

Select the categories you want InboxIQ to rescue, such as:

    Electronics & Gadgets
    Fashion & Clothing
    Travel & Hotels

They are saved automatically.

### 8. Connect Gmail

Click:

    CONNECT GMAIL

A Google authorization window will open.

Sign into the Gmail account you want InboxIQ to manage.

Review the permissions and allow access.

After successful authorization, InboxIQ creates:

    token.json

Do not delete token.json while you want automatic Gmail access.

### 9. Test it

Send a test email to the connected Gmail account.

Keep the InboxIQ terminal running.

Within about 20 seconds, InboxIQ checks unread Inbox mail.

Possible result:

    HAM
      -> stays in Gmail Inbox

    SPAM + selected preference
      -> removed from Inbox
      -> Gmail label: InboxIQ

    SPAM + no selected preference
      -> removed from Inbox
      -> Gmail label: InboxIQ/Spam

The labels appear in Gmail's left sidebar.

## Important behavior

InboxIQ is processing messages that Gmail has delivered to the Inbox.

Gmail's own spam filtering can move some messages directly into Gmail's Spam folder before InboxIQ gets them. This local version does not automatically override Gmail's own spam system.

Also, this version uses local polling rather than Gmail push notifications. That keeps the project simple and reliable for a college demonstration.

## Security

InboxIQ never asks for or stores your Gmail password.

OAuth creates a local `token.json`.

Do not upload/share:

    credentials.json
    token.json
    .env

## If you want to disconnect

Delete:

    token.json

Then restart InboxIQ. You can authorize again.

## Model

The supplied `inboxiq_model.pkl` is already placed in the correct filename expected by `app.py`.

The pickle was created with scikit-learn 1.6.1. The requirements file therefore pins the scikit-learn range around that version to reduce model compatibility problems.

## Stop

In the terminal running InboxIQ:

    Ctrl+C

The automatic worker stops when the Python process stops.

## For your project presentation

The clean architecture is:

    Gmail
       |
       | OAuth + Gmail API
       v
    InboxIQ Gmail Adapter
       |
       v
    Email extraction / preprocessing
       |
       v
    Stage 1: HAM vs SPAM
       |
       +----------------------+
       |                      |
      HAM                    SPAM
       |                      |
       v                      v
    Gmail Inbox       Stage 2: Preference Matching
                              |
                    +---------+---------+
                    |                   |
                 MATCH               NO MATCH
                    |                   |
                    v                   v
                 InboxIQ           InboxIQ/Spam

For a production/cloud deployment, replace the 20-second polling worker with Gmail push notifications through Google Cloud Pub/Sub.
