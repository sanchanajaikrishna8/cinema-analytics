import hashlib
import io
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MultiLabelBinarizer
import streamlit as st

# PDF & QR Code Generation Imports
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Streamline Analytics - Cinema Intelligence & Booking",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# PDF TICKET GENERATOR FUNCTION
# -----------------------------------------------------------------------------
def generate_ticket_pdf(booking_id, movie, city, theater, seats, amount, pay_method):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()

    # Create Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#2D2115'),
        alignment=1,
        spaceAfter=15
    )
    
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=colors.HexColor('#8C5A3C')
    )
    
    val_style = ParagraphStyle(
        'ValStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        textColor=colors.HexColor('#1E150C')
    )

    # 1. Header Title
    story.append(Paragraph("🎬 CINEMA CORE - MOVIE ADMISSION PASS", title_style))
    story.append(Spacer(1, 10))

    # 2. Generate QR Code Image
    qr_data = f"BOOKING-ID: #{booking_id} | MOVIE: {movie} | SEATS: {seats} | THEATER: {theater}"
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    img_buffer = io.BytesIO()
    qr_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    qr_reportlab_img = Image(img_buffer, width=120, height=120)

    # 3. Build Key-Value Details Layout
    ticket_data = [
        [Paragraph("Booking Reference:", label_style), Paragraph(f"#{booking_id}", val_style), qr_reportlab_img],
        [Paragraph("Movie Title:", label_style), Paragraph(str(movie), val_style), ""],
        [Paragraph("City & Location:", label_style), Paragraph(str(city), val_style), ""],
        [Paragraph("Cinema Theater:", label_style), Paragraph(str(theater), val_style), ""],
        [Paragraph("Reserved Seats:", label_style), Paragraph(str(seats), val_style), ""],
        [Paragraph("Total Amount:", label_style), Paragraph(f"₹{amount}", val_style), ""],
        [Paragraph("Payment Method:", label_style), Paragraph(str(pay_method), val_style), ""],
        [Paragraph("Booking Status:", label_style), Paragraph("CONFIRMED / PAID", val_style), ""]
    ]

    t = Table(ticket_data, colWidths=[130, 260, 140])
    t.setStyle(TableStyle([
        ('SPAN', (2, 0), (2, 7)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (1, -1), 0.5, colors.HexColor('#EAE0D5')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAF7F2')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#D8C8B8')),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # 4. Scanner Note
    note_style = ParagraphStyle(
        'NoteStyle',
        parent=styles['Italic'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        textColor=colors.HexColor('#7A6555'),
        alignment=1
    )
    story.append(Paragraph("Scan this QR Code at the entry gate usher counter for direct admission.", note_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'analyst'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Title TEXT NOT NULL,
                    Genres TEXT NOT NULL,
                    Cast TEXT DEFAULT 'N/A',
                    Cast_Photo TEXT DEFAULT '',
                    Primary_Language TEXT DEFAULT 'Kannada',
                    Available_Languages TEXT DEFAULT 'Kannada, English, Hindi',
                    Theaters_Available TEXT DEFAULT 'N/A',
                    Trailer_URL TEXT DEFAULT 'https://www.youtube.com',
                    Runtime_Min INTEGER NOT NULL,
                    Release_Month TEXT NOT NULL,
                    Season TEXT NOT NULL,
                    Content_Type TEXT NOT NULL,
                    IMDb_Score REAL NOT NULL,
                    TMDB_Popularity REAL NOT NULL
                )
            """)
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
            if "id" in df.columns:
                df = df.drop(columns=["id"])
            return df

    def save_catalog_data(self, df):
        with self._get_connection() as conn:
            df.to_sql("movies", conn, if_exists="replace", index=False)

    def save_booking(self, movie, city, theater, seats, amount, pay_method, status="CONFIRMED"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO movie_bookings 
                (movie_title, city, theater, seats, total_amount, payment_method, payment_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (movie, city, theater, str(seats), amount, pay_method, status))
            conn.commit()
            return cursor.lastrowid

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

    def get_booking_history(self):
        with self._get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM movie_bookings ORDER BY timestamp DESC", conn)

backend = AnalyticsBackend()

# -----------------------------------------------------------------------------
# 3. GLOBAL CUSTOM STYLING & SEAT MAP UI
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background-color: #FAF7F2;
        color: #1E150C;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F5ECE0 0%, #EFE3D3 100%) !important;
        border-right: 1px solid #D8C8B8 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #2D2115 !important;
    }
    
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
        height: 380px;
        object-fit: cover;
    }
    .card-content { padding: 20px; color: #1E150C !important; }
    .card-content h4 {
        margin-top: 0;
        margin-bottom: 8px;
        color: #8C5A3C !important;
        font-size: 1.15rem;
    }

    .payment-summary-box {
        background-color: #FFFFFF;
        border: 1px solid #D8C8B8;
        border-radius: 12px;
        padding: 20px;
        color: #1E150C !important;
        font-weight: 600;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.05);
    }
    .payment-summary-box p, .payment-summary-box span, .payment-summary-box div {
        color: #1E150C !important;
    }

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
    
    .trailer-link-btn {
        display: inline-block;
        background-color: #FF0000;
        color: #FFFFFF !important;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: bold;
        text-decoration: none;
        margin-left: 8px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. AUTHENTICATION CONTROLLER
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
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
# 5. DATA SYNTHESIS PIPELINE WITH REAL MOVIE POSTERS
# -----------------------------------------------------------------------------
@st.cache_data
def load_or_generate_dataset(samples=1200):
    real_movies = [
        {"Title": "Kantara", "Lang": "Kannada", "Genres": "Action, Thriller, Drama", "Cast": "Rishab Shetty", "Trailer": "https://www.youtube.com/watch?v=8mrVmf239GU", "Img": "https://upload.wikimedia.org/wikipedia/en/8/84/Kantara_poster.jpeg"},
        {"Title": "KGF: Chapter 2", "Lang": "Kannada", "Genres": "Action, Crime, Drama", "Cast": "Yash", "Trailer": "https://www.youtube.com/watch?v=JKa05nyUmuQ", "Img": "https://upload.wikimedia.org/wikipedia/en/d/d0/K.G.F_Chapter_2.jpg"},
        {"Title": "777 Charlie", "Lang": "Kannada", "Genres": "Adventure, Comedy, Drama", "Cast": "Rakshit Shetty", "Trailer": "https://www.youtube.com/watch?v=RN9-Yl58c-8", "Img": "https://upload.wikimedia.org/wikipedia/en/a/a3/777_Charlie_poster.jpg"},
        {"Title": "Vikrant Rona", "Lang": "Kannada", "Genres": "Action, Mystery, Thriller", "Cast": "Kiccha Sudeep", "Trailer": "https://www.youtube.com/watch?v=Ypdu_Wc53s0", "Img": "https://upload.wikimedia.org/wikipedia/en/b/b8/Vikrant_Rona_poster.jpg"},
        {"Title": "Jawan", "Lang": "Hindi", "Genres": "Action, Thriller", "Cast": "Shah Rukh Khan", "Trailer": "https://www.youtube.com/watch?v=COv52Qyctws", "Img": "https://upload.wikimedia.org/wikipedia/en/3/39/Jawan_film_poster.jpg"},
        {"Title": "Stree 2", "Lang": "Hindi", "Genres": "Comedy, Horror", "Cast": "Rajkummar Rao, Shraddha Kapoor", "Trailer": "https://www.youtube.com/watch?v=KVnheXywIbU", "Img": "https://upload.wikimedia.org/wikipedia/en/7/7f/Stree_2_poster.jpg"},
        {"Title": "Dangal", "Lang": "Hindi", "Genres": "Biography, Drama, Sport", "Cast": "Aamir Khan", "Trailer": "https://www.youtube.com/watch?v=x_7YlGv9u1g", "Img": "https://upload.wikimedia.org/wikipedia/en/9/99/Dangal_Poster.jpg"},
        {"Title": "Pathaan", "Lang": "Hindi", "Genres": "Action, Adventure, Thriller", "Cast": "Shah Rukh Khan, Deepika Padukone", "Trailer": "https://www.youtube.com/watch?v=vqu4z34wENw", "Img": "https://upload.wikimedia.org/wikipedia/en/c/c3/Pathaan_film_poster.jpg"},
        {"Title": "Oppenheimer", "Lang": "English", "Genres": "Biography, Drama, History", "Cast": "Cillian Murphy", "Trailer": "https://www.youtube.com/watch?v=uYPbbksJxIg", "Img": "https://upload.wikimedia.org/wikipedia/en/4/4a/Oppenheimer_%28film%29.jpg"},
        {"Title": "Avatar: The Way of Water", "Lang": "English", "Genres": "Action, Adventure, Sci-Fi", "Cast": "Sam Worthington", "Trailer": "https://www.youtube.com/watch?v=d9MyW72ELq0", "Img": "https://upload.wikimedia.org/wikipedia/en/5/54/Avatar_The_Way_of_Water_poster.jpg"},
        {"Title": "Inception", "Lang": "English", "Genres": "Action, Adventure, Sci-Fi", "Cast": "Leonardo DiCaprio", "Trailer": "https://www.youtube.com/watch?v=YoHD9XEInc0", "Img": "https://upload.wikimedia.org/wikipedia/en/2/2e/Inception_%282010%29_theatrical_poster.jpg"},
        {"Title": "Interstellar", "Lang": "English", "Genres": "Adventure, Drama, Sci-Fi", "Cast": "Matthew McConaughey", "Trailer": "https://www.youtube.com/watch?v=zSWdZVtXT7E", "Img": "https://upload.wikimedia.org/wikipedia/en/b/bc/Interstellar_film_poster.jpg"}
    ]

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    seasons_map = {"Jan": "Winter", "Feb": "Winter", "Mar": "Spring", "Apr": "Spring", "May": "Spring", "Jun": "Summer", "Jul": "Summer", "Aug": "Summer", "Sep": "Fall", "Oct": "Fall", "Nov": "Fall", "Dec": "Winter"}
    karnataka_theaters = [
        "PVR Forum Mall (Koramangala, Bengaluru)",
        "PVR Superplex (Lulu Mall, Bengaluru)",
        "INOX Mantri Square (Malleshwaram, Bengaluru)",
        "Cinepolis (Nexus Shantiniketan, Bengaluru)",
        "DRC Cinemas (BM Habitat Mall, Mysuru)",
        "PVR Urban Oasis Mall (Hubballi)",
        "Bharat Mall Cinepolis (Mangaluru)"
    ]

    np.random.seed(42)
    data = []
    for idx in range(samples):
        item = real_movies[idx % len(real_movies)]
        runtime = max(90, min(180, int(np.random.normal(140, 15))))
        release_m = np.random.choice(months)
        is_original = np.random.choice(["Original", "Licensed"], p=[0.4, 0.6])
        imdb_score = round(np.clip(np.random.normal(7.8, 0.6), 5.0, 9.8), 1)
        tmdb_popularity = round(np.random.exponential(scale=55.0) + 20, 2)
        theaters = ", ".join(np.random.choice(karnataka_theaters, size=2, replace=False))
        
        data.append({
            "Title": item["Title"],
            "Genres": item["Genres"],
            "Cast": item["Cast"],
            "Cast_Photo": item["Img"],
            "Primary_Language": item["Lang"],
            "Available_Languages": f"{item['Lang']}, English, Hindi",
            "Theaters_Available": theaters,
            "Trailer_URL": item["Trailer"],
            "Runtime_Min": runtime,
            "Release_Month": release_m,
            "Season": seasons_map[release_m],
            "Content_Type": is_original,
            "IMDb_Score": imdb_score,
            "TMDB_Popularity": tmdb_popularity
        })

    generated_df = pd.DataFrame(data)
    backend.save_catalog_data(generated_df)
    return generated_df


# -----------------------------------------------------------------------------
# 6. MACHINE LEARNING MODEL PIPELINE
# -----------------------------------------------------------------------------
@st.cache_resource
def train_predictive_models(df):
    if df.empty:
        return None, None, [], []
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
    
    username = st.session_state.get("username", "User")
    user_role = st.session_state.get("user_role", "Analyst")
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
    st.info("📍 **Location Target**: Karnataka & Pan-India (English, Hindi, Kannada)")

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
    "🔍 Search & Movie Poster", 
    "📊 Genre Analytics", 
    "⏱️ Runtime Window", 
    "📅 Release Timing", 
    "🔮 ML Predictor Engine",
    "💾 Saved History"
])

# -----------------------------------------------------------------------------
# TAB: BOOK MOVIE TICKETS
# -----------------------------------------------------------------------------
with tab_book:
    st.subheader("🎟️ Book Movie Tickets - English, Hindi & Kannada Titles")
    st.markdown("Select your city, theater, movie, seat layout, and execute online payment.")
    
    col_b1, col_b2, col_b3 = st.columns(3)
    
    with col_b1:
        city_selected = st.selectbox("Select City", options=[
            "Bengaluru", "Mysuru", "Hubballi-Dharwad", "Mangaluru", "Mumbai", "Delhi NCR", "Hyderabad"
        ])
    
    with col_b2:
        karnataka_theaters_map = {
            "Bengaluru": ["PVR Forum Mall (Koramangala)", "PVR Superplex (Lulu Mall)", "INOX Mantri Square (Malleshwaram)", "Cinepolis (Nexus Shantiniketan)"],
            "Mysuru": ["DRC Cinemas (BM Habitat Mall)", "INOX Centre Point Mall"],
            "Hubballi-Dharwad": ["PVR Urban Oasis Mall", "Cinepolis Urban Mall"],
            "Mangaluru": ["Bharat Mall Cinepolis", "PVR Forum Fiza Mall"],
            "Mumbai": ["PVR ICON Phoenix Palladium", "Cinepolis Viviana Mall"],
            "Delhi NCR": ["PVR Director's Cut Vasant Kunj", "PVR Anupam Saket"],
            "Hyderabad": ["AMB Cinemas (Gachibowli)", "PVR Forum Sujana Mall"]
        }
        theater_options = karnataka_theaters_map.get(city_selected, ["PVR Cinemas Central"])
        theater_selected = st.selectbox("Select Cinema Theater", options=theater_options)
        
    with col_b3:
        movie_selected = st.selectbox("Select Movie", options=df["Title"].unique())

    st.markdown("---")
    
    selected_movie_row = df[df["Title"] == movie_selected].iloc[0]
    
    b_col1, b_col2 = st.columns([1, 2])
    with b_col1:
        default_img = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80"
        movie_poster_url = selected_movie_row.get("Cast_Photo")
        if not movie_poster_url or not isinstance(movie_poster_url, str):
            movie_poster_url = default_img

        trailer_url = selected_movie_row.get("Trailer_URL", "https://www.youtube.com")

        st.markdown(f"""
        <div class="image-card">
            <img src="{movie_poster_url}" alt="{selected_movie_row['Title']} Poster">
            <div class="card-content">
                <h4>
                    {selected_movie_row['Title']} 
                    <a href="{trailer_url}" target="_blank" class="trailer-link-btn">▶️ Watch Trailer</a>
                </h4>
                <p><strong>Language:</strong> {selected_movie_row.get('Primary_Language', 'Kannada')}</p>
                <p><strong>Lead Cast:</strong> {selected_movie_row.get('Cast', 'N/A')}</p>
                <p><strong>IMDb Rating:</strong> ⭐ {selected_movie_row['IMDb_Score']} / 10</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with b_col2:
        st.markdown("### 💺 Interactive Seat Selection")
        st.write("Click on seats to add or remove them from your booking.")
        
        st.markdown('<div class="cinema-screen">SCREEN THIS WAY</div>', unsafe_allow_html=True)
        
        pricing_tiers = {
            "Recliner VIP (Row A-B)": {"rows": ["A", "B"], "price": 600},
            "Prime Gold (Row C-E)": {"rows": ["C", "D", "E"], "price": 350},
            "Classic Silver (Row F-H)": {"rows": ["F", "G", "H"], "price": 200}
        }
        
        if "selected_seats" not in st.session_state:
            st.session_state.selected_seats = []
            
        for category, info in pricing_tiers.items():
            st.markdown(f"**{category} - ₹{info['price']}**")
            for row in info["rows"]:
                seat_cols = st.columns(10)
                for seat_num in range(1, 11):
                    seat_id = f"{row}{seat_num}"
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
            st.markdown(f"""
            <div class="payment-summary-box">
                <p style="font-size: 1.1rem; font-weight: 700;">Selected Movie: {movie_selected}</p>
                <p><strong>Selected Seats:</strong> {', '.join(st.session_state.selected_seats) if st.session_state.selected_seats else 'None'}</p>
                <p><strong>City:</strong> {city_selected}</p>
                <p><strong>Theater:</strong> {theater_selected}</p>
                <hr style="border-color: #D8C8B8;">
                <h3 style="color: #1E150C !important; font-weight: 800; margin: 0;">Total Payable: ₹{total_price}</h3>
            </div>
            """, unsafe_allow_html=True)

        with col_pay2:
            if st.session_state.selected_seats:
                payment_method = st.radio(
                    "Select Payment Gateway",
                    options=["UPI (Google Pay / PhonePe / Paytm)", "Credit / Debit Card", "Net Banking"],
                    key="pay_method_choice"
                )
                
                if st.button("💳 Confirm Booking & Pay Now", use_container_width=True):
                    # Save booking to SQLite database
                    booking_id = backend.save_booking(
                        movie=movie_selected,
                        city=city_selected,
                        theater=theater_selected,
                        seats=", ".join(st.session_state.selected_seats),
                        amount=total_price,
                        pay_method=payment_method,
                        status="CONFIRMED"
                    )
                    
                    # Store booking details into session state to maintain state across reruns
                    st.session_state["last_booking"] = {
                        "booking_id": booking_id,
                        "movie": movie_selected,
                        "city": city_selected,
                        "theater": theater_selected,
                        "seats": ", ".join(st.session_state.selected_seats),
                        "amount": total_price,
                        "pay_method": payment_method
                    }
                    
                    # Clear selected seats state
                    st.session_state.selected_seats = []
                    st.rerun()
            else:
                st.warning("⚠️ Please select at least one seat to proceed with payment.")

        # PDF Download display block
        if "last_booking" in st.session_state:
            booking = st.session_state["last_booking"]
            
            st.markdown("---")
            st.success(f"🎉 **Booking Confirmed!** Reference ID: **#{booking['booking_id']}**")
            
            pdf_bytes = generate_ticket_pdf(
                booking_id=booking["booking_id"],
                movie=booking["movie"],
                city=booking["city"],
                theater=booking["theater"],
                seats=booking["seats"],
                amount=booking["amount"],
                pay_method=booking["pay_method"]
            )
            
            dl_col1, dl_col2 = st.columns([2, 1])
            with dl_col1:
                st.download_button(
                    label=f"📄 Download PDF Admission Ticket (Pass #{booking['booking_id']})",
                    data=pdf_bytes,
                    file_name=f"CinemaCore_Ticket_{booking['booking_id']}.pdf",
                    mime="application/pdf",
                    key=f"download_pdf_{booking['booking_id']}",
                    use_container_width=True
                )
            with dl_col2:
                if st.button("❌ Dismiss Ticket", use_container_width=True):
                    del st.session_state["last_booking"]
                    st.rerun()


# -----------------------------------------------------------------------------
# TAB 1: EXECUTIVE INSIGHTS
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("🎯 Executive Dashboard & Key Metrics")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Total Movies in Catalog", len(df))
    with col_m2:
        st.metric("Avg IMDb Rating", f"{df['IMDb_Score'].mean():.2f} / 10")
    with col_m3:
        st.metric("Avg TMDB Popularity", f"{df['TMDB_Popularity'].mean():.1f}")
    with col_m4:
        st.metric("Avg Runtime", f"{int(df['Runtime_Min'].mean())} min")
        
    st.markdown("---")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("### IMDb Score Distribution")
        fig_rating = px.histogram(df, x="IMDb_Score", nbins=20, color_discrete_sequence=['#8C5A3C'])
        fig_rating.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_rating, use_container_width=True)
        
    with col_g2:
        st.markdown("### Content Distribution by Language")
        fig_lang = px.pie(df, names="Primary_Language", color_discrete_sequence=px.colors.sequential.Amber)
        fig_lang.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_lang, use_container_width=True)


# -----------------------------------------------------------------------------
# TAB 2: SEARCH & MOVIE POSTER
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("🔍 Movie Catalog & Posters")
    
    search_query = st.text_input("Search movie title, cast, or genre...", placeholder="e.g., Kantara, Action, Yash")
    
    filtered_df = df.copy()
    if search_query:
        query = search_query.lower()
        filtered_df = filtered_df[
            filtered_df['Title'].str.lower().str.contains(query) |
            filtered_df['Cast'].str.lower().str.contains(query) |
            filtered_df['Genres'].str.lower().str.contains(query)
        ]
        
    st.write(f"Showing **{len(filtered_df)}** titles:")
    
    cols = st.columns(3)
    for idx, (_, row) in enumerate(filtered_df.iterrows()):
        with cols[idx % 3]:
            img_url = row.get("Cast_Photo") if isinstance(row.get("Cast_Photo"), str) and row.get("Cast_Photo") else "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80"
            trailer_url = row.get("Trailer_URL", "https://www.youtube.com")
            
            st.markdown(f"""
            <div class="image-card">
                <img src="{img_url}" alt="{row['Title']}">
                <div class="card-content">
                    <h4>{row['Title']}</h4>
                    <p><strong>Genre:</strong> {row['Genres']}</p>
                    <p><strong>Language:</strong> {row['Primary_Language']}</p>
                    <p><strong>Cast:</strong> {row['Cast']}</p>
                    <p><strong>IMDb:</strong> ⭐ {row['IMDb_Score']} | <strong>Popularity:</strong> {row['TMDB_Popularity']}</p>
                    <a href="{trailer_url}" target="_blank" class="trailer-link-btn">▶️ Watch Trailer</a>
                </div>
            </div>
            """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# TAB 3: GENRE ANALYTICS
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("📊 Genre Performance Analytics")
    
    genre_data = []
    for _, row in df.iterrows():
        for g in str(row['Genres']).split(','):
            genre_data.append({
                "Genre": g.strip(),
                "IMDb_Score": row['IMDb_Score'],
                "TMDB_Popularity": row['TMDB_Popularity']
            })
    genre_df = pd.DataFrame(genre_data)
    
    genre_summary = genre_df.groupby("Genre").agg({
        "IMDb_Score": "mean",
        "TMDB_Popularity": "mean",
        "Genre": "count"
    }).rename(columns={"Genre": "Count"}).reset_index()
    
    col_ga1, col_ga2 = st.columns(2)
    with col_ga1:
        fig_g_score = px.bar(
            genre_summary.sort_values(by="IMDb_Score", ascending=False),
            x="Genre", y="IMDb_Score", color="IMDb_Score",
            title="Average IMDb Score by Genre",
            color_continuous_scale="Viridis"
        )
        fig_g_score.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_g_score, use_container_width=True)
        
    with col_ga2:
        fig_g_pop = px.bar(
            genre_summary.sort_values(by="TMDB_Popularity", ascending=False),
            x="Genre", y="TMDB_Popularity", color="TMDB_Popularity",
            title="Average TMDB Popularity by Genre",
            color_continuous_scale="Magma"
        )
        fig_g_pop.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_g_pop, use_container_width=True)


# -----------------------------------------------------------------------------
# TAB 4: RUNTIME WINDOW
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("⏱️ Runtime vs. Audience Ratings & Popularity")
    
    fig_scatter = px.scatter(
        df,
        x="Runtime_Min",
        y="IMDb_Score",
        size="TMDB_Popularity",
        color="Primary_Language",
        hover_name="Title",
        title="Runtime (Minutes) vs. IMDb Score (Bubble Size = TMDB Popularity)"
    )
    fig_scatter.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_scatter, use_container_width=True)


