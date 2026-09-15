InboxIQ --- Personalized Spam Intelligence

Personalized spam intelligence --- rescue what matters.

InboxIQ is a machine-learning based email classification system designed
to go beyond traditional spam filtering. Instead of treating every
unwanted message the same way, InboxIQ combines spam detection with
the user's personal interests to identify promotional/spam emails
that are relevant to them.

For example, when a user selects Electronics & Gadgets, InboxIQ can
identify an unwanted electronics promotion and use the user's
preferences as an additional layer in its decision-making.

✨ Key Features

Machine-learning based email classification

Personalized spam detection using user-selected interests

Gmail integration through Google OAuth and the Gmail API

Processing of unread Gmail messages

Manual email testing through the web interface

Classification confidence displayed in the UI

Visual classification results

Serialized trained model included with the project

Supported interest categories include:

Finance & Banking

Electronics & Gadgets

Food & Dining

Fashion & Clothing

Health & Fitness

Travel & Hotels

Festival & Seasonal Sales

Shopping & Deals

Beauty & Skincare

🧠 How InboxIQ Works

InboxIQ is built around two questions:

Is this email legitimate or spam?

If it is unwanted, does it match the user's interests?

High-level workflow

flowchart TD
    A[User opens InboxIQ] --> B{Choose input}
    B -->|Paste email| C[Email content]
    B -->|Gmail| D[Connect Gmail]
    D --> E[Fetch unread emails]
    E --> C
    C --> F[Preprocess email]
    F --> G[Feature extraction]
    G --> H[Trained ML model]
    H --> I{Classification}
    I -->|HAM / Legitimate| J[Normal Inbox]
    I -->|Spam| K[Interest matching]
    K --> L{Matches selected interest?}
    L -->|Yes| M[InboxIQ / Rescued Spam]
    L -->|No| N[Regular Spam]

🔄 Personalized Classification

Spam does not automatically mean irrelevant.

flowchart LR
    A[Incoming Email] --> B[Spam Classifier]
    B -->|Legitimate| C[Normal Inbox]
    B -->|Spam| D[Interest Matching]
    D --> E{Matches preference?}
    E -->|Electronics| F[InboxIQ Electronics]
    E -->|Finance| G[InboxIQ Finance]
    E -->|Food| H[InboxIQ Food]
    E -->|No match| I[Regular Spam]

This gives InboxIQ a more personalized approach than a simple spam/ham
classifier.

🏗️ System Architecture

flowchart TB
    U[User] --> UI[InboxIQ Web Interface]
    UI --> API[Flask Application]
    API --> ML[Trained ML Model]
    API --> PREF[User Preferences]
    API --> GI[Gmail Integration]
    GI --> GOOGLE[Google Gmail API]
    GOOGLE --> GI
    ML --> RESULT[Classification Result]
    PREF --> RESULT
    GI --> RESULT
    RESULT --> UI

Component           Purpose

Frontend            InboxIQ user interface
Flask Backend       Application logic and routing
ML Model            Email classification
Gmail Integration   Gmail API communication
Preferences         Selected user-interest categories
Model File          Serialized trained model
Notebook            ML experimentation and development

📁 Project Structure

inboxIQ-GIT/
│
├── app.py
├── app_original.py
│
├── gmail_integration.py
├── gmail_integration_backup.py
│
├── inboxiq_model.pkl
├── index.html
├── MAINproject.ipynb
├── preferences.json
├── requirements.txt
│
├── START_INBOXIQ.bat
└── START_INBOXIQ.command

Important files

app.py --- Main Flask application and web-server entry point.

gmail_integration.py --- Gmail-related functionality and Gmail API
communication.

inboxiq_model.pkl --- Serialized machine-learning model loaded by
the application.

index.html --- Web interface.

MAINproject.ipynb --- Machine-learning development and
experimentation notebook.

preferences.json --- Stores selected interest categories.

requirements.txt --- Python dependencies.

START_INBOXIQ.command --- macOS startup helper.

START_INBOXIQ.bat --- Windows startup helper.

The *_backup.py and *_original.py files are development/reference
copies and are not required for the core application.

🤖 Machine Learning

The project experimented with several supervised-learning algorithms,
including:

Naive Bayes

Logistic Regression

Random Forest

Support Vector Machine (SVM)

The strongest-performing model from the experiments was selected for the
application and serialized as:

inboxiq_model.pkl

The application loads the trained model at startup rather than
retraining it every time.

ML pipeline

flowchart LR
    A[Email Dataset] --> B[Data Cleaning]
    B --> C[Text Processing]
    C --> D[Feature Representation]
    D --> E[Train Models]
    E --> F[Evaluate Models]
    F --> G[Select Best Model]
    G --> H[Save Model]
    H --> I[inboxiq_model.pkl]
    I --> J[Flask Application]

📧 Gmail Integration

InboxIQ can connect to Gmail using Google's OAuth authentication and
Gmail API.

