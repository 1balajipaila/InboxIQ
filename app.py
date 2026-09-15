"""
InboxIQ — Flask Backend
=======================
Run:
    pip install flask flask-cors
    python app.py

Endpoints:
    POST /classify   — classify an email
    GET  /categories — list all available preference categories
    GET  /health     — health check
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

import gmail_integration
from flask import send_from_directory

import re
import os
import pickle
import string
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ─────────────────────────────────────────────────────────────
#  App Setup
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)   # allow requests from the frontend HTML file


# ─────────────────────────────────────────────────────────────
#  NLP Preprocessing  (mirrored from the notebook — no NLTK)
# ─────────────────────────────────────────────────────────────
STOP_WORDS = frozenset([
    'i','me','my','myself','we','our','ours','ourselves','you',"you're",
    "you've","you'll","you'd",'your','yours','yourself','yourselves',
    'he','him','his','himself','she',"she's",'her','hers','herself',
    'it',"it's",'its','itself','they','them','their','theirs','themselves',
    'what','which','who','whom','this','that',"that'll",'these','those',
    'am','is','are','was','were','be','been','being','have','has','had',
    'having','do','does','did','doing','a','an','the','and','but','if',
    'or','because','as','until','while','of','at','by','for','with',
    'about','against','between','into','through','during','before',
    'after','above','below','to','from','up','down','in','out','on',
    'off','over','under','again','further','then','once','here','there',
    'when','where','why','how','all','both','each','few','more','most',
    'other','some','such','than','too','s','t','just','should','would',
    'could','shall','will','may','might','must','can','need','dare',
    'ought','used','also','however','well'
])

IRREGULARS = {
    'won':'win','better':'good','best':'good','worse':'bad','worst':'bad',
    'ran':'run','goes':'go','went':'go','gone':'go','got':'get',
    'gotten':'get','paid':'pay','bought':'buy','told':'tell',
    'sent':'send','said':'say','came':'come','taken':'take',
    'given':'give','shown':'show',
}

LEMMA_RULES = [
    (re.compile(r'ies$'),   'y'),
    (re.compile(r'ied$'),   'y'),
    (re.compile(r'ing$'),   ''),
    (re.compile(r'tion$'),  'te'),
    (re.compile(r'ness$'),  ''),
    (re.compile(r'ments?$'),''),
    (re.compile(r'ers?$'),  ''),
    (re.compile(r'ly$'),    ''),
    (re.compile(r'est$'),   ''),
    (re.compile(r'ed$'),    ''),
    (re.compile(r'ss$'),    'ss'),
    (re.compile(r's$'),     ''),
]

CONTRACTIONS = {
    "won't":'will not',"can't":'cannot',"don't":'do not',
    "i'm":'i am',"you've":'you have',"it's":'it is',
    "that's":'that is',"i've":'i have',"isn't":'is not',
    "aren't":'are not',"wasn't":'was not',"weren't":'were not',
}


def _lemmatize(word: str) -> str:
    if word in IRREGULARS:
        return IRREGULARS[word]
    for pat, repl in LEMMA_RULES:
        new = pat.sub(repl, word)
        if new != word and len(new) >= 3:
            return new
    return word


def preprocess(text: str) -> str:
    text = text.lower()
    text = re.sub(r'https?://\S+|www\.\S+', ' url ', text)
    text = re.sub(r'\S+@\S+\.\S+',          ' email ', text)
    text = re.sub(r'\b\d{10,13}\b',          ' phone ', text)
    for k, v in CONTRACTIONS.items():
        text = text.replace(k, v)
    text = re.sub(r'[^a-z\s]', ' ', text)
    tokens = [
        _lemmatize(t)
        for t in text.split()
        if t not in STOP_WORDS and len(t) >= 3
    ]
    return ' '.join(tokens)


# ─────────────────────────────────────────────────────────────
#  Category Profiles  (same 10 categories as the notebook)
# ─────────────────────────────────────────────────────────────
CATEGORY_PROFILES = {
    'Fashion & Clothing': (
        'fashion clothing wear apparel shirt dress jeans outfit style wardrobe '
        'trendy brand sale discount nike adidas zara myntra ajio amazon fashion '
        'new arrival season launch ethnic western formal casual shoes boots sneakers '
        'accessories hoodie jacket coat collection limited edition exclusive buy now '
        'flat off percent clearance stock kurti saree lehenga blazer suit tshirt'
    ),
    'Electronics & Gadgets': (
        'electronics gadget phone laptop mobile iphone samsung earbuds tablet smartwatch '
        'tech device charger headphones camera television smart tv cpu gpu processor '
        'keyboard mouse speaker powerbank bluetooth router wifi buy deal offer '
        'cashback discount price percent off model launch pre order book now limited '
        'upgrade refresh rate display screen resolution best price lowest ever'
    ),
    'Food & Dining': (
        'food restaurant dining meal delivery zomato swiggy pizza burger order cuisine '
        'eat discount offer biryani thali combo menu chef recipe taste dessert coffee '
        'cafe fast food healthy meal subscription breakfast lunch dinner free delivery '
        'order now voucher promo code coupon flat percent off tonight weekend special'
    ),
    'Health & Fitness': (
        'health fitness gym workout protein supplement yoga wellness nutrition exercise '
        'diet weight loss muscle ayurveda medicine vitamin tablet capsule immunity '
        'health plan subscription fitness app wearable calorie burn fat membership '
        'join today offer discount free trial personal trainer class schedule sessions '
        'whey creatine bcaa preworkout bulk cut tone stamina endurance strength'
    ),
    'Travel & Hotels': (
        'travel hotel flight booking trip vacation tour holiday resort airfare '
        'makemytrip goibibo airline destination package visa staycation adventure '
        'trekking cruise weekend getaway cab train bus irctc ticket oyo treebo '
        'cheapest lowest price percent off limited seats book now early bird deal '
        'international domestic departure arrival special fare flash sale'
    ),
    'Festival & Seasonal Sales': (
        'sale discount offer festival diwali eid christmas holi new year republic '
        'big billion great indian flash deal cashback coupon extra off clearance '
        'limited time special best price today only buy hurry stock ends midnight '
        'weekend offer flat percent celebrate gift hamper exclusive members first '
        'season sale end year mega biggest ever festive collection'
    ),
    'Finance & Banking': (
        'credit card loan emi investment mutual fund insurance banking finance savings '
        'cashback reward points interest rate offer apply income tax itr zerodha stock '
        'demat account sip fd rd gold bond equity trading return wealth portfolio '
        'instant approval pre approved limit upgrade zero percent interest cashback '
        'spend earn reward redeem annual fee waiver lounge access milestone'
    ),
    'Shopping & Deals': (
        'shopping deal offer buy online store discount sale percent off free shipping '
        'cashback voucher coupon promo code limited time best price today purchase '
        'cart checkout order now deliver tomorrow express fast shipping amazon flipkart '
        'meesho snapdeal nykaa purplle bigbasket blinkit grofers daily needs household '
        'super saver value pack combo kit bundle exclusive member'
    ),
    'Beauty & Skincare': (
        'beauty skincare cosmetics makeup face wash moisturizer serum hair care salon '
        'nykaa lipstick foundation glow cream sunscreen toner cleanser lotion shampoo '
        'conditioner face mask anti ageing body fragrance perfume deodorant beauty '
        'subscription box kit set palette eye shadow blush bronzer highlighter glow '
        'organic natural vegan cruelty free dermatologist tested SPF protection'
    ),
    'Lottery & Scam': (
        'winner lottery prize won million billion award selected congratulations '
        'claim now urgent immediately verification account suspended blocked '
        'password reset security alert unusual activity kindly verify otp code '
        'send money transfer wire western union gift card bitcoin cryptocurrency '
        'inheritance estate late prince nigerian advance fee confidential'
    ),
}

CATEGORY_LABELS = list(CATEGORY_PROFILES.keys())
CATEGORY_ICONS  = {
    'Fashion & Clothing':       '👗',
    'Electronics & Gadgets':    '💻',
    'Food & Dining':            '🍕',
    'Health & Fitness':         '💪',
    'Travel & Hotels':          '✈️',
    'Festival & Seasonal Sales':'🎉',
    'Finance & Banking':        '💳',
    'Shopping & Deals':         '🛍️',
    'Beauty & Skincare':        '💄',
    'Lottery & Scam':           '⚠️',
}

RESCUE_THRESHOLD = 0.07


# ─────────────────────────────────────────────────────────────
#  Build In-Memory Vectorizers  (no .pkl dependency required)
# ─────────────────────────────────────────────────────────────
def _build_vectorizers():
    """Fit the two TF-IDF vectorizers used by the pipeline."""

    # Stage 1 vectorizer — fitted on category profiles as a proxy vocabulary
    # In production this would be fitted on the full training corpus from the notebook.
    # Here we load from the .pkl if available, otherwise create a lightweight version.
    stage1_tfidf = TfidfVectorizer(
        max_features=8000, ngram_range=(1, 2),
        sublinear_tf=True, min_df=1, max_df=0.99
    )

    # Stage 2 (preference) vectorizer
    pref_tfidf = TfidfVectorizer(
        ngram_range=(1, 2), sublinear_tf=True, min_df=1
    )
    pref_matrix = pref_tfidf.fit_transform(list(CATEGORY_PROFILES.values()))

    # Fit stage1 on category profiles (fallback — good enough for demo)
    all_text = ' '.join(CATEGORY_PROFILES.values())
    stage1_tfidf.fit([all_text])

    return stage1_tfidf, pref_tfidf, pref_matrix


# Try to load the trained .pkl from the notebook; fall back to in-memory build
_stage1_pipeline  = None   # full sklearn pipeline (tfidf + classifier)
_pref_vectorizer  = None
_category_matrix  = None

PKL_PATH = 'inboxiq_model.pkl'

if os.path.exists(PKL_PATH):
    try:
        with open(PKL_PATH, 'rb') as f:
            _bundle = pickle.load(f)
        _stage1_pipeline = _bundle.get('champion_pipeline')
        _pref_vectorizer  = _bundle.get('pref_vectorizer')
        _category_matrix  = _bundle.get('category_matrix')
        print(f'✅  Loaded trained model from {PKL_PATH}')
        print(f'   Champion : {_bundle.get("champion_name", "unknown")}')
    except Exception as e:
        print(f'⚠️   Could not load {PKL_PATH}: {e} — using heuristic fallback')

if _pref_vectorizer is None or _category_matrix is None:
    print('ℹ️   Building in-memory preference vectorizer …')
    _, _pref_vectorizer, _category_matrix = _build_vectorizers()
    print('✅  In-memory vectorizer ready')


# ─────────────────────────────────────────────────────────────
#  Heuristic Stage-1 Classifier  (used when .pkl not present)
# ─────────────────────────────────────────────────────────────
_SPAM_SIGNALS = [
    r'\bfree\b', r'\bwinner\b', r'\bwon\b', r'\bprize\b', r'\bclaim\b',
    r'\bcongratulations?\b', r'\burgent\b', r'\bclick\s*here\b',
    r'\blimited\s*time\b', r'\boffer\b', r'\bdiscount\b', r'\b\d+\s*%\s*off\b',
    r'\bflash\s*sale\b', r'\bbuy\s*now\b', r'\bshop\s*now\b', r'\bdeal\b',
    r'\bpromo\b', r'\bcoupon\b', r'\bcashback\b', r'\bsubscri', r'\bexpires?\b',
    r'\bact\s*now\b', r'\bhurry\b', r'\bends?\s*(tonight|midnight|sunday)\b',
    r'\bexclusive\b', r'\bsale\s*(ends?|live)\b', r'\bpercent\b', r'bit\.ly',
    r'\bno\s*cost\s*emi\b', r'\bpre.?approved\b', r'\binstant\s*(loan|disbursal)\b',
]
_SPAM_PATTERNS = [re.compile(p, re.I) for p in _SPAM_SIGNALS]

_HAM_SIGNALS = [
    r'\bmeeting\b', r'\btomorrow\b', r'\bagenda\b', r'\bhi\s+\w+\b',
    r'\bhey\s+\w+\b', r'\bdear\s+\w+\b', r'\bteam\b', r'\bplease\s+(join|find|see)\b',
    r'\battached\b', r'\bkindly\b', r'\bregards\b', r'\bthanks?\b',
    r'\bfollowup\b', r'\bscheduled?\b', r'\bcall\b', r'\binterview\b',
]
_HAM_PATTERNS = [re.compile(p, re.I) for p in _HAM_SIGNALS]


def _heuristic_classify(text: str) -> tuple[str, float]:
    """
    Rule-based spam/ham classifier used when the trained .pkl is absent.
    Returns (label, confidence_percent).
    """
    spam_hits = sum(1 for p in _SPAM_PATTERNS if p.search(text))
    ham_hits  = sum(1 for p in _HAM_PATTERNS  if p.search(text))

    total     = spam_hits + ham_hits + 1e-9
    spam_prob = spam_hits / (total + 3)   # slight regularisation toward ham

    # Boost confidence if signal is very clear
    if spam_hits >= 4:
        spam_prob = min(0.97, spam_prob * 2.5)
    if ham_hits >= 3 and spam_hits == 0:
        spam_prob = max(0.05, spam_prob * 0.3)

    if spam_prob >= 0.35:
        return 'SPAM', round(min(99.0, spam_prob * 100 + 45), 1)
    else:
        ham_conf = round(min(99.0, (1 - spam_prob) * 100 + 20), 1)
        return 'HAM', ham_conf


# ─────────────────────────────────────────────────────────────
#  Stage 2 — Category Classification + Preference Matching
# ─────────────────────────────────────────────────────────────
def _classify_category(text: str) -> tuple[str, float]:
    """Return (best_category, similarity_score)."""
    vec  = _pref_vectorizer.transform([text.lower()])
    sims = cosine_similarity(vec, _category_matrix).ravel()
    idx  = int(np.argmax(sims))
    return CATEGORY_LABELS[idx], round(float(sims[idx]), 4)


def _match_preferences(
    text: str,
    user_interests: list,
    threshold: float = RESCUE_THRESHOLD
) -> dict:
    """Return matched categories and whether to rescue the email."""
    if not user_interests:
        return {'matched': [], 'scores': {}, 'rescue': False}

    vec     = _pref_vectorizer.transform([text.lower()])
    matched = []
    scores  = {}

    for interest in user_interests:
        if interest not in CATEGORY_LABELS:
            continue
        idx = CATEGORY_LABELS.index(interest)
        sim = float(cosine_similarity(vec, _category_matrix[idx])[0][0])
        scores[interest] = round(sim, 4)
        if sim >= threshold:
            matched.append(interest)

    return {'matched': matched, 'scores': scores, 'rescue': bool(matched)}


# ─────────────────────────────────────────────────────────────
#  Core Pipeline
# ─────────────────────────────────────────────────────────────
def run_pipeline(email_text: str, user_interests: list) -> dict:
    """
    Full InboxIQ two-stage pipeline.

    Returns a JSON-serialisable dict consumed by the frontend.
    """
    cleaned = preprocess(email_text)

    # ── Stage 1: Spam vs Ham ──────────────────────────────────
    if _stage1_pipeline is not None:
        try:
            pred       = int(_stage1_pipeline.predict([cleaned])[0])
            proba      = _stage1_pipeline.predict_proba([cleaned])[0]
            stage1     = 'SPAM' if pred == 1 else 'HAM'
            confidence = round(float(max(proba)) * 100, 1)
        except Exception:
            stage1, confidence = _heuristic_classify(email_text)
    else:
        stage1, confidence = _heuristic_classify(email_text)

    # ── Stage 2: Category + Rescue ────────────────────────────
    category     = None
    cat_score    = 0.0
    pref_result  = {'matched': [], 'scores': {}, 'rescue': False}
    final_class  = stage1
    folder       = ''
    reason       = ''

    if stage1 == 'SPAM':
        category, cat_score = _classify_category(email_text)
        if user_interests:
            pref_result = _match_preferences(email_text, user_interests)

        if pref_result['rescue']:
            final_class = 'INBOXIQ'
            folder      = 'InboxIQ'
            reason      = (f"Flagged as spam, but rescued because it matches "
                           f"your interest in: {', '.join(pref_result['matched'])}")
        else:
            final_class = 'SPAM'
            folder      = 'Spam'
            reason      = (f"Classified as spam. Category: {category} "
                           f"(score {cat_score:.3f}). No matching preference found.")
    else:
        folder = 'Inbox'
        reason = 'Classified as a legitimate email — delivered to your inbox.'

    # Sort preference scores descending
    sorted_scores = dict(
        sorted(pref_result['scores'].items(), key=lambda x: -x[1])
    )

    return {
        'status':            'success',
        'final_class':       final_class,          # 'HAM' | 'SPAM' | 'INBOXIQ'
        'folder':            folder,               # 'Inbox' | 'Spam' | 'InboxIQ'
        'stage1_class':      stage1,
        'confidence_pct':    confidence,
        'spam_category':     category,
        'cat_score':         cat_score,
        'matched_interests': pref_result['matched'],
        'preference_scores': sorted_scores,
        'reason':            reason,
        'rescued':           final_class == 'INBOXIQ',
        'model_source':      'trained' if _stage1_pipeline else 'heuristic',
    }



@app.route('/', methods=['GET'])
def home():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')

# ─────────────────────────────────────────────────────────────
#  Flask Routes
# ─────────────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status':       'ok',
        'model_loaded': _stage1_pipeline is not None,
        'categories':   len(CATEGORY_LABELS),
    })


@app.route('/categories', methods=['GET'])
def get_categories():
    """Return all available preference categories with icons."""
    return jsonify({
        'categories': [
            {'name': name, 'icon': CATEGORY_ICONS.get(name, '📌')}
            for name in CATEGORY_LABELS
            if name != 'Lottery & Scam'   # hide internal scam category from UI
        ]
    })


@app.route('/classify', methods=['POST'])
def classify():
    """
    POST /classify
    Body (JSON):
        {
            "email_text":     "full email content here ...",
            "user_interests": ["Health & Fitness", "Electronics & Gadgets"]
        }
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON body received'}), 400

    email_text = (data.get('email_text') or '').strip()
    if not email_text:
        return jsonify({'status': 'error', 'message': 'email_text is required'}), 400

    user_interests = data.get('user_interests', [])
    if not isinstance(user_interests, list):
        user_interests = []

    # Sanitise interest names
    user_interests = [
        i for i in user_interests
        if isinstance(i, str) and i in CATEGORY_LABELS
    ]

    result = run_pipeline(email_text, user_interests)
    return jsonify(result)