# -----------------------------------------------------------------------------
# TAB 5: RELEASE TIMING
# -----------------------------------------------------------------------------
with tab5:
    st.subheader("📅 Seasonal & Monthly Release Trends")
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly_counts = df["Release_Month"].value_counts().reindex(month_order).reset_index()
        monthly_counts.columns = ["Month", "Releases"]
        
        fig_month = px.line(monthly_counts, x="Month", y="Releases", markers=True, title="Releases by Month")
        fig_month.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_month, use_container_width=True)
        
    with col_t2:
        season_summary = df.groupby("Season")[["IMDb_Score", "TMDB_Popularity"]].mean().reset_index()
        fig_season = px.bar(season_summary, x="Season", y="TMDB_Popularity", title="Average TMDB Popularity by Season", color="Season")
        fig_season.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_season, use_container_width=True)


# -----------------------------------------------------------------------------
# TAB 6: ML PREDICTOR ENGINE
# -----------------------------------------------------------------------------
with tab6:
    st.subheader("🔮 Machine Learning Box-Office & Success Predictor")
    st.write("Input prospective movie metadata to predict expected IMDb Rating and TMDB Popularity Score.")
    
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        p_genres = st.multiselect("Select Genres", options=genre_list, default=["Action", "Drama"])
        p_runtime = st.slider("Runtime (Minutes)", min_value=60, max_value=210, value=135)
        p_season = st.selectbox("Release Season", options=["Winter", "Spring", "Summer", "Fall"])
        p_type = st.selectbox("Content Source", options=["Original", "Licensed"])
        
        predict_btn = st.button("🔮 Predict Success Metrics", use_container_width=True)
        
    with col_p2:
        if predict_btn and rf_rating and rf_pop:
            input_dict = {col: 0 for col in feature_columns}
            
            input_dict['Runtime_Min'] = p_runtime
            
            for g in p_genres:
                if g in input_dict:
                    input_dict[g] = 1
                    
            season_col = f"Season_{p_season}"
            type_col = f"Content_Type_{p_type}"
            if season_col in input_dict:
                input_dict[season_col] = 1
            if type_col in input_dict:
                input_dict[type_col] = 1
                
            input_df = pd.DataFrame([input_dict])
            
            pred_rating = round(float(rf_rating.predict(input_df)[0]), 2)
            pred_popularity = round(float(rf_pop.predict(input_df)[0]), 1)
            
            backend.log_prediction(p_genres, p_runtime, p_season, p_type, pred_rating, pred_popularity)
            
            st.markdown("### 📊 Prediction Results")
            st.metric("Predicted IMDb Score", f"⭐ {pred_rating} / 10")
            st.metric("Predicted TMDB Popularity Index", f"🔥 {pred_popularity}")
            st.success("✅ Prediction logged into backend database!")


# -----------------------------------------------------------------------------
# TAB 7: SAVED HISTORY
# -----------------------------------------------------------------------------
with tab7:
    st.subheader("💾 Persistent Database Records")
    
    hist_tab1, hist_tab2 = st.tabs(["🎟️ Ticket Bookings History", "🔮 ML Predictions History"])
    
    with hist_tab1:
        booking_df = backend.get_booking_history()
        if not booking_df.empty:
            st.dataframe(booking_df, use_container_width=True)
        else:
            st.info("No booking records found yet.")
            
    with hist_tab2:
        prediction_df = backend.get_prediction_history()
        if not prediction_df.empty:
            st.dataframe(prediction_df, use_container_width=True)
        else:
            st.info("No prediction records found yet.")