sequenceDiagram
    participant User
    participant InboxIQ
    participant Google
    participant Gmail

    User->>InboxIQ: Click Connect Gmail
    InboxIQ->>Google: Request OAuth authorization
    Google->>User: Request permission
    User->>Google: Grant permission
    Google->>InboxIQ: Authorization response
    InboxIQ->>Gmail: Request messages
    Gmail->>InboxIQ: Return messages
    InboxIQ->>InboxIQ: Classify messages
    InboxIQ->>User: Display results

Gmail setup requirements

You need:

A Google Cloud project

Gmail API enabled

OAuth configuration

An authorized Google account when the OAuth app is in testing mode

Never commit OAuth credentials, access tokens, refresh tokens, or
private keys to GitHub.

⚙️ Installation

1. Clone the repository

git clone <YOUR_GITHUB_REPOSITORY_URL>
cd inboxIQ-GIT

2. Create a virtual environment

macOS / Linux

python3 -m venv venv
source venv/bin/activate

Windows

python -m venv venv
venv\Scripts\activate

3. Install dependencies

pip install -r requirements.txt

🔐 Gmail Configuration

Configure the Google Cloud OAuth credentials required by the Gmail
integration.

If the OAuth application is in Testing mode, add the Google account
you intend to use as an authorized test user.

Keep credentials outside the repository.

A recommended .gitignore includes:

__pycache__/
*.pyc
.env
.env.*
credentials.json
token.json
client_secret*.json
*.pem
.DS_Store

▶️ Running InboxIQ

Start the Flask application:

python3 app.py

Then open:

http://127.0.0.1:5000

On macOS, the included startup script can also be used when configured
for the local environment:

START_INBOXIQ.command

🖥️ Using the Application

1. Open InboxIQ

Start the application and open the local web address.

2. Select interests

Choose the categories that matter to you, for example:

✓ Electronics & Gadgets
✓ Finance & Banking
✓ Food & Dining

3. Connect Gmail

Click:

CONNECT GMAIL

and complete Google's authorization flow.

4. Process unread emails

Use the application's unread-email processing option to retrieve and
classify unread Gmail messages.

5. Review the result

The interface can display:

Classification

Spam category

Confidence

Model source

Final InboxIQ decision

🧪 Manual Testing

InboxIQ also supports testing an individual email without using Gmail.

Paste an email into the Paste Email section and select:

CLASSIFY EMAIL

The message is then passed through the application's classification
workflow.

📊 Example Decision

Suppose a user selects:

Electronics & Gadgets
Finance & Banking
Food & Dining

An unwanted electronics promotion can follow:

Spam
  ↓
Electronics-related
  ↓
Matches user preference
  ↓
InboxIQ

An unrelated unwanted message can follow:

Spam
  ↓
No relevant preference match
  ↓
Regular Spam

The central idea is simple:

Personalized filtering instead of one-size-fits-all filtering.

🛡️ Security & Privacy

InboxIQ can process email content, so security should be considered
carefully.

Never publish:

Gmail passwords

OAuth client secrets

Access tokens

Refresh tokens

API keys

Private keys

Personal email datasets

Sensitive real email contents

For a public repository, use placeholder configuration and .gitignore
rules for local secrets.

⚠️ Development Status

InboxIQ is currently a development/project implementation.

The Flask development server is intended for local development and
testing. A production deployment should use a production-grade WSGI
server together with appropriate security configuration.

The Gmail OAuth application may also require Google's verification
process before unrestricted public use.

🚀 Future Improvements

Potential improvements include:

More advanced NLP feature extraction

User feedback-based personalization

Email priority scoring

More detailed spam categories

Better confidence calibration

Automatic Gmail labels for InboxIQ results

Background email processing

Database-backed user profiles

Analytics and classification statistics

Production deployment

Improved OAuth/account management

🎯 Project Objective

InboxIQ is not simply designed to answer:

"Is this email spam?"

It aims to answer a more useful question:

"If this email is unwanted, is it still relevant to this particular
user?"

That personalization is the central concept behind InboxIQ.

📌 Conclusion

InboxIQ brings together machine learning, Gmail integration, a web
interface, and user preferences into one email-management workflow.

The project demonstrates how a trained classification model can be
connected to a practical application and then extended with personalized
decision-making. Instead of treating every spam message as equally
unwanted, InboxIQ explores the idea of identifying messages that may
still be valuable to a particular user.

The current implementation also provides a foundation for future
development in personalized email intelligence, where filtering
decisions can become increasingly tailored to individual interests and
behaviour.

👨‍💻 Technology Stack

Python
Flask
Machine Learning
HTML / CSS / JavaScript
Gmail API
Google OAuth

⭐ Final Note

InboxIQ started with a simple problem: spam filtering is not always
personal.

A message that is useless to one person may be interesting to another.
InboxIQ explores that gap by combining traditional email classification
with personal interests.

InboxIQ --- rescue what matters.
