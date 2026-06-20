import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
from groq import Groq

# ==========================
# PAGE CONFIG
# ==========================
st.set_page_config(
    page_title="BPS Tutor",
    page_icon="📚",
    layout="wide"
)

st.title("📚 BPS Tutor")

# ==========================
# GROQ CONFIG
# ==========================
client = Groq(
    api_key=st.secrets["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"]
)

# ==========================
# DATABASE
# ==========================
conn = sqlite3.connect("bps_tutor.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash BLOB,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER,
        role TEXT,
        content TEXT,
        timestamp TEXT
    )
    """)

    conn.commit()

init_db()

# ==========================
# SESSION STATE
# ==========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.conversation_id = None

# ==========================
# AUTH FUNCTIONS
# ==========================
def signup(username, password):
    try:
        hashed = hashlib.sha256(
            password.encode()
        ).hexdigest()

        cursor.execute(
            """
            INSERT INTO users(username, password_hash, created_at)
            VALUES (?, ?, ?)
            """,
            (username, hashed, datetime.now().isoformat())
        )

        conn.commit()
        return True, "Account created!"

    except:
        return False, "Username already exists"


def login(username, password):
    cursor.execute(
        "SELECT id, password_hash FROM users WHERE username=?",
        (username,)
    )

    user = cursor.fetchone()

    if user:
        password_hash = user[1]

        hashed_input = hashlib.sha256(
            password.encode()
        ).hexdigest()

        if hashed_input == password_hash:
            st.session_state.logged_in = True
            st.session_state.user_id = user[0]
            st.session_state.username = username
            return True

    return False

    if user:
        password_hash = user[1]

        hashed_input = hashlib.sha256(
            password.encode()
        ).hexdigest()

        if hashed_input == password_hash:
            st.session_state.logged_in = True
            st.session_state.user_id = user[0]
            st.session_state.username = username
            return True

    return False

def logout():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.conversation_id = None
    st.rerun()

# ==========================
# AUTH UI
# ==========================
if not st.session_state.logged_in:

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):
            if login(u, p):
                st.success("Logged in!")
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        u = st.text_input("New Username")
        p = st.text_input("New Password", type="password")
        c = st.text_input("Confirm Password", type="password")

        if st.button("Sign Up"):
            if p != c:
                st.error("Passwords do not match")
            else:
                ok, msg = signup(u, p)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.stop()

# ==========================
# SIDEBAR
# ==========================
with st.sidebar:
    st.success(f"Logged in as {st.session_state.username}")
    if st.button("Logout"):
        logout()

# ==========================
# HELPERS
# ==========================
def get_chats(uid):
    cursor.execute("SELECT id, title FROM conversations WHERE user_id=? ORDER BY updated_at DESC", (uid,))
    return cursor.fetchall()

def new_chat(uid):
    cursor.execute("""
    INSERT INTO conversations(user_id, title, created_at, updated_at)
    VALUES (?, 'New Chat', ?, ?)
    """, (uid, datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    return cursor.lastrowid

def save_msg(cid, role, msg):
    cursor.execute("""
    INSERT INTO messages(conversation_id, role, content, timestamp)
    VALUES (?, ?, ?, ?)
    """, (cid, role, msg, datetime.now().isoformat()))
    conn.commit()

def load_msgs(cid):
    cursor.execute("SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id", (cid,))
    return cursor.fetchall()

# ==========================
# CHAT SETUP
# ==========================
with st.sidebar:
    if st.button("➕ New Chat"):
        st.session_state.conversation_id = new_chat(st.session_state.user_id)
        st.rerun()

    st.subheader("Chats")

    chats = get_chats(st.session_state.user_id)
    for cid, title in chats:
        if st.button(title, key=str(cid)):
            st.session_state.conversation_id = cid
            st.rerun()

if st.session_state.conversation_id is None:
    chats = get_chats(st.session_state.user_id)
    st.session_state.conversation_id = chats[0][0] if chats else new_chat(st.session_state.user_id)

# ==========================
# SHOW CHAT HISTORY
# ==========================
messages = load_msgs(st.session_state.conversation_id)

for role, msg in messages:
    with st.chat_message(role):
        st.markdown(msg)

# ==========================
# CHAT INPUT
# ==========================
user_prompt = st.chat_input("Ask something...")

if user_prompt:

    with st.chat_message("user"):
        st.markdown(user_prompt)

    save_msg(st.session_state.conversation_id, "user", user_prompt)

    history = load_msgs(st.session_state.conversation_id)[-5:]

    context = "\n".join([f"{r}: {m}" for r, m in history])

    system_prompt = f"""
You are a helpful tutor.
Keep answers short, simple, and easy to understand.

Conversation:
{context}

User: {user_prompt}
"""

    with st.chat_message("assistant"):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a helpful tutor. Keep answers short."},
                    {"role": "user", "content": system_prompt}
                ]
            )

            reply = response.choices[0].message.content

        except Exception as e:
            reply = f"Error: {str(e)}"

        st.markdown(reply)

    save_msg(st.session_state.conversation_id, "assistant", reply)

    st.rerun()

if user_prompt:

    with st.chat_message("user"):
        st.markdown(user_prompt)

    save_msg(st.session_state.conversation_id, "user", user_prompt)

    history = load_msgs(st.session_state.conversation_id)[-5:]
    context = "\n".join([f"{r}: {m}" for r, m in history])

    system_prompt = f"""
You are BPS Tutor, an AI teacher.

Return ONLY valid JSON in this format:

{{
  "explanation": "short simple explanation",
  "questions": [
    {{
      "question": "Q1?",
      "options": ["A", "B", "C", "D"],
      "answer": "A"
    }},
    {{
      "question": "Q2?",
      "options": ["A", "B", "C", "D"],
      "answer": "B"
    }},
    {{
      "question": "Q3?",
      "options": ["A", "B", "C", "D"],
      "answer": "C"
    }}
  ]
}}

Topic:
{user_prompt}

Conversation:
{context}
"""

    with st.chat_message("assistant"):

        placeholder = st.empty()

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": "Return only valid JSON. No extra text."
                    },
                    {
                        "role": "user",
                        "content": system_prompt
                    }
                ]
            )

            raw = response.choices[0].message.content
            data = json.loads(raw)

            # ==========================
            # SHOW EXPLANATION
            # ==========================
            st.markdown("### 📘 Explanation")
            st.write(data["explanation"])

            st.markdown("### 🧠 Quiz")

            # store score safely
            if "score" not in st.session_state:
                st.session_state.score = 0

            # ==========================
            # QUESTIONS WITH BUTTONS
            # ==========================
            for i, q in enumerate(data["questions"]):

                st.write(f"**Q{i+1}. {q['question']}**")

                for option in q["options"]:

                    if st.button(option, key=f"{user_prompt}_{i}_{option}"):

                        if option == q["answer"]:
                            st.success("✅ Correct!")
                            st.session_state.score += 1
                        else:
                            st.error(f"❌ Wrong! Correct answer: {q['answer']}")

            st.info(f"⭐ Score: {st.session_state.score}")

        except Exception as e:
            st.error(f"Error: {str(e)}")

    save_msg(
        st.session_state.conversation_id,
        "assistant",
        str(data) if "data" in locals() else raw
    )

    st.rerun()
