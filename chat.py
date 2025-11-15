import streamlit as st
import hashlib
from datetime import datetime, timezone
import gspread
from google.oauth2.service_account import Credentials
from streamlit_autorefresh import st_autorefresh
import time

# --- CONFIGURATION ---
SPREADSHEET_ID = "1X0cLUjq05jRhQXXIw58v1amQQZXTK4IPe0T32KMlV-g"
SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

# CSS style for red admin names
ADMIN_NAME_STYLE = "style='color:red; font-weight:bold;'"
ADMIN_ROLE_COLOR = "red" # Used for chat bubble details

# ---------------------- GOOGLE SHEETS INIT (with Streamlit Secrets) ----------------------
try:
    # Try loading from Streamlit Secrets (for cloud deployment)
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
except st.errors.StreamlitSecretNotFoundError:
    # This error happens locally when no secrets.toml is found
    # Fallback to local key.json file (for local development)
    try:
        creds = Credentials.from_service_account_file("key.json", scopes=SCOPE)
    except FileNotFoundError:
        st.error("Credential file 'key.json' not found. This file is required for local development when Streamlit Secrets are not set.")
        st.stop()
    except Exception as e:
        st.error(f"Error loading local key.json: {e}")
        st.stop()
except Exception as e:
    # Catch any other unexpected errors
    st.error(f"An unexpected error occurred loading credentials: {e}")
    st.stop()

# Authorize gspread
try:
    gc = gspread.authorize(creds)
except Exception as e:
    st.error(f"Failed to authorize gspread: {e}")
    st.stop()

# Access worksheets
try:
    sh = gc.open_by_key(SPREADSHEET_ID)
    users_ws = sh.worksheet("users")
    banned_ws = sh.worksheet("banned")
    messages_ws = sh.worksheet("messages")
except Exception as e:
    st.error(f"Failed to access spreadsheet or worksheets: {e}")
    st.stop()

# ---------------------- PASSWORD HASH ----------------------
def hash_password(password):
    """Hashes the password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------------- SHEET HELPERS ----------------------
def add_user(username, password, role="user"):
    """Adds a new user to the users sheet."""
    users = users_ws.get_all_values()[1:] # Skip header
    if any(u and u[0] == username for u in users): 
        return False, "Username already exists."
    users_ws.append_row([username, hash_password(password), role])
    return True, "Account created. You can now log in."

def verify_user(username, password):
    """Verifies user credentials and checks for bans."""
    users = users_ws.get_all_records()
    for u in users:
        if u.get('username') == username and u.get('password') == hash_password(password):
            banned = [b.get('username') for b in banned_ws.get_all_records() if b.get('username')]
            if username in banned:
                return False, "banned"
            return True, u.get('role', 'user')
    return False, None

def ban_user(username):
    """Adds a user to the banned list."""
    banned_list = banned_ws.get_all_records()
    if username not in [b.get('username') for b in banned_list if b.get('username')]:
        banned_ws.append_row([username])
        st.cache_data.clear() 
        st.rerun()

def unban_user(username):
    """Removes a user from the banned list."""
    banned_list = banned_ws.get_all_records()
    try:
        row_index = [i + 2 for i, b in enumerate(banned_list) if b.get('username') == username][0]
        banned_ws.delete_rows(row_index)
        st.cache_data.clear() 
        st.rerun()
        return True
    except IndexError:
        return False 

def add_message(username, role, content):
    """Adds a new message to the messages sheet."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    messages_ws.append_row([username, role, content, timestamp])
    
    # --- FIX ---
    # Clear the cache *before* rerunning.
    # This forces get_messages_cached() to fetch new data on the rerun.
    st.cache_data.clear() 
    st.rerun()
# ---------------------- CACHED DATA ----------------------
@st.cache_data(ttl=60) 
def get_messages_cached():
    """Fetches and caches all messages from the sheet."""
    time.sleep(0.5) 
    try:
        return messages_ws.get_all_records()
    except Exception as e:
        st.error(f"Error fetching messages: {e}. Data might be stale.")
        return []

@st.cache_data(ttl=300) 
def get_all_users_cached():
    """Fetches all users and current banned status."""
    try:
        all_values = users_ws.get_all_values()
        
        if not all_values:
            return []
            
        header = [h.lower() for h in all_values[0]]
        data_rows = all_values[1:]
        
        banned = [b.get('username') for b in banned_ws.get_all_records() if b.get('username')]
        
        user_list = []
        for row in data_rows:
            if len(row) >= 1 and row[0].strip(): 
                username = row[0].strip()
                role = row[2].strip() if len(row) > 2 else 'user' 
                
                user_list.append({
                    'username': username,
                    'role': role,
                    'is_banned': username in banned
                })
        return user_list
    except Exception as e:
        st.error(f"Error fetching user list: {e}")
        return []

