import hashlib
import io
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MultiLabelBinarizer
import streamlit as st

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
                    Stream_URL TEXT DEFAULT '',
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
                    ("analyst", self._hash_password("netflix2026"), "analyst"),
                ]
                cursor.executemany(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    default_users,
                )
                conn.commit()

    def authenticate_user(self, username, password):
        hashed = self._hash_password(password)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, role FROM users WHERE username = ? AND password_hash = ?",
                (username, hashed),
            )
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

    def save_booking(
        self,
        movie,
        city,
        theater,
        seats,
        amount,
        pay_method,
        status="CONFIRMED",
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO movie_bookings 
                (movie_title, city, theater, seats, total_amount, payment_method, payment_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (movie, city, theater, str(seats), amount, pay_method, status),
            )
            booking_id = cursor.lastrowid
            conn.commit()
            return booking_id

    def log_prediction(self, genres, runtime, season, c_type, imdb, pop):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO saved_predictions 
                (genres_input, runtime_input, season_input, type_input, predicted_imdb, predicted_pop)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (str(genres), runtime, season, c_type, imdb, pop),
            )
            conn.commit()

    def get_prediction_history(self):
        with self._get_connection() as conn:
            return pd.read_sql_query(
                "SELECT * FROM saved_predictions ORDER BY timestamp DESC", conn
            )

    def get_booking_history(self):
        with self._get_connection() as conn:
            return pd.read_sql_query(
                "SELECT * FROM movie_bookings ORDER BY timestamp DESC", conn
            )


backend = AnalyticsBackend()


# -----------------------------------------------------------------------------
# 3. HELPER FUNCTION: PDF TICKET GENERATOR WITH QR CODE
# -----------------------------------------------------------------------------
def generate_ticket_pdf(booking_id, movie, city, theater, seats, amount):
    qr_data = (
        f"BOOKING ID: #{booking_id}\nMovie: {movie}\nTheater: {theater}, {city}\n"
        f"Seats: {seats}\nAmount: Rs.{amount}\nStatus: CONFIRMED"
    )

    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    pdf_buffer = io.BytesIO()
    p = canvas.Canvas(pdf_buffer, pagesize=letter)

    p.setFillColorRGB(0.18, 0.13, 0.08)
    p.rect(0, 700, 612, 92, fill=1, stroke=0)

    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 22)
    p.drawString(40, 740, "STREAMLINE CINEMAS - E-TICKET")
    p.setFont("Helvetica", 10)
    p.drawString(40, 720, f"Booking Ref: #{booking_id}")

    p.setFillColorRGB(0.1, 0.1, 0.1)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, 660, f"Movie: {movie}")

    p.setFont("Helvetica", 11)
    p.drawString(40, 635, f"City: {city}")
    p.drawString(40, 615, f"Theater: {theater}")
    p.drawString(40, 595, f"Seat(s): {seats}")
    p.drawString(40, 575, f"Total Paid: Rs. {amount}")
    p.drawString(40, 555, "Status: CONFIRMED")

    p.setStrokeColorRGB(0.8, 0.8, 0.8)
    p.setLineWidth(1)
    p.line(40, 535, 572, 535)

    qr_reader = canvas.ImageReader(qr_buffer)
    p.drawImage(qr_reader, 400, 550, width=150, height=150)
    p.setFont("Helvetica-Oblique", 9)
    p.setFillColorRGB(0.4, 0.4, 0.4)
    p.drawString(400, 538, "Scan QR at entry gate")

    p.setFont("Helvetica", 9)
    p.drawString(40, 500, "Please present this e-ticket at the theater entrance.")
    p.drawString(40, 485, "Thank you for booking with Streamline Analytics!")

    p.showPage()
    p.save()

    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


