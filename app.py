import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MultiLabelBinarizer
import sqlite3
import hashlib
import io

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Streamline Analytics - Cinema Intelligence & Booking",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. COMPLETE BACKEND ENGINE (SQLite & Persistence)
# -----------------------------------------------------------------------------
class AnalyticsBackend:
    def __init__(self, db_name="streamline_analytics.db"):
        self.db_name = db_name
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # User Auth Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'analyst'
                )
            """)
            # Catalog Table (Updated with Cast, Languages, Theaters, Cast Photo)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Title TEXT NOT NULL,
                    Genres TEXT NOT NULL,
                    Cast TEXT DEFAULT 'N/A',
                    Cast_Photo TEXT DEFAULT 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&q=80',
                    Primary_Language TEXT DEFAULT 'Kannada',
                    Available_Languages TEXT DEFAULT 'Kannada, English, Hindi',
                    Theaters_Available TEXT DEFAULT 'N/A',
                    Runtime_Min INTEGER NOT NULL,
                    Release_Month TEXT NOT NULL,
                    Season TEXT NOT NULL,
                    Content_Type TEXT NOT NULL,
                    IMDb_Score REAL NOT NULL,
                    TMDB_Popularity REAL NOT NULL
                )
            """)
            # Bookings Database Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movie_bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    movie_title TEXT NOT NULL,
                    city TEXT NOT NULL,
                    theater TEXT NOT NULL,
                    seats TEXT NOT NULL,
                    total_amount REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    payment_status TEXT NOT NULL
                )
            """)
            # Saved Predictions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    genres_input TEXT,
                    runtime_input INTEGER,
                    season_input TEXT,
                    type_input TEXT,
                    predicted_imdb REAL,
                    predicted_pop REAL
                )
            """)
            conn.commit()
            
            # Seed Default Users if empty
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                default_users = [
                    ("admin", self._hash_password("password123"), "admin"),
                    ("analyst", self._hash_password("netflix2026"), "analyst")
                ]
                cursor.executemany("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", default_users)
                conn.commit()

    def authenticate_user(self, username, password):
        hashed = self._hash_password(password)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, role FROM users WHERE username = ? AND password_hash = ?", (username, hashed))
            return cursor.fetchone()

    def get_catalog_data(self):
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM movies", conn)
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            return df

    def save_catalog_data(self, df):
        with self._get_connection() as conn:
            df.to_sql("movies", conn, if_exists="replace", index=False)

    def save_booking(self, movie, city, theater, seats, amount, pay_method, status="SUCCESS"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO movie_bookings 
                (movie_title, city, theater, seats, total_amount, payment_method, payment_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (movie, city, theater, str(seats), amount, pay_method, status))
            conn.commit()

    def log_prediction(self, genres, runtime, season, c_type, imdb, pop):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO saved_predictions 
                (genres_input, runtime_input, season_input, type_input, predicted_imdb, predicted_pop)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(genres), runtime, season, c_type, imdb, pop))
            conn.commit()

    def get_prediction_history(self):
        with self._get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM saved_predictions ORDER BY timestamp DESC", conn)

backend = AnalyticsBackend()