# ---------------------- STREAMLIT CONFIG ----------------------
st.set_page_config(page_title="Chat App", layout="wide", page_icon="💬")

# ---------------------- SESSION STATE INITIALIZATION ----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------------- LOGIN/SIGN UP ----------------------
if not st.session_state.logged_in:
    st.title("Welcome to the Chat App 💬")
    tab1, tab2 = st.tabs(["Login 🔑", "Sign Up 📝"])
    
    with tab1:
        username = st.text_input("Username", placeholder="Enter username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In"):
            ok, role = verify_user(username, password)
            if ok and role != "banned":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = role
                st.rerun()
            elif role == "banned":
                st.error("You are banned from this service.")
            else:
                st.error("Invalid username or password.")
                
    with tab2:
        new_user = st.text_input("Create username", key="signup_user")
        new_pass = st.text_input("Create password", type="password", key="signup_pass")
        if st.button("Create Account"):
            ok, msg = add_user(new_user, new_pass)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    

    st.markdown(
    """
    <style>
        .social-icons {
            text-align: center;
            margin-top: 60px;
        }

        .social-icons a {
            text-decoration: none !important;
            margin: 0 20px;
            font-size: 28px;
            display: inline-block;
            color: inherit !important; /* force child i to use its color */
        }

        

        /* Hover glitch animation */
        .social-icons a:hover {
            animation: glitch 0.3s infinite;
        }

        
        /* Contact us heading */
        .contact-heading {
            text-align: center;
            font-size: 25px;
            font-weight: bold;
            margin-bottom: 15px;
        }
        @keyframes glitch {
            0% { transform: translate(0px, 0px); text-shadow: 2px 2px #0ff, -2px -2px #f0f; }
            20% { transform: translate(-2px, 1px); text-shadow: -2px 2px #0ff, 2px -2px #f0f; }
            40% { transform: translate(2px, -1px); text-shadow: 2px -2px #0ff, -2px 2px #f0f; }
            60% { transform: translate(-1px, 2px); text-shadow: -2px 2px #0ff, 2px -2px #f0f; }
            80% { transform: translate(1px, -2px); text-shadow: 2px -2px #0ff, -2px 2px #f0f; }
            100% { transform: translate(0px, 0px); text-shadow: 2px 2px #0ff, -2px -2px #f0f; }
        }
    </style>
    <div class="social-icons">
    <div class="contact-heading">Contact Us:</div>
        <a class='fb' href='https://www.facebook.com/sakibhossain.tahmid' target='_blank'>
            <i class='fab fa-facebook'></i> 
        </a> 
        <a class='insta' href='https://www.instagram.com/_sakib_000001' target='_blank'>
            <i class='fab fa-instagram'></i> 
        </a> 
        <a class='github' href='https://github.com/sakib-12345' target='_blank'>
            <i class='fab fa-github'></i> 
        </a> 
        <a class='email' href='mailto:sakibhossaintahmid@gmail.com'>
            <i class='fas fa-envelope'></i> 
        </a>
    </div>
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    """,
    unsafe_allow_html=True
     )


    st.markdown(
            f'<div style="text-align: center; color: grey;">&copy; 2025 Sakib Hossain Tahmid. All Rights Reserved.</div>',
            unsafe_allow_html=True
           )             
    st.stop()

# ---------------------- AUTO REFRESH ----------------------
st_autorefresh(interval=30000, key="chat_refresh") 

# ==========================================================
# ---------------------- SIDEBAR USER MANAGER ----------------
# ==========================================================

with st.sidebar:
    st.header("👤 Users Online")
    
    current_username = st.session_state.username
    is_admin = st.session_state.role == "admin"
    
    user_data = get_all_users_cached()
    
    for user in user_data:
        username = user['username']
        is_banned = user['is_banned']
        is_current = username == current_username
        
        display_text = username
        
        if user['role'] == 'admin':
            display_text = f"<span {ADMIN_NAME_STYLE}>{display_text}</span>"
            
        if is_current:
            display_text = f"**{display_text} (You)**"
        
        status_emoji = "(Admin)" if user['role'] == 'admin' else ""
        s = "🙎🏻‍♂️" if user['role'] == 'admin' else "👤"
        if is_banned:
            status_emoji = "🚫(banned)"
            display_text = f"~~{display_text}~~"
        
        st.markdown(f"{s}{display_text}{status_emoji}", unsafe_allow_html=True)
        
        if is_admin and not is_current:
            col1, col2 = st.columns(2)
            
            if not is_banned:
                if col1.button("Ban", key=f"ban_{username}", use_container_width=True):
                    ban_user(username)
            else:
                if col2.button("Unban", key=f"unban_{username}", use_container_width=True):
                    unban_user(username)
        
        