# -----------------------------------------------------------------------------
# 4. STYLING
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
    .stApp { background-color: #FAF7F2; color: #1E150C; font-family: 'Inter', sans-serif; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #F5ECE0 0%, #EFE3D3 100%) !important; border-right: 1px solid #D8C8B8 !important; }
    section[data-testid="stSidebar"] * { color: #2D2115 !important; }
    .sidebar-brand-card { background: linear-gradient(135deg, #2D2115 0%, #4A3B2C 100%); padding: 20px; border-radius: 14px; color: #FFFFFF; text-align: center; margin-bottom: 20px; }
    .sidebar-brand-card h3 { color: #FFFFFF !important; margin: 0 !important; font-size: 1.2rem !important; font-weight: 800 !important; }
    .sidebar-brand-card p { color: #E2D5C3 !important; font-size: 0.8rem; margin-top: 4px; margin-bottom: 0; }
    .user-profile-badge { display: flex; align-items: center; gap: 10px; background-color: rgba(255, 255, 255, 0.6); padding: 10px 14px; border-radius: 10px; border: 1px solid #E2D5C3; margin-bottom: 16px; }
    .user-avatar { background-color: #8C5A3C; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.85rem; }
    .login-card { background-color: #FFFFFF; padding: 40px 45px; border-radius: 20px; border: 1px solid #EAE0D5; box-shadow: 0px 12px 32px rgba(74, 59, 44, 0.08); width: 100%; max-width: 460px; margin: 0 auto; }
    .brand-logo-container { text-align: center; margin-bottom: 15px; }
    .movie-logo-icon { background: linear-gradient(135deg, #8C5A3C 0%, #4A3B2C 100%); width: 70px; height: 70px; border-radius: 18px; display: inline-flex; align-items: center; justify-content: center; font-size: 2.2rem; box-shadow: 0px 6px 16px rgba(140, 90, 60, 0.3); margin-bottom: 12px; }
    .login-title { font-size: 1.8rem !important; font-weight: 800 !important; color: #2D2115 !important; text-align: center; margin-bottom: 4px !important; }
    .hero-banner { background: linear-gradient(135deg, #2D2115 0%, #4A3B2C 50%, #8C5A3C 100%); padding: 36px 40px; border-radius: 20px; margin-bottom: 28px; color: white; display: flex; align-items: center; justify-content: space-between; }
    .hero-title { color: #FFFFFF !important; margin: 0; font-size: 2.3rem; font-weight: 800; }
    .hero-tagline { color: #E2D5C3 !important; margin-top: 6px; font-size: 1.1rem; }
    .image-card { background-color: #FFFFFF; border-radius: 14px; border: 1px solid #EAE0D5; box-shadow: 0px 4px 14px rgba(0, 0, 0, 0.04); overflow: hidden; margin-bottom: 24px; }
    .image-card img { width: 100%; height: 380px; object-fit: cover; }
    .card-content { padding: 20px; color: #1E150C !important; }
    .card-content h4 { margin-top: 0; margin-bottom: 8px; color: #8C5A3C !important; font-size: 1.15rem; }
    .payment-summary-box { background-color: #FFFFFF; border: 1px solid #D8C8B8; border-radius: 12px; padding: 20px; color: #1E150C !important; font-weight: 600; }
    .payment-summary-box p, .payment-summary-box span, .payment-summary-box div { color: #1E150C !important; }
    .cinema-screen { background: linear-gradient(180deg, #8C5A3C 0%, rgba(140, 90, 60, 0.1) 100%); height: 18px; width: 80%; margin: 20px auto 30px auto; border-radius: 50% 50% 0 0 / 100% 100% 0 0; text-align: center; font-size: 0.75rem; font-weight: bold; color: #FFFFFF; letter-spacing: 3px; }
    div[data-testid="stMetric"] { background-color: #FFFFFF; padding: 20px; border-radius: 12px; border: 1px solid #EAE0D5; }
    div[data-testid="stMetricValue"] { color: #8C5A3C !important; font-weight: 800; }
    .stButton>button { background-color: #8C5A3C !important; color: #FFFFFF !important; border-radius: 10px !important; border: none !important; font-weight: 700 !important; font-size: 1rem !important; padding: 12px 28px !important; }
    .stButton>button:hover { background-color: #6F452C !important; }
    .trailer-link-btn { display: inline-block; background-color: #FF0000; color: #FFFFFF !important; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: bold; text-decoration: none; margin-left: 8px; }
    .netflix-section-title { font-size: 1.4rem; font-weight: 800; color: #2D2115; margin: 20px 0 10px 0; border-left: 4px solid #E50914; padding-left: 10px; }
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 5. AUTHENTICATION CONTROLLER
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        st.markdown(
            """
            <div class="login-card">
                <div class="brand-logo-container">
                    <div class="movie-logo-icon">🎬</div>
                </div>
                <h2 class="login-title">Streamline Analytics</h2>
                <div style="color: #8C5A3C; font-weight: 700; text-align: center; text-transform: uppercase; margin-bottom: 8px;">Decoding Box Office & Cinema Booking</div>
                <p style="color: #7A6555; text-align: center; margin-bottom: 24px; font-size: 0.9rem;">Sign in to access analytics and ticket booking</p>
            """,
            unsafe_allow_html=True,
        )

        username = st.text_input(
            "Username", key="login_user", placeholder="Enter your username"
        )
        password = st.text_input(
            "Password", type="password", key="login_pass", placeholder="••••••••"
        )

        st.markdown(
            "<div style='margin-top: 16px;'></div>", unsafe_allow_html=True
        )
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
# 6. DATA SYNTHESIS PIPELINE
# -----------------------------------------------------------------------------
@st.cache_data
def load_or_generate_dataset(samples=1200):
    real_movies = [
        {
            "Title": "Kantara",
            "Lang": "Kannada",
            "Genres": "Action, Thriller, Drama",
            "Cast": "Rishab Shetty",
            "Trailer": "https://www.youtube.com/watch?v=8mrVmf239GU",
            "Stream": "https://www.youtube.com/embed/8mrVmf239GU",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/8/84/Kantara_poster.jpeg"
            ),
        },
        {
            "Title": "KGF: Chapter 2",
            "Lang": "Kannada",
            "Genres": "Action, Crime, Drama",
            "Cast": "Yash",
            "Trailer": "https://www.youtube.com/watch?v=JKa05nyUmuQ",
            "Stream": "https://www.youtube.com/embed/JKa05nyUmuQ",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/d/d0/K.G.F_Chapter_2.jpg"
            ),
        },
        {
            "Title": "777 Charlie",
            "Lang": "Kannada",
            "Genres": "Adventure, Comedy, Drama",
            "Cast": "Rakshit Shetty",
            "Trailer": "https://www.youtube.com/watch?v=RN9-Yl58c-8",
            "Stream": "https://www.youtube.com/embed/RN9-Yl58c-8",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/a/a3/777_Charlie_poster.jpg"
            ),
        },
        {
            "Title": "Vikrant Rona",
            "Lang": "Kannada",
            "Genres": "Action, Mystery, Thriller",
            "Cast": "Kiccha Sudeep",
            "Trailer": "https://www.youtube.com/watch?v=Ypdu_Wc53s0",
            "Stream": "https://www.youtube.com/embed/Ypdu_Wc53s0",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/b/b8/Vikrant_Rona_poster.jpg"
            ),
        },
        {
            "Title": "Jawan",
            "Lang": "Hindi",
            "Genres": "Action, Thriller",
            "Cast": "Shah Rukh Khan",
            "Trailer": "https://www.youtube.com/watch?v=COv52Qyctws",
            "Stream": "https://www.youtube.com/embed/COv52Qyctws",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/3/39/Jawan_film_poster.jpg"
            ),
        },
        {
            "Title": "Stree 2",
            "Lang": "Hindi",
            "Genres": "Comedy, Horror",
            "Cast": "Rajkummar Rao, Shraddha Kapoor",
            "Trailer": "https://www.youtube.com/watch?v=KVnheXywIbU",
            "Stream": "https://www.youtube.com/embed/KVnheXywIbU",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/7/7f/Stree_2_poster.jpg"
            ),
        },
        {
            "Title": "Dangal",
            "Lang": "Hindi",
            "Genres": "Biography, Drama, Sport",
            "Cast": "Aamir Khan",
            "Trailer": "https://www.youtube.com/watch?v=x_7YlGv9u1g",
            "Stream": "https://www.youtube.com/embed/x_7YlGv9u1g",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/9/99/Dangal_Poster.jpg"
            ),
        },
        {
            "Title": "Pathaan",
            "Lang": "Hindi",
            "Genres": "Action, Adventure, Thriller",
            "Cast": "Shah Rukh Khan, Deepika Padukone",
            "Trailer": "https://www.youtube.com/watch?v=vqu4z34wENw",
            "Stream": "https://www.youtube.com/embed/vqu4z34wENw",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/c/c3/Pathaan_film_poster.jpg"
            ),
        },
        {
            "Title": "Oppenheimer",
            "Lang": "English",
            "Genres": "Biography, Drama, History",
            "Cast": "Cillian Murphy",
            "Trailer": "https://www.youtube.com/watch?v=uYPbbksJxIg",
            "Stream": "https://www.youtube.com/embed/uYPbbksJxIg",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/4/4a/Oppenheimer_%28film%29.jpg"
            ),
        },
        {
            "Title": "Avatar: The Way of Water",
            "Lang": "English",
            "Genres": "Action, Adventure, Sci-Fi",
            "Cast": "Sam Worthington",
            "Trailer": "https://www.youtube.com/watch?v=d9MyW72ELq0",
            "Stream": "https://www.youtube.com/embed/d9MyW72ELq0",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/5/54/Avatar_The_Way_of_Water_poster.jpg"
            ),
        },
        {
            "Title": "Inception",
            "Lang": "English",
            "Genres": "Action, Adventure, Sci-Fi",
            "Cast": "Leonardo DiCaprio",
            "Trailer": "https://www.youtube.com/watch?v=YoHD9XEInc0",
            "Stream": "https://www.youtube.com/embed/YoHD9XEInc0",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/2/2e/Inception_%282010%29_theatrical_poster.jpg"
            ),
        },
        {
            "Title": "Interstellar",
            "Lang": "English",
            "Genres": "Adventure, Drama, Sci-Fi",
            "Cast": "Matthew McConaughey",
            "Trailer": "https://www.youtube.com/watch?v=zSWdZVtXT7E",
            "Stream": "https://www.youtube.com/embed/zSWdZVtXT7E",
            "Img": (
                "https://upload.wikimedia.org/wikipedia/en/b/bc/Interstellar_film_poster.jpg"
            ),
        },
    ]

    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    seasons_map = {
        "Jan": "Winter",
        "Feb": "Winter",
        "Mar": "Spring",
        "Apr": "Spring",
        "May": "Spring",
        "Jun": "Summer",
        "Jul": "Summer",
        "Aug": "Summer",
        "Sep": "Fall",
        "Oct": "Fall",
        "Nov": "Fall",
        "Dec": "Winter",
    }
    karnataka_theaters = [
        "PVR Forum Mall (Koramangala, Bengaluru)",
        "PVR Superplex (Lulu Mall, Bengaluru)",
        "INOX Mantri Square (Malleshwaram, Bengaluru)",
        "Cinepolis (Nexus Shantiniketan, Bengaluru)",
        "DRC Cinemas (BM Habitat Mall, Mysuru)",
        "PVR Urban Oasis Mall (Hubballi)",
        "Bharat Mall Cinepolis (Mangaluru)",
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
        theaters = ", ".join(
            np.random.choice(karnataka_theaters, size=2, replace=False)
        )

        data.append({
            "Title": item["Title"],
            "Genres": item["Genres"],
            "Cast": item["Cast"],
            "Cast_Photo": item["Img"],
            "Primary_Language": item["Lang"],
            "Available_Languages": f"{item['Lang']}, English, Hindi",
            "Theaters_Available": theaters,
            "Trailer_URL": item["Trailer"],
            "Stream_URL": item["Stream"],
            "Runtime_Min": runtime,
            "Release_Month": release_m,
            "Season": seasons_map[release_m],
            "Content_Type": is_original,
            "IMDb_Score": imdb_score,
            "TMDB_Popularity": tmdb_popularity,
        })

    generated_df = pd.DataFrame(data)
    backend.save_catalog_data(generated_df)
    return generated_df


# -----------------------------------------------------------------------------
# 7. MACHINE LEARNING MODEL PIPELINE
# -----------------------------------------------------------------------------
@st.cache_resource
def train_predictive_models(df):
    if df.empty:
        return None, None, [], []
    df_copy = df.copy()
    genre_series = df_copy["Genres"].apply(
        lambda x: [g.strip() for g in x.split(",")]
    )
    mlb = MultiLabelBinarizer()
    genre_encoded = pd.DataFrame(
        mlb.fit_transform(genre_series),
        columns=mlb.classes_,
        index=df_copy.index,
    )
    cat_features = pd.get_dummies(
        df_copy[["Season", "Content_Type"]], drop_first=False
    )

    X = pd.concat(
        [df_copy[["Runtime_Min"]], genre_encoded, cat_features], axis=1
    )
    y_rating = df_copy["IMDb_Score"]
    y_pop = df_copy["TMDB_Popularity"]

    rf_rating = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_rating.fit(X, y_rating)

    rf_pop = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_pop.fit(X, y_pop)

    return rf_rating, rf_pop, mlb.classes_, X.columns


# -----------------------------------------------------------------------------
# 8. MAIN INTERFACE & NAVIGATION
# -----------------------------------------------------------------------------
df = load_or_generate_dataset()
rf_rating, rf_pop, genre_list, feature_columns = train_predictive_models(df)

with st.sidebar:
    st.markdown(
        """
    <div class="sidebar-brand-card">
        <h3>🎬 Cinema Core</h3>
        <p>Analytics & Ticket Booking</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    username = st.session_state.get("username", "User")
    user_role = st.session_state.get("user_role", "Analyst")
    st.markdown(
        f"""
    <div class="user-profile-badge">
        <div class="user-avatar">{username[0].upper()}</div>
        <div style="line-height: 1.2;">
            <div style="font-weight: 700; font-size: 0.9rem; color: #2D2115;">{username.capitalize()}</div>
            <div style="font-size: 0.75rem; color: #7A6555; text-transform: capitalize;">{user_role} Access</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

    st.markdown("---")
    st.info("📍 **Location Target**: Karnataka & Pan-India")

st.markdown(
    """
<div class="hero-banner">
    <div>
        <h1 class="hero-title">🎬 Streamline Analytics & Cinema</h1>
        <div class="hero-tagline">Market Intelligence, Booking Engine & Movie Hub</div>
    </div>
    <div style="font-size: 3.5rem;">🍿</div>
</div>
""",
    unsafe_allow_html=True,
)

tab_stream, tab_book, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📺 Stream Movies",
    "🎟️ Book Movie Tickets",
    "🎯 Executive Insights",
    "🔍 Search & Movie Poster",
    "📊 Genre Analytics",
    "⏱️ Runtime Window",
    "📅 Release Timing",
    "🔮 ML Predictor Engine",
    "💾 Saved History",
])

# -----------------------------------------------------------------------------
# TAB: STREAM MOVIES (NETFLIX STYLE)
# -----------------------------------------------------------------------------
with tab_stream:
    st.subheader("📺 Streamline Watch Hub - Trending & Watchable Movies")
    st.write(
        "Browse featured titles or select a movie to start watching directly."
    )

    unique_movies_df = df.drop_duplicates(subset=["Title"]).reset_index(
        drop=True
    )

    st.markdown(
        '<div class="netflix-section-title">🔥 Trending Now</div>',
        unsafe_allow_html=True,
    )
    trending_movies = unique_movies_df.sort_values(
        by="TMDB_Popularity", ascending=False
    ).head(4)

    t_cols = st.columns(4)
    for idx, (_, movie_row) in enumerate(trending_movies.iterrows()):
        with t_cols[idx]:
            img_url = (
                movie_row["Cast_Photo"]
                if isinstance(movie_row["Cast_Photo"], str)
                and movie_row["Cast_Photo"]
                else "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80"
            )
            st.image(img_url, use_container_width=True)
            st.markdown(f"**{movie_row['Title']}**")
            st.caption(
                f"⭐ {movie_row['IMDb_Score']} | {movie_row['Primary_Language']}"
            )

    st.markdown(
        '<div class="netflix-section-title">🎬 Watch Full Feature / Trailer'
        "</div>",
        unsafe_allow_html=True,
    )

    selected_watch_title = st.selectbox(
        "Select Movie to Watch", options=unique_movies_df["Title"].unique()
    )

    watch_movie_data = unique_movies_df[
        unique_movies_df["Title"] == selected_watch_title
    ].iloc[0]

    st.markdown(f"### Now Playing: {watch_movie_data['Title']}")
    w_col1, w_col2 = st.columns([1, 2])

    with w_col1:
        st.image(watch_movie_data["Cast_Photo"], use_container_width=True)
        st.markdown(
            f"**Genres:** {watch_movie_data['Genres']}\n\n"
            f"**Cast:** {watch_movie_data['Cast']}\n\n"
            f"**Language:** {watch_movie_data['Primary_Language']}\n\n"
            f"**Rating:** ⭐ {watch_movie_data['IMDb_Score']} / 10"
        )

    with w_col2:
        stream_link = watch_movie_data.get("Stream_URL")
        if stream_link:
            st.video(stream_link)
        else:
            st.warning("Video stream unavailable for this title.")

# -----------------------------------------------------------------------------
# TAB: BOOK MOVIE TICKETS
# -----------------------------------------------------------------------------
with tab_book:
    st.subheader("🎟️ Book Movie Tickets - English, Hindi & Kannada Titles")

    col_b1, col_b2, col_b3 = st.columns(3)

    with col_b1:
        city_selected = st.selectbox(
            "Select City",
            options=[
                "Bengaluru",
                "Mysuru",
                "Hubballi-Dharwad",
                "Mangaluru",
                "Mumbai",
                "Delhi NCR",
                "Hyderabad",
            ],
        )

    with col_b2:
        karnataka_theaters_map = {
            "Bengaluru": [
                "PVR Forum Mall (Koramangala)",
                "PVR Superplex (Lulu Mall)",
                "INOX Mantri Square (Malleshwaram)",
                "Cinepolis (Nexus Shantiniketan)",
            ],
            "Mysuru": [
                "DRC Cinemas (BM Habitat Mall)",
                "INOX Centre Point Mall",
            ],
            "Hubballi-Dharwad": [
                "PVR Urban Oasis Mall",
                "Cinepolis Urban Mall",
            ],
            "Mangaluru": ["Bharat Mall Cinepolis", "PVR Forum Fiza Mall"],
            "Mumbai": [
                "PVR ICON Phoenix Palladium",
                "Cinepolis Viviana Mall",
            ],
            "Delhi NCR": [
                "PVR Director's Cut Vasant Kunj",
                "PVR Anupam Saket",
            ],
            "Hyderabad": [
                "AMB Cinemas (Gachibowli)",
                "PVR Forum Sujana Mall",
            ],
        }
        theater_options = karnataka_theaters_map.get(
            city_selected, ["PVR Cinemas Central"]
        )
        theater_selected = st.selectbox(
            "Select Cinema Theater", options=theater_options
        )

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

        trailer_url = selected_movie_row.get(
            "Trailer_URL", "https://www.youtube.com"
        )

        st.markdown(
            f"""
            <div class="image-card">
                <img src="{movie_poster_url}" alt="{selected_movie_row['Title']} Poster">
                <div class="card-content">
                    <h4>
                        {selected_movie_row['Title']} 
                        <a href="{trailer_url}" target="_blank" class="trailer-link-btn">▶️ Trailer</a>
                    </h4>
                    <p><strong>Language:</strong> {selected_movie_row.get('Primary_Language', 'Kannada')}</p>
                    <p><strong>Lead Cast:</strong> {selected_movie_row.get('Cast', 'N/A')}</p>
                    <p><strong>IMDb Rating:</strong> ⭐ {selected_movie_row['IMDb_Score']} / 10</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with b_col2:
        st.markdown("### 💺 Interactive Seat Selection")
        st.markdown(
            '<div class="cinema-screen">SCREEN THIS WAY</div>',
            unsafe_allow_html=True,
        )

        pricing_tiers = {
            "Recliner VIP (Row A-B)": {"rows": ["A", "B"], "price": 600},
            "Prime Gold (Row C-E)": {"rows": ["C", "D", "E"], "price": 350},
            "Classic Silver (Row F-H)": {"rows": ["F", "G", "H"], "price": 200},
        }

        if "selected_seats" not in st.session_state:
            st.session_state.selected_seats = []

        for category, info in pricing_tiers.items():
            st.markdown(f"**{category} - ₹{info['price']}**")
            for row in info["rows"]:
                seat_cols = st.columns(10)
                for seat_num in range(1, 11):
                    seat_id = f"{row}{seat_num}"
                    is_sold = hash(seat_id + movie_selected) % 7 == 0

                    with seat_cols[seat_num - 1]:
                        if is_sold:
                            st.button(
                                f"❌ {seat_id}",
                                key=f"btn_{seat_id}",
                                disabled=True,
                            )
                        else:
                            is_selected = seat_id in st.session_state.selected_seats
                            btn_label = (
                                f"✅ {seat_id}" if is_selected else f"💺 {seat_id}"
                            )
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
            st.markdown(
                f"""
                <div class="payment-summary-box">
                    <p style="font-size: 1.1rem; font-weight: 700;">Selected Movie: {movie_selected}</p>
                    <p><strong>Selected Seats:</strong> {', '.join(st.session_state.selected_seats) if st.session_state.selected_seats else 'None'}</p>
                    <p><strong>City:</strong> {city_selected}</p>
                    <p><strong>Theater:</strong> {theater_selected}</p>
                    <hr style="border-color: #D8C8B8;">
                    <h3 style="color: #1E150C !important; font-weight: 800; margin: 0;">Total Payable: ₹{total_price}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_pay2:
            if st.session_state.selected_seats:
                payment_method = st.radio(
                    "Choose Payment Method",
                    options=[
                        "UPI (GPay / PhonePe / Paytm)",
                        "Credit / Debit Card",
                        "Net Banking (SBI, HDFC, ICICI)",
                    ],
                )

                simulate_failure = st.checkbox("⚠️ Simulate Payment Failure")

                if st.button(
                    "🚀 Pay Now & Confirm Booking", use_container_width=True
                ):
                    seats_str = ", ".join(st.session_state.selected_seats)
                    if simulate_failure:
                        backend.save_booking(
                            movie=movie_selected,
                            city=city_selected,
                            theater=theater_selected,
                            seats=seats_str,
                            amount=total_price,
                            pay_method=payment_method,
                            status="FAILED",
                        )
                        st.error("❌ Payment Failed! Please try again.")
                    else:
                        booking_id = backend.save_booking(
                            movie=movie_selected,
                            city=city_selected,
                            theater=theater_selected,
                            seats=seats_str,
                            amount=total_price,
                            pay_method=payment_method,
                            status="CONFIRMED",
                        )

                        pdf_data = generate_ticket_pdf(
                            booking_id,
                            movie_selected,
                            city_selected,
                            theater_selected,
                            seats_str,
                            total_price,
                        )

                        st.session_state.last_ticket_pdf = pdf_data
                        st.session_state.last_booking_id = booking_id
                        st.session_state.selected_seats = []
                        st.balloons()
                        st.success(f"🎉 Booking #{booking_id} Confirmed!")

                if "last_ticket_pdf" in st.session_state:
                    st.download_button(
                        label="📄 Download Ticket PDF with QR Code",
                        data=st.session_state.last_ticket_pdf,
                        file_name=f"ticket_{st.session_state.last_booking_id}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

# -----------------------------------------------------------------------------
# TAB 1: EXECUTIVE INSIGHTS
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Key Findings & Strategic Recommendations")
    col1, col2 = st.columns(2)

    with col1:
        df_expanded = df.assign(
            Genre_List=df["Genres"].str.split(", ")
        ).explode("Genre_List")
        genre_scores = (
            df_expanded.groupby("Genre_List")["IMDb_Score"]
            .mean()
            .sort_values(ascending=False)
        )
        top_g = genre_scores.index[0]
        top_g_score = round(genre_scores.iloc[0], 2)

        st.metric(
            label="Highest Rated Genre",
            value=f"{top_g}",
            delta=f"{top_g_score} Avg IMDb",
        )
        st.write(
            f"• **Genre Dominance**: Real-time evaluation identifies **{top_g}**"
            " as the strongest performing category."
        )

    with col2:
        season_pop = (
            df.groupby("Season")["TMDB_Popularity"]
            .mean()
            .sort_values(ascending=False)
        )
        top_season = season_pop.index[0]
        top_season_pop = round(season_pop.iloc[0], 2)

        st.metric(
            label="Peak Popularity Season",
            value=f"{top_season}",
            delta=f"{top_season_pop} Pop Index",
        )
        st.write(
            f"• **Seasonal Trends**: **{top_season}** demonstrates maximum"
            " audience engagement."
        )

# -----------------------------------------------------------------------------
# TAB 2: SEARCH & MOVIE POSTER
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("🔍 Movie Catalog Search & Media Viewer")

    search_query = st.text_input(
        "Search Title, Cast, or Genre",
        placeholder="e.g., Kantara, Shah Rukh Khan, Action",
    )

    filtered_df = df.copy()
    if search_query:
        mask = (
            filtered_df["Title"].str.contains(
                search_query, case=False, na=False
            )
            | filtered_df["Cast"].str.contains(
                search_query, case=False, na=False
            )
            | filtered_df["Genres"].str.contains(
                search_query, case=False, na=False
            )
        )
        filtered_df = filtered_df[mask]

    st.write(f"Displaying **{len(filtered_df)}** matching results:")

    cols = st.columns(3)
    for idx, row in filtered_df.reset_index(drop=True).iterrows():
        with cols[idx % 3]:
            img_url = (
                row.get("Cast_Photo")
                if isinstance(row.get("Cast_Photo"), str)
                and row.get("Cast_Photo")
                else "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80"
            )
            trailer = row.get("Trailer_URL", "https://www.youtube.com")

            st.markdown(
                f"""
                <div class="image-card">
                    <img src="{img_url}" alt="{row['Title']}">
                    <div class="card-content">
                        <h4>{row['Title']} <a href="{trailer}" target="_blank" class="trailer-link-btn">▶️ Trailer</a></h4>
                        <p><strong>Genre:</strong> {row['Genres']}</p>
                        <p><strong>Language:</strong> {row['Primary_Language']}</p>
                        <p><strong>Cast:</strong> {row['Cast']}</p>
                        <p><strong>Rating:</strong> ⭐ {row['IMDb_Score']} | <strong>Popularity:</strong> {row['TMDB_Popularity']}</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# -----------------------------------------------------------------------------
# TAB 3: GENRE ANALYTICS
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("📊 Genre Performance Metrics")

    df_genre_exp = df.assign(
        Genre_List=df["Genres"].str.split(", ")
    ).explode("Genre_List")
    genre_metrics = (
        df_genre_exp.groupby("Genre_List")
        .agg(
            Count=("Title", "count"),
            Avg_IMDb=("IMDb_Score", "mean"),
            Avg_Popularity=("TMDB_Popularity", "mean"),
        )
        .reset_index()
    )

    fig_genre = px.bar(
        genre_metrics,
        x="Genre_List",
        y="Avg_IMDb",
        color="Avg_Popularity",
        title="Average IMDb Score by Genre",
        labels={"Genre_List": "Genre", "Avg_IMDb": "Average IMDb Rating"},
        color_continuous_scale="Viridis",
    )
    st.plotly_chart(fig_genre, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: RUNTIME WINDOW
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("⏱️ Duration & Engagement Analytics")

    fig_runtime = px.scatter(
        df,
        x="Runtime_Min",
        y="IMDb_Score",
        size="TMDB_Popularity",
        color="Content_Type",
        hover_data=["Title", "Genres"],
        title="Runtime vs IMDb Score",
        labels={
            "Runtime_Min": "Runtime (Minutes)",
            "IMDb_Score": "IMDb Rating",
        },
    )
    st.plotly_chart(fig_runtime, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: RELEASE TIMING
# -----------------------------------------------------------------------------
with tab5:
    st.subheader("📅 Release Window Analysis")

    monthly_order = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    monthly_stats = (
        df.groupby("Release_Month")
        .agg(
            Releases=("Title", "count"),
            Avg_IMDb=("IMDb_Score", "mean"),
            Avg_Pop=("TMDB_Popularity", "mean"),
        )
        .reindex(monthly_order)
        .reset_index()
    )

    fig_month = px.line(
        monthly_stats,
        x="Release_Month",
        y="Avg_Pop",
        markers=True,
        title="Seasonal Popularity Trend Across Months",
        labels={
            "Release_Month": "Month",
            "Avg_Pop": "Average TMDB Popularity",
        },
    )
    st.plotly_chart(fig_month, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 6: ML PREDICTOR ENGINE
# -----------------------------------------------------------------------------
with tab6:
    st.subheader("🔮 Predictive Machine Learning Engine")

    col_pred1, col_pred2 = st.columns(2)

    with col_pred1:
        selected_genres = st.multiselect(
            "Select Concept Genres",
            options=genre_list,
            default=[genre_list[0]],
        )
        runtime_input = st.slider(
            "Target Runtime (Minutes)", min_value=60, max_value=210, value=135
        )
        season_input = st.selectbox(
            "Release Season", options=["Winter", "Spring", "Summer", "Fall"]
        )
        type_input = st.selectbox(
            "Content Model", options=["Original", "Licensed"]
        )

    with col_pred2:
        if st.button(
            "🚀 Run ML Performance Prediction", use_container_width=True
        ):
            if not selected_genres:
                st.warning("Please select at least one genre.")
            else:
                input_data = pd.DataFrame(
                    0, index=[0], columns=feature_columns
                )
                input_data["Runtime_Min"] = runtime_input

                for g in selected_genres:
                    if g in input_data.columns:
                        input_data[g] = 1

                season_col = f"Season_{season_input}"
                if season_col in input_data.columns:
                    input_data[season_col] = 1

                type_col = f"Content_Type_{type_input}"
                if type_col in input_data.columns:
                    input_data[type_col] = 1

                pred_rating = round(rf_rating.predict(input_data)[0], 2)
                pred_pop = round(rf_pop.predict(input_data)[0], 2)

                st.metric("Predicted IMDb Rating", f"⭐ {pred_rating} / 10")
                st.metric("Predicted TMDB Popularity", f"🔥 {pred_pop}")

                backend.log_prediction(
                    genres=", ".join(selected_genres),
                    runtime=runtime_input,
                    season=season_input,
                    c_type=type_input,
                    imdb=pred_rating,
                    pop=pred_pop,
                )
                st.success("Prediction logged to local database!")

# -----------------------------------------------------------------------------
# TAB 7: SAVED HISTORY
# -----------------------------------------------------------------------------
with tab7:
    st.subheader("💾 Persistent Database Records")

    hist_tab1, hist_tab2 = st.tabs(
        ["🎟️ Ticket Bookings History", "🔮 ML Prediction Log"]
    )

    with hist_tab1:
        booking_history_df = backend.get_booking_history()
        if not booking_history_df.empty:
            st.dataframe(booking_history_df, use_container_width=True)
        else:
            st.info("No bookings recorded in database yet.")

    with hist_tab2:
        pred_history_df = backend.get_prediction_history()
        if not pred_history_df.empty:
            st.dataframe(pred_history_df, use_container_width=True)
        else:
            st.info("No prediction logs saved yet.")