# ─────────────────────────────────────────────────────────────
#  Gmail Integration Routes
# ─────────────────────────────────────────────────────────────
@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    if request.method == 'GET':
        return jsonify({
            'status': 'success',
            'user_interests': gmail_integration._load_preferences()
        })

    data = request.get_json(silent=True) or {}
    interests = data.get('user_interests', [])
    if not isinstance(interests, list):
        interests = []

    interests = [
        i for i in interests
        if isinstance(i, str) and i in CATEGORY_LABELS
    ]
    gmail_integration.save_preferences(interests)

    return jsonify({
        'status': 'success',
        'user_interests': interests
    })


@app.route('/gmail/status', methods=['GET'])
def gmail_status():
    return jsonify(gmail_integration.status())


@app.route('/gmail/connect', methods=['POST'])
def gmail_connect():
    state = gmail_integration.status()

    if state['connected']:
        gmail_integration.ensure_labels()
        gmail_integration.start_background_worker()
        return jsonify({
            'status': 'connected',
            'message': f"Gmail connected as {state['email']}. Automatic processing is ON."
        })

    if not os.path.exists(gmail_integration.CREDENTIALS_FILE):
        return jsonify({
            'status': 'setup_required',
            'message': (
                "credentials.json is missing. Put your Google OAuth Desktop "
                "credentials JSON beside app.py, then click CONNECT GMAIL again."
            )
        }), 400

    gmail_integration.start_oauth()
    return jsonify({
        'status': 'authorizing',
        'message': (
            "Google authorization started. Complete the Google window that "
            "opens, then return to InboxIQ."
        )
    })


@app.route('/gmail/process-now', methods=['POST'])
def gmail_process_now():
    try:
        results = gmail_integration.process_new_mail_once()
        return jsonify({
            'status': 'success',
            'processed_count': len(results),
            'results': results,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('\n' + '═' * 60)
    print('  📬  InboxIQ — Gmail Edition')
    print('═' * 60)
    print('  Open: http://127.0.0.1:5000')
    print('  Gmail: connect from the web interface')
    print('  Automatic polling: every 20 seconds')
    print('  Stop: press Ctrl+C')
    print('═' * 60 + '\n')

    # Resume automatic Gmail processing after a previous OAuth authorization.
    try:
        if os.path.exists(gmail_integration.TOKEN_FILE):
            gmail_integration.ensure_labels()
            gmail_integration.start_background_worker()
            print('  ✓ Existing Gmail authorization found — worker started.')
        else:
            print('  ○ Gmail not connected yet.')
    except Exception as e:
        print(f'  ⚠ Gmail startup warning: {e}')

    # debug=False prevents Flask's development reloader from starting
    # a duplicate Gmail worker process.
    app.run(host='127.0.0.1', port=5000, debug=False)