# -----------------------------------------------------------------------------
# 3. GLOBAL CUSTOM STYLING & SEAT MAP UI
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Main Background & Base Text */
    .stApp {
        background-color: #FAF7F2;
        color: #1E150C;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* ENHANCED SIDEBAR DESIGN */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F5ECE0 0%, #EFE3D3 100%) !important;
        border-right: 1px solid #D8C8B8 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #2D2115 !important;
    }
    
    /* Sidebar Brand Card */
    .sidebar-brand-card {
        background: linear-gradient(135deg, #2D2115 0%, #4A3B2C 100%);
        padding: 20px;
        border-radius: 14px;
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0px 4px 12px rgba(45, 33, 21, 0.15);
    }
    .sidebar-brand-card h3 {
        color: #FFFFFF !important;
        margin: 0 !important;
        font-size: 1.2rem !important;
        font-weight: 800 !important;
    }
    .sidebar-brand-card p {
        color: #E2D5C3 !important;
        font-size: 0.8rem;
        margin-top: 4px;
        margin-bottom: 0;
    }
    
    /* User Profile Badge */
    .user-profile-badge {
        display: flex;
        align-items: center;
        gap: 10px;
        background-color: rgba(255, 255, 255, 0.6);
        padding: 10px 14px;
        border-radius: 10px;
        border: 1px solid #E2D5C3;
        margin-bottom: 16px;
    }
    .user-avatar {
        background-color: #8C5A3C;
        color: white;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 0.85rem;
    }

    /* LOGIN & COVER PAGE STYLES */
    .login-card {
        background-color: #FFFFFF;
        padding: 40px 45px;
        border-radius: 20px;
        border: 1px solid #EAE0D5;
        box-shadow: 0px 12px 32px rgba(74, 59, 44, 0.08);
        width: 100%;
        max-width: 460px;
        margin: 0 auto;
    }
    .brand-logo-container { text-align: center; margin-bottom: 15px; }
    .movie-logo-icon {
        background: linear-gradient(135deg, #8C5A3C 0%, #4A3B2C 100%);
        width: 70px;
        height: 70px;
        border-radius: 18px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 2.2rem;
        box-shadow: 0px 6px 16px rgba(140, 90, 60, 0.3);
        margin-bottom: 12px;
    }
    .login-title {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        color: #2D2115 !important;
        text-align: center;
        margin-bottom: 4px !important;
    }

    /* Cover Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, #2D2115 0%, #4A3B2C 50%, #8C5A3C 100%);
        padding: 36px 40px;
        border-radius: 20px;
        margin-bottom: 28px;
        color: white;
        box-shadow: 0px 8px 24px rgba(45, 33, 21, 0.15);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .hero-title {
        color: #FFFFFF !important;
        margin: 0;
        font-size: 2.3rem;
        font-weight: 800;
    }
    .hero-tagline {
        color: #E2D5C3 !important;
        margin-top: 6px;
        font-size: 1.1rem;
    }

    /* Executive Image Cards & Cast Visuals */
    .image-card {
        background-color: #FFFFFF;
        border-radius: 14px;
        border: 1px solid #EAE0D5;
        box-shadow: 0px 4px 14px rgba(0, 0, 0, 0.04);
        overflow: hidden;
        margin-bottom: 24px;
    }
    .image-card img {
        width: 100%;
        height: 200px;
        object-fit: cover;
    }
    .card-content { padding: 20px; }
    .card-content h4 {
        margin-top: 0;
        margin-bottom: 8px;
        color: #8C5A3C !important;
        font-size: 1.15rem;
    }

    /* CINEMA SCREEN & SEATING STYLES */
    .cinema-screen {
        background: linear-gradient(180deg, #8C5A3C 0%, rgba(140, 90, 60, 0.1) 100%);
        height: 18px;
        width: 80%;
        margin: 20px auto 30px auto;
        border-radius: 50% 50% 0 0 / 100% 100% 0 0;
        text-align: center;
        font-size: 0.75rem;
        font-weight: bold;
        color: #FFFFFF;
        letter-spacing: 3px;
        box-shadow: 0px -4px 12px rgba(140, 90, 60, 0.4);
    }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #EAE0D5;
        box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.03);
    }
    div[data-testid="stMetricValue"] {
        color: #8C5A3C !important;
        font-weight: 800;
    }

    /* Buttons */
    .stButton>button {
        background-color: #8C5A3C !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 12px 28px !important;
    }
    .stButton>button:hover {
        background-color: #6F452C !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. AUTHENTICATION CONTROLLER
# -----------------------------------------------------------------------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        st.markdown("""
        <div class="login-card">
            <div class="brand-logo-container">
                <div class="movie-logo-icon">🎬</div>
            </div>
            <h2 class="login-title">Streamline Analytics</h2>
            <div style="color: #8C5A3C; font-weight: 700; text-align: center; text-transform: uppercase; margin-bottom: 8px;">Decoding Box Office & Cinema Booking</div>
            <p style="color: #7A6555; text-align: center; margin-bottom: 24px; font-size: 0.9rem;">Sign in to access analytics and ticket booking</p>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Username", key="login_user", placeholder="Enter your username")
        password = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")
        
        st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
        if st.button("Sign In to Portal", use_container_width=True):
            user_info = backend.authenticate_user(username, password)
            if user_info:
                st.session_state.authenticated = True
                st.session_state.username = user_info[0]
                st.session_state.user_role = user_info[1]
                st.rerun()
            else:
                st.error("Invalid username or password.")

if not st.session_state.authenticated:
    login_page()
    st.stop()

# -----------------------------------------------------------------------------
# 5. DATA SYNTHESIS & BACKEND SEEDING PIPELINE (KARNATAKA & INDIA THEATERS)
# -----------------------------------------------------------------------------
@st.cache_data
def load_or_generate_dataset(samples=1200):
    existing_df = backend.get_catalog_data()
    if not existing_df.empty:
        return existing_df
    
    np.random.seed(42)
    genres_list = ['Drama', 'Comedy', 'Action', 'Documentary', 'Animation', 'Thriller', 'Sci-Fi', 'Romance']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    seasons_map = {'Jan': 'Winter', 'Feb': 'Winter', 'Mar': 'Spring', 'Apr': 'Spring', 'May': 'Spring',
                   'Jun': 'Summer', 'Jul': 'Summer', 'Aug': 'Summer', 'Sep': 'Fall', 'Oct': 'Fall',
                   'Nov': 'Fall', 'Dec': 'Winter'}

    sample_titles = [
        "KGF: Chapter 3", "Kantara: Chapter 1", "RRM: Rise of Empire", "Bangalore Days Revisit", 
        "Echoes of Mysuru", "Western Ghats Mystery", "Neon Nights Bengaluru", "The Heritage of Hampi"
    ]

    cast_members = [
        ("Yash", "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=500&q=80"),
        ("Rishab Shetty", "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=500&q=80"),
        ("Srinidhi Shetty", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&q=80"),
        ("Shivarajkumar", "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=500&q=80"),
        ("Deepika Padukone", "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=500&q=80")
    ]
    
    languages_pool = ["Kannada", "Hindi", "Telugu", "Tamil", "English", "Malayalam"]
    karnataka_theaters = [
        "PVR Forum Mall (Koramangala, Bengaluru)",
        "PVR Superplex (Lulu Mall, Bengaluru)",
        "INOX Mantri Square (Malleshwaram, Bengaluru)",
        "Cinepolis (Nexus Shantiniketan, Bengaluru)",
        "DRC Cinemas (BM Habitat Mall, Mysuru)",
        "PVR Urban Oasis Mall (Hubballi)",
        "Bharat Mall Cinepolis (Mangaluru)",
        "Sangam Multiplex (Belagavi)"
    ]

    data = []
    for idx in range(samples):
        title_name = sample_titles[idx] if idx < len(sample_titles) else f"Indian Cinema Release {idx + 1}"
        g_count = np.random.choice([1, 2, 3], p=[0.5, 0.4, 0.1])
        g_assigned = list(np.random.choice(genres_list, size=g_count, replace=False))
        
        runtime = max(45, min(210, int(np.random.normal(135, 20))))
        release_m = np.random.choice(months)
        is_original = np.random.choice(['Original', 'Licensed'], p=[0.4, 0.6])
        
        imdb_score = round(np.clip(np.random.normal(7.2, 0.8), 1.0, 10.0), 1)
        tmdb_popularity = round(np.random.exponential(scale=45.0) + 15, 2)

        cast_person, cast_img = cast_members[idx % len(cast_members)]
        primary_lang = np.random.choice(languages_pool, p=[0.5, 0.2, 0.1, 0.1, 0.05, 0.05])
        avail_langs = f"{primary_lang}, " + ", ".join(np.random.choice(languages_pool, size=2, replace=False))
        theaters = ", ".join(np.random.choice(karnataka_theaters, size=2, replace=False))

        data.append({
            'Title': title_name,
            'Genres': ", ".join(g_assigned),
            'Cast': cast_person,
            'Cast_Photo': cast_img,
            'Primary_Language': primary_lang,
            'Available_Languages': avail_langs,
            'Theaters_Available': theaters,
            'Runtime_Min': runtime,
            'Release_Month': release_m,
            'Season': seasons_map[release_m],
            'Content_Type': is_original,
            'IMDb_Score': imdb_score,
            'TMDB_Popularity': tmdb_popularity
        })

    generated_df = pd.DataFrame(data)
    backend.save_catalog_data(generated_df)
    return generated_df

# -----------------------------------------------------------------------------
# 6. MACHINE LEARNING MODEL PIPELINE
# -----------------------------------------------------------------------------
@st.cache_resource
def train_predictive_models(df):
    if df.empty: return None, None, [], []
    df_copy = df.copy()
    genre_series = df_copy['Genres'].apply(lambda x: [g.strip() for g in x.split(',')])
    mlb = MultiLabelBinarizer()
    genre_encoded = pd.DataFrame(mlb.fit_transform(genre_series), columns=mlb.classes_, index=df_copy.index)
    cat_features = pd.get_dummies(df_copy[['Season', 'Content_Type']], drop_first=False)
    
    X = pd.concat([df_copy[['Runtime_Min']], genre_encoded, cat_features], axis=1)
    y_rating = df_copy['IMDb_Score']
    y_pop = df_copy['TMDB_Popularity']

    rf_rating = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_rating.fit(X, y_rating)
    
    rf_pop = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_pop.fit(X, y_pop)

    return rf_rating, rf_pop, mlb.classes_, X.columns

# -----------------------------------------------------------------------------
# 7. MAIN INTERFACE & NAVIGATION
# -----------------------------------------------------------------------------
df = load_or_generate_dataset()
rf_rating, rf_pop, genre_list, feature_columns = train_predictive_models(df)

# Sidebar UI
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand-card">
        <h3>🎬 Cinema Core</h3>
        <p>Analytics & Ticket Booking</p>
    </div>
    """, unsafe_allow_html=True)
    
    username = st.session_state.get('username', 'User')
    user_role = st.session_state.get('user_role', 'Analyst')
    st.markdown(f"""
    <div class="user-profile-badge">
        <div class="user-avatar">{username[0].upper()}</div>
        <div style="line-height: 1.2;">
            <div style="font-weight: 700; font-size: 0.9rem; color: #2D2115;">{username.capitalize()}</div>
            <div style="font-size: 0.75rem; color: #7A6555; text-transform: capitalize;">{user_role} Access</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

    st.markdown("---")
    st.info("📍 **Location Target**: Karnataka & Pan-India Theaters Active")

# Cover Banner
st.markdown("""
<div class="hero-banner">
    <div>
        <h1 class="hero-title">🎬 Streamline Analytics & Booking</h1>
        <div class="hero-tagline">Market Intelligence & Ticket Booking Engine</div>
    </div>
    <div style="font-size: 3.5rem;">🍿</div>
</div>
""", unsafe_allow_html=True)

# Tabs Navigation
tab_book, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎟️ Book Movie Tickets",
    "🎯 Executive Insights", 
    "🔍 Search & Cast visual",
    "📊 Genre Analytics", 
    "⏱️ Runtime Window", 
    "📅 Release Timing", 
    "🔮 ML Predictor Engine",
    "💾 Saved History"
])

# -----------------------------------------------------------------------------
# TAB: BOOK MOVIE TICKETS (KARNATAKA & INDIA THEATERS + SEAT SELECTION + PAYMENT)
# -----------------------------------------------------------------------------
with tab_book:
    st.subheader("🎟️ Book Movie Tickets - Karnataka & India Theaters")
    st.markdown("Select your city, theater, movie, seat layout, and execute online payment.")
    
    col_b1, col_b2, col_b3 = st.columns(3)
    
    with col_b1:
        city_selected = st.selectbox(
            "Select City (Karnataka Focus)",
            options=["Bengaluru", "Mysuru", "Hubballi-Dharwad", "Mangaluru", "Belagavi", "Mumbai", "Delhi NCR", "Hyderabad", "Chennai"]
        )
        
    with col_b2:
        karnataka_theaters_map = {
            "Bengaluru": ["PVR Forum Mall (Koramangala)", "PVR Superplex (Lulu Mall)", "INOX Mantri Square (Malleshwaram)", "Cinepolis (Nexus Shantiniketan)"],
            "Mysuru": ["DRC Cinemas (BM Habitat Mall)", "INOX Centre Point Mall"],
            "Hubballi-Dharwad": ["PVR Urban Oasis Mall", "Cinepolis Urban Mall"],
            "Mangaluru": ["Bharat Mall Cinepolis", "PVR Forum Fiza Mall"],
            "Belagavi": ["Sangam Multiplex", "INOX Chandan Cinema"],
            "Mumbai": ["PVR ICON Phoenix Palladium", "Cinepolis Viviana Mall"],
            "Delhi NCR": ["PVR Director's Cut Vasant Kunj", "PVR Anupam Saket"],
            "Hyderabad": ["AMB Cinemas (Gachibowli)", "PVR Forum Sujana Mall"],
            "Chennai": ["SPI Luxe Cinema (Phoenix Marketcity)", "PVR VR Chennai"]
        }
        theater_options = karnataka_theaters_map.get(city_selected, ["PVR Cinemas Central"])
        theater_selected = st.selectbox("Select Cinema Theater", options=theater_options)
        
    with col_b3:
        movie_selected = st.selectbox("Select Movie", options=df['Title'].unique())

    st.markdown("---")
    
    # Show Selected Movie Visual Banner & Details
    selected_movie_row = df[df['Title'] == movie_selected].iloc[0]
    
    b_col1, b_col2 = st.columns([1, 2])
    with b_col1:
        st.markdown(f"""
        <div class="image-card">
            <img src="{selected_movie_row.get('Cast_Photo', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&q=80')}" alt="Cast & Movie Image">
            <div class="card-content">
                <h4>{selected_movie_row['Title']}</h4>
                <p><strong>Lead Cast:</strong> {selected_movie_row.get('Cast', 'N/A')}</p>
                <p><strong>Language:</strong> {selected_movie_row.get('Primary_Language', 'Kannada')}</p>
                <p><strong>IMDb Rating:</strong> ⭐ {selected_movie_row['IMDb_Score']} / 10</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with b_col2:
        st.markdown("### 💺 Interactive Seat Selection")
        st.write("Click on seats to add or remove them from your booking.")
        
        # Screen Visual Representation
        st.markdown('<div class="cinema-screen">SCREEN THIS WAY</div>', unsafe_allow_html=True)
        
        # Seat Configuration Setup
        pricing_tiers = {
            "Recliner VIP (Row A-B)": {"rows": ["A", "B"], "price": 600},
            "Prime Gold (Row C-E)": {"rows": ["C", "D", "E"], "price": 350},
            "Classic Silver (Row F-H)": {"rows": ["F", "G", "H"], "price": 200}
        }
        
        # Initialize selected seats state
        if 'selected_seats' not in st.session_state:
            st.session_state.selected_seats = []
            
        # Seat Grid layout
        for category, info in pricing_tiers.items():
            st.markdown(f"**{category} - ₹{info['price']}**")
            for row in info['rows']:
                seat_cols = st.columns(10)
                for seat_num in range(1, 11):
                    seat_id = f"{row}{seat_num}"
                    # Randomly set some seats as already booked/sold out
                    is_sold = (hash(seat_id + movie_selected) % 7 == 0)
                    
                    with seat_cols[seat_num - 1]:
                        if is_sold:
                            st.button(f"❌ {seat_id}", key=f"btn_{seat_id}", disabled=True, help="Sold Out")
                        else:
                            is_selected = seat_id in st.session_state.selected_seats
                            btn_label = f"✅ {seat_id}" if is_selected else f"💺 {seat_id}"
                            if st.button(btn_label, key=f"btn_{seat_id}"):
                                if is_selected:
                                    st.session_state.selected_seats.remove(seat_id)
                                else:
                                    st.session_state.selected_seats.append(seat_id)
                                st.rerun()

        # Calculate Price Breakdown
        st.markdown("---")
        st.subheader("💳 Booking & Payment Summary")
        
        total_price = 0
        for seat in st.session_state.selected_seats:
            row_letter = seat[0]
            if row_letter in ["A", "B"]:
                total_price += 600
            elif row_letter in ["C", "D", "E"]:
                total_price += 350
            else:
                total_price += 200

        col_pay1, col_pay2 = st.columns(2)
        with col_pay1:
            st.write(f"**Selected Seats:** {', '.join(st.session_state.selected_seats) if st.session_state.selected_seats else 'None'}")
            st.write(f"**City:** {city_selected}")
            st.write(f"**Theater:** {theater_selected}")
            st.markdown(f"### **Total Amount: ₹{total_price}**")

        with col_pay2:
            if st.session_state.selected_seats:
                st.markdown("**Online Payment Gateway Options**")
                payment_method = st.radio("Choose Payment Method", options=["UPI (GPay / PhonePe / Paytm)", "Credit / Debit Card", "Net Banking (SBI, HDFC, ICICI)"])
                
                if st.button("🚀 Pay Now & Confirm Booking", use_container_width=True):
                    backend.save_booking(
                        movie=movie_selected,
                        city=city_selected,
                        theater=theater_selected,
                        seats=", ".join(st.session_state.selected_seats),
                        amount=total_price,
                        pay_method=payment_method,
                        status="CONFIRMED"
                    )
                    st.balloons()
                    st.success(f"🎉 Booking Confirmed! {len(st.session_state.selected_seats)} seats reserved at {theater_selected}.")
                    st.session_state.selected_seats = []
            else:
                st.info("Select at least one seat from the seating layout above to proceed to payment.")

# -----------------------------------------------------------------------------
# TAB 1: EXECUTIVE INSIGHTS
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Key Findings & Strategic Recommendations")
    col1, col2 = st.columns(2)
    
    with col1:
        df_expanded = df.assign(Genre_List=df['Genres'].str.split(', ')).explode('Genre_List')
        genre_scores = df_expanded.groupby('Genre_List')['IMDb_Score'].mean().sort_values(ascending=False)
        top_g = genre_scores.index[0]
        
        st.markdown(f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80" alt="Cinema">
            <div class="card-content">
                <h4>1. Top Performing Genre: {top_g}</h4>
                <p><strong>{top_g}</strong> leads average ratings at <strong>{genre_scores.iloc[0]:.2f} / 10</strong> in catalog analysis.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        df['Runtime_Bin'] = pd.cut(df['Runtime_Min'], bins=[0, 80, 100, 120, 140, 240], 
                                  labels=['<80 min', '80-100 min', '100-120 min', '120-140 min', '140+ min'])
        best_bin = df.groupby('Runtime_Bin', observed=False)['IMDb_Score'].mean().idxmax()
        
        st.markdown(f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?auto=format&fit=crop&w=800&q=80" alt="Film Reel">
            <div class="card-content">
                <h4>2. Optimal Duration Window: {best_bin}</h4>
                <p>Titles in the <strong>{best_bin}</strong> duration bracket exhibit optimal audience retention.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        season_perf = df.groupby('Season')['TMDB_Popularity'].mean().sort_values(ascending=False)
        
        st.markdown(f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1518676599625-5832a514d026?auto=format&fit=crop&w=800&q=80" alt="Winter Season">
            <div class="card-content">
                <h4>3. Peak Launch Window: {season_perf.index[0]}</h4>
                <p>Releases during <strong>{season_perf.index[0]}</strong> achieve peak engagement (Avg Popularity: <strong>{season_perf.iloc[0]:.1f}</strong>).</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        lic_counts = df['Content_Type'].value_counts(normalize=True) * 100
        
        st.markdown(f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?auto=format&fit=crop&w=800&q=80" alt="Streaming">
            <div class="card-content">
                <h4>4. Catalog Composition Ratio</h4>
                <p>Portfolio consists of <strong>{lic_counts.get('Licensed', 0):.1f}% Licensed</strong> and <strong>{lic_counts.get('Original', 0):.1f}% Originals</strong>.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 2: SEARCH & CAST VISUALS
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("🔍 Movie Search & Cast Visual Card")
    
    col_search1, col_search2, col_search3 = st.columns([2, 1, 1])
    with col_search1:
        search_query = st.text_input("Search title or cast", placeholder="Type title or actor name...")
    with col_search2:
        genre_filter = st.multiselect("Filter Genre", options=list(genre_list))
    with col_search3:
        lang_filter = st.multiselect("Filter Language", options=list(df['Primary_Language'].unique()))

    filtered_df = df.copy()
    if search_query:
        title_match = filtered_df['Title'].str.contains(search_query, case=False, na=False)
        cast_match = filtered_df['Cast'].str.contains(search_query, case=False, na=False)
        filtered_df = filtered_df[title_match | cast_match]
    if genre_filter:
        pattern = '|'.join(genre_filter)
        filtered_df = filtered_df[filtered_df['Genres'].str.contains(pattern, case=False, na=False)]
    if lang_filter:
        filtered_df = filtered_df[filtered_df['Primary_Language'].isin(lang_filter)]

    if len(filtered_df) > 0:
        selected_title = st.selectbox("Select title:", options=filtered_df['Title'].values)
        movie_data = filtered_df[filtered_df['Title'] == selected_title].iloc[0]
        
        st.markdown("---")
        card_col1, card_col2 = st.columns([1, 2])
        
        with card_col1:
            st.markdown(f"""
            <div class="image-card">
                <img src="{movie_data.get('Cast_Photo', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&q=80')}" alt="Cast Photo">
                <div class="card-content">
                    <h4>{movie_data['Title']}</h4>
                    <p><strong>🎭 Lead Cast:</strong> {movie_data.get('Cast', 'N/A')}</p>
                    <p><strong>Genres:</strong> {movie_data['Genres']}</p>
                    <p><strong>🗣️ Primary Language:</strong> {movie_data.get('Primary_Language', 'N/A')}</p>
                    <p><strong>🌍 Available Languages:</strong> {movie_data.get('Available_Languages', 'N/A')}</p>
                    <p><strong>🏛️ Theaters Available:</strong> {movie_data.get('Theaters_Available', 'N/A')}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with card_col2:
            m1, m2 = st.columns(2)
            with m1:
                st.metric("IMDb Score", f"{movie_data['IMDb_Score']} / 10")
            with m2:
                st.metric("Popularity", f"{movie_data['TMDB_Popularity']}")
            st.dataframe(filtered_df.head(10), use_container_width=True)
    else:
        st.warning("No titles found.")

# -----------------------------------------------------------------------------
# TAB 3: GENRE PERFORMANCE
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Genre Ratings Breakdown")
    df_expanded = df.assign(Genre_List=df['Genres'].str.split(', ')).explode('Genre_List')
    g_summary = df_expanded.groupby('Genre_List').agg(Avg_Rating=('IMDb_Score', 'mean')).reset_index().sort_values(by='Avg_Rating', ascending=True)

    fig_g = px.bar(g_summary, x='Avg_Rating', y='Genre_List', orientation='h', color='Avg_Rating', color_continuous_scale=['#E2D5C3', '#8C5A3C'])
    fig_g.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#1E150C', size=13))
    st.plotly_chart(fig_g, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: RUNTIME ENGAGEMENT
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("Runtime Duration vs. Audience Response")
    fig_run = px.scatter(df, x='Runtime_Min', y='IMDb_Score', color='Content_Type', size='TMDB_Popularity', color_discrete_sequence=['#8C5A3C', '#D4A373'])
    fig_run.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#1E150C', size=13))
    st.plotly_chart(fig_run, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: SEASONALITY & RELEASE
# -----------------------------------------------------------------------------
with tab5:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Monthly Popularity")
        m_summary = df.groupby('Release_Month')['TMDB_Popularity'].mean().reset_index()
        fig_m = px.line(m_summary, x='Release_Month', y='TMDB_Popularity', markers=True)
        fig_m.update_traces(line_color='#8C5A3C', line_width=3)
        fig_m.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_m, use_container_width=True)
    with col_b:
        st.subheader("Seasonal Engagement")
        s_summary = df.groupby('Season')['TMDB_Popularity'].mean().reset_index()
        fig_s = px.bar(s_summary, x='Season', y='TMDB_Popularity', color='Season', color_discrete_sequence=['#8C5A3C', '#A87654', '#C4936F', '#E2D5C3'])
        fig_s.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_s, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 6: ML PREDICTOR ENGINE
# -----------------------------------------------------------------------------
with tab6:
    st.subheader("🔮 Predictive Machine Learning Engine")
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        input_genres = st.multiselect("Targeted Genres", options=list(genre_list), default=[genre_list[0]])
        input_runtime = st.slider("Target Runtime (Minutes)", min_value=45, max_value=210, value=110)
    with col_in2:
        input_season = st.selectbox("Release Season", options=['Winter', 'Spring', 'Summer', 'Fall'])
        input_type = st.radio("Content Classification", options=['Original', 'Licensed'], horizontal=True)

    if st.button("🚀 Execute Prediction Model", use_container_width=True):
        input_dict = {col: 0 for col in feature_columns}
        input_dict['Runtime_Min'] = input_runtime
        for g in input_genres:
            if g in input_dict: input_dict[g] = 1
        if f"Season_{input_season}" in input_dict: input_dict[f"Season_{input_season}"] = 1
        if f"Content_Type_{input_type}" in input_dict: input_dict[f"Content_Type_{input_type}"] = 1
            
        input_df = pd.DataFrame([input_dict])
        pred_rating = rf_rating.predict(input_df)[0]
        pred_pop = rf_pop.predict(input_df)[0]
        
        backend.log_prediction(genres=", ".join(input_genres), runtime=input_runtime, season=input_season, c_type=input_type, imdb=round(pred_rating, 2), pop=round(pred_pop, 2))
        
        st.markdown("---")
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric(label="Predicted IMDb Rating", value=f"{pred_rating:.2f} / 10")
        with res_col2:
            st.metric(label="Predicted TMDB Popularity", value=f"{pred_pop:.2f}")

# -----------------------------------------------------------------------------
# TAB 7: SAVED HISTORY
# -----------------------------------------------------------------------------
with tab7:
    st.subheader("💾 Saved Prediction Audit Log")
    history_df = backend.get_prediction_history()
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("No saved prediction history.")