# ==========================================================
# ---------------------- MAIN CHAT UI ----------------------
# ==========================================================

st.title(f"Hello, {st.session_state.username} 👋")

left, right = st.columns([4, 1])

with left:
    st.subheader("Chat History")
    chat_container = st.container(height=500)
    
    with chat_container:
        msgs = get_messages_cached()
        
        for m in msgs:
            author = m.get('username', 'Unknown')
            role = m.get('role', 'user')
            text = m.get('content', 'No content')
            ts = m.get('timestamp', 'N/A')
            
            avatar = "👮" if role == "admin" else "👤"

            with st.chat_message(author, avatar=avatar):
                if role == 'admin':
                    name_html = f"<span {ADMIN_NAME_STYLE}>{author}</span>"
                    role_text = f"<span style='color:{ADMIN_ROLE_COLOR};'>({role.capitalize()})</span>"
                else:
                    name_html = author
                    role_text = f"({role.capitalize()})"
                
                st.markdown(f"{name_html} {role_text} - *{ts}*", unsafe_allow_html=True)
                st.write(text)

    # Chat Input
    msg = st.chat_input("Type a message...")
    if msg:
        add_message(st.session_state.username, st.session_state.role, msg)

with right:
    st.caption(f"Your Role: **{st.session_state.role.capitalize()}**")
    
    if st.button("Log Out", type="primary", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    if st.session_state.role == "admin":
        st.divider()
        st.subheader("Admin Tools")
        
        # --- FIX: Replaced clear() with delete_rows() ---
        if st.button("Clear Chat", use_container_width=True):
            # Get all data rows (this is a list of lists)
            all_data_rows = messages_ws.get_all_values()
            
            # Check if there's more than just the header (which is row 1)
            if len(all_data_rows) > 1:
                # Get the number of the last row with data
                last_row_index = len(all_data_rows)
                
                # Delete all rows from 2 (the first data row) to the end (inclusive)
                messages_ws.delete_rows(2, last_row_index)
            
            st.cache_data.clear() 
            st.success("Chat cleared.")
            st.rerun()




st.sidebar.markdown(
    """
    <style>
        .social-icons {
            text-align: center;
            margin-top: 40px;
        }

        .social-icons a {
            text-decoration: none !important;
            margin: 0 10px;
            font-size: 20px;
            display: inline-block;
            color: inherit !important; /* force child i to use its color */
        }

        

        /* Hover glitch animation */
        .social-icons a:hover {
            animation: glitch 0.3s infinite;
        }

        
        /* Contact us heading */
        .contact-heading {
            text-align: center;
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 15px;
        }
        @keyframes glitch {
            0% { transform: translate(0px, 0px); text-shadow: 2px 2px #0ff, -2px -2px #f0f; }
            20% { transform: translate(-2px, 1px); text-shadow: -2px 2px #0ff, 2px -2px #f0f; }
            40% { transform: translate(2px, -1px); text-shadow: 2px -2px #0ff, -2px 2px #f0f; }
            60% { transform: translate(-1px, 2px); text-shadow: -2px 2px #0ff, 2px -2px #f0f; }
            80% { transform: translate(1px, -2px); text-shadow: 2px -2px #0ff, -2px 2px #f0f; }
            100% { transform: translate(0px, 0px); text-shadow: 2px 2px #0ff, -2px -2px #f0f; }
        }
    </style>
    <div class="social-icons">
    <div class="contact-heading">Contact Us:</div>
        <a class='fb' href='https://www.facebook.com/sakibhossain.tahmid' target='_blank'>
            <i class='fab fa-facebook'></i> 
        </a> 
        <a class='insta' href='https://www.instagram.com/_sakib_000001' target='_blank'>
            <i class='fab fa-instagram'></i> 
        </a> 
        <a class='github' href='https://github.com/sakib-12345' target='_blank'>
            <i class='fab fa-github'></i> 
        </a> 
        <a class='email' href='mailto:sakibhossaintahmid@gmail.com'>
            <i class='fas fa-envelope'></i> 
        </a>
    </div>
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    """,
    unsafe_allow_html=True
)


st.markdown(
            f'<div style="text-align: center; color: grey;">&copy; 2025 Sakib Hossain Tahmid. All Rights Reserved.</div>',
            unsafe_allow_html=True

           ) 

