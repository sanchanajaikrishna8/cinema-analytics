import hashlib
import io
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
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
      # User Auth Table
      cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'analyst'
                )
            """)
      # Catalog Table
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
                    Trailer_URL TEXT DEFAULT 'https://www.youtube.com',
                    Runtime_Min INTEGER NOT NULL,
                    Release_Month TEXT NOT NULL,
                    Season TEXT NOT NULL,
                    Content_Type TEXT NOT NULL,
                    IMDb_Score REAL NOT NULL,
                    TMDB_Popularity REAL NOT NULL
                )
            """)

      # Schema Migration
      cursor.execute("PRAGMA table_info(movies)")
      existing_cols = [col[1] for col in cursor.fetchall()]
      if "Cast_Photo" not in existing_cols:
        cursor.execute(
            "ALTER TABLE movies ADD COLUMN Cast_Photo TEXT DEFAULT"
            " 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&q=80'"
        )
      if "Trailer_URL" not in existing_cols:
        cursor.execute(
            "ALTER TABLE movies ADD COLUMN Trailer_URL TEXT DEFAULT"
            " 'https://www.youtube.com'"
        )

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
            ("analyst", self._hash_password("netflix2026"), "analyst"),
        ]
        cursor.executemany(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?,"
            " ?)",
            default_users,
        )
        conn.commit()

  def authenticate_user(self, username, password):
    hashed = self._hash_password(password)
    with self._get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(
          "SELECT username, role FROM users WHERE username = ? AND"
          " password_hash = ?",
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
      conn.commit()

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
# 3. GLOBAL CUSTOM STYLING & SEAT MAP UI
# -----------------------------------------------------------------------------
st.markdown(
    """
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
        height: 200px;
        object-fit: cover;
    }
    .card-content { padding: 20px; color: #1E150C !important; }
    .card-content h4 {
        margin-top: 0;
        margin-bottom: 8px;
        color: #8C5A3C !important;
        font-size: 1.15rem;
    }

    /* DARKENED PAYMENT SECTION TEXT STYLING */
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
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 4. AUTHENTICATION CONTROLLER
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
# 5. DATA SYNTHESIS PIPELINE (ENGLISH, HINDI, KANNADA MOVIES)
# -----------------------------------------------------------------------------
@st.cache_data
def load_or_generate_dataset(samples=1200):
  real_movies = [
      # Kannada Movies
      {
          "Title": "Kantara",
          "Lang": "Kannada",
          "Genres": "Action, Thriller, Drama",
          "Cast": "Rishab Shetty",
          "Trailer": "https://www.youtube.com/watch?v=8mrVmf239GU",
          "Img": (
              "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=500&q=80"
          ),
      },
      {
          "Title": "KGF: Chapter 2",
          "Lang": "Kannada",
          "Genres": "Action, Crime, Drama",
          "Cast": "Yash",
          "Trailer": "https://www.youtube.com/watch?v=JKa05nyUmuQ",
          "Img": (
              "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=500&q=80"
          ),
      },
      {
          "Title": "777 Charlie",
          "Lang": "Kannada",
          "Genres": "Adventure, Comedy, Drama",
          "Cast": "Rakshit Shetty",
          "Trailer": "https://www.youtube.com/watch?v=RN9-Yl58c-8",
          "Img": (
              "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&q=80"
          ),
      },
      {
          "Title": "Vikrant Rona",
          "Lang": "Kannada",
          "Genres": "Action, Mystery, Thriller",
          "Cast": "Kiccha Sudeep",
          "Trailer": "https://www.youtube.com/watch?v=Ypdu_Wc53s0",
          "Img": (
              "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=500&q=80"
          ),
      },
      # Hindi Movies
      {
          "Title": "Jawan",
          "Lang": "Hindi",
          "Genres": "Action, Thriller",
          "Cast": "Shah Rukh Khan",
          "Trailer": "https://www.youtube.com/watch?v=COv52Qyctws",
          "Img": (
              "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=500&q=80"
          ),
      },
      {
          "Title": "Stree 2",
          "Lang": "Hindi",
          "Genres": "Comedy, Horror",
          "Cast": "Rajkummar Rao, Shraddha Kapoor",
          "Trailer": "https://www.youtube.com/watch?v=KVnheXywIbU",
          "Img": (
              "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=500&q=80"
          ),
      },
      {
          "Title": "Dangal",
          "Lang": "Hindi",
          "Genres": "Biography, Drama, Sport",
          "Cast": "Aamir Khan",
          "Trailer": "https://www.youtube.com/watch?v=x_7YlGv9u1g",
          "Img": (
              "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=500&q=80"
          ),
      },
      {
          "Title": "Pathaan",
          "Lang": "Hindi",
          "Genres": "Action, Adventure, Thriller",
          "Cast": "Shah Rukh Khan, Deepika Padukone",
          "Trailer": "https://www.youtube.com/watch?v=vqu4z34wENw",
          "Img": (
              "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=500&q=80"
          ),
      },
      # English Movies
      {
          "Title": "Oppenheimer",
          "Lang": "English",
          "Genres": "Biography, Drama, History",
          "Cast": "Cillian Murphy",
          "Trailer": "https://www.youtube.com/watch?v=uYPbbksJxIg",
          "Img": (
              "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=500&q=80"
          ),
      },
      {
          "Title": "Avatar: The Way of Water",
          "Lang": "English",
          "Genres": "Action, Adventure, Sci-Fi",
          "Cast": "Sam Worthington",
          "Trailer": "https://www.youtube.com/watch?v=d9MyW72ELq0",
          "Img": (
              "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&q=80"
          ),
      },
      {
          "Title": "Inception",
          "Lang": "English",
          "Genres": "Action, Adventure, Sci-Fi",
          "Cast": "Leonardo DiCaprio",
          "Trailer": "https://www.youtube.com/watch?v=YoHD9XEInc0",
          "Img": (
              "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=500&q=80"
          ),
      },
      {
          "Title": "Interstellar",
          "Lang": "English",
          "Genres": "Adventure, Drama, Sci-Fi",
          "Cast": "Matthew McConaughey",
          "Trailer": "https://www.youtube.com/watch?v=zSWdZVtXT7E",
          "Img": (
              "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=500&q=80"
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
# 6. MACHINE LEARNING MODEL PIPELINE
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

  X = pd.concat([df_copy[["Runtime_Min"]], genre_encoded, cat_features], axis=1)
  y_rating = df_copy["IMDb_Score"]
  y_pop = df_copy["TMDB_Popularity"]

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
  st.info(
      "📍 **Location Target**: Karnataka & Pan-India (English, Hindi, Kannada)"
  )

# Cover Banner
st.markdown(
    """
<div class="hero-banner">
    <div>
        <h1 class="hero-title">🎬 Streamline Analytics & Booking</h1>
        <div class="hero-tagline">Market Intelligence & Ticket Booking Engine</div>
    </div>
    <div style="font-size: 3.5rem;">🍿</div>
</div>
""",
    unsafe_allow_html=True,
)

# Tabs Navigation
tab_book, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎟️ Book Movie Tickets",
    "🎯 Executive Insights",
    "🔍 Search & Cast visual",
    "📊 Genre Analytics",
    "⏱️ Runtime Window",
    "📅 Release Timing",
    "🔮 ML Predictor Engine",
    "💾 Saved History",
])

# -----------------------------------------------------------------------------
# TAB: BOOK MOVIE TICKETS
# -----------------------------------------------------------------------------
with tab_book:
  st.subheader("🎟️ Book Movie Tickets - English, Hindi & Kannada Titles")
  st.markdown(
      "Select your city, theater, movie, seat layout, and execute online"
      " payment."
  )

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
    default_img = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&q=80"
    cast_img_url = selected_movie_row.get("Cast_Photo", default_img)
    trailer_url = selected_movie_row.get(
        "Trailer_URL", "https://www.youtube.com"
    )

    st.markdown(
        f"""
        <div class="image-card">
            <img src="{cast_img_url}" alt="Cast & Movie Image">
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
        """,
        unsafe_allow_html=True,
    )

  with b_col2:
    st.markdown("### 💺 Interactive Seat Selection")
    st.write("Click on seats to add or remove them from your booking.")

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
                  help="Sold Out",
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
        st.markdown(
            "**<span style='color: #1E150C;'>Online Payment Gateway"
            " Options</span>**",
            unsafe_allow_html=True,
        )
        payment_method = st.radio(
            "Choose Payment Method",
            options=[
                "UPI (GPay / PhonePe / Paytm)",
                "Credit / Debit Card",
                "Net Banking (SBI, HDFC, ICICI)",
            ],
        )

        simulate_failure = st.checkbox(
            "⚠️ Simulate Payment Failure (Testing Feature)"
        )

        if st.button(
            "🚀 Pay Now & Confirm Booking", use_container_width=True
        ):
          if simulate_failure:
            backend.save_booking(
                movie=movie_selected,
                city=city_selected,
                theater=theater_selected,
                seats=", ".join(st.session_state.selected_seats),
                amount=total_price,
                pay_method=payment_method,
                status="FAILED",
            )
            st.error(
                "❌ Payment Failed! Transaction could not be processed by your"
                " bank. Please try again or change payment method."
            )
          else:
            backend.save_booking(
                movie=movie_selected,
                city=city_selected,
                theater=theater_selected,
                seats=", ".join(st.session_state.selected_seats),
                amount=total_price,
                pay_method=payment_method,
                status="CONFIRMED",
            )
            st.balloons()
            st.success(
                f"🎉 Booking Confirmed! {len(st.session_state.selected_seats)}"
                f" seats reserved at {theater_selected}."
            )
            st.session_state.selected_seats = []
      else:
        st.info(
            "Select at least one seat from the seating layout above to proceed"
            " to payment."
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

    st.markdown(
        f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80" alt="Cinema">
            <div class="card-content">
                <h4>1. Top Performing Genre: {top_g}</h4>
                <p><strong>{top_g}</strong> leads average ratings at <strong>{genre_scores.iloc[0]:.2f} / 10</strong> in catalog analysis.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  with col2:
    season_perf = (
        df.groupby("Season")["TMDB_Popularity"]
        .mean()
        .sort_values(ascending=False)
    )

    st.markdown(
        f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1518676599625-5832a514d026?auto=format&fit=crop&w=800&q=80" alt="Winter Season">
            <div class="card-content">
                <h4>2. Peak Launch Window: {season_perf.index[0]}</h4>
                <p>Releases during <strong>{season_perf.index[0]}</strong> achieve peak engagement (Avg Popularity: <strong>{season_perf.iloc[0]:.1f}</strong>).</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# TAB 2: SEARCH & CAST VISUALS
# -----------------------------------------------------------------------------
with tab2:
  st.subheader("🔍 Movie Search & Cast Visual Card")

  col_search1, col_search2, col_search3 = st.columns([2, 1, 1])
  with col_search1:
    search_query = st.text_input(
        "Search title or cast", placeholder="Type title or actor name..."
    )
  with col_search2:
    genre_filter = st.multiselect("Filter Genre", options=list(genre_list))
  with col_search3:
    lang_filter = st.multiselect(
        "Filter Language", options=list(df["Primary_Language"].unique())
    )

  filtered_df = df.copy()
  if search_query:
    title_match = filtered_df["Title"].str.contains(
        search_query, case=False, na=False
    )
    cast_match = filtered_df["Cast"].str.contains(
        search_query, case=False, na=False
    )
    filtered_df = filtered_df[title_match | cast_match]
  if genre_filter:
    pattern = "|".join(genre_filter)
    filtered_df = filtered_df[
        filtered_df["Genres"].str.contains(pattern, case=False, na=False)
    ]
  if lang_filter:
    filtered_df = filtered_df[filtered_df["Primary_Language"].isin(lang_filter)]

  if len(filtered_df) > 0:
    selected_title = st.selectbox(
        "Select title:", options=filtered_df["Title"].unique()
    )
    movie_data = filtered_df[filtered_df["Title"] == selected_title].iloc[0]

    st.markdown("---")
    card_col1, card_col2 = st.columns([1, 2])

    with card_col1:
      default_img = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&q=80"
      cast_img_url = movie_data.get("Cast_Photo", default_img)
      t_url = movie_data.get("Trailer_URL", "https://www.youtube.com")

      st.markdown(
          f"""
            <div class="image-card">
                <img src="{cast_img_url}" alt="Cast Photo">
                <div class="card-content">
                    <h4>
                        {movie_data['Title']}
                        <a href="{t_url}" target="_blank" class="trailer-link-btn">▶️ Watch Trailer</a>
                    </h4>
                    <p><strong>Starring:</strong> {movie_data.get('Cast', 'N/A')}</p>
                    <p><strong>Language:</strong> {movie_data.get('Primary_Language', 'Kannada')}</p>
                </div>
            </div>
            """,
          unsafe_allow_html=True,
      )

    with card_col2:
      st.write(f"**Genres:** {movie_data['Genres']}")
      st.write(f"**Runtime:** {movie_data['Runtime_Min']} mins")
      st.write(f"**Season:** {movie_data['Season']}")
      st.write(f"**Type:** {movie_data['Content_Type']}")
      st.metric("IMDb Rating", f"⭐ {movie_data['IMDb_Score']} / 10")
      st.metric("TMDB Popularity", f"🔥 {movie_data['TMDB_Popularity']}")
  else:
    st.warning("No movies found matching the search criteria.")

# -----------------------------------------------------------------------------
# TAB 3: GENRE ANALYTICS (FIXED COLOR SCALE ERROR)
# -----------------------------------------------------------------------------
with tab3:
  st.subheader("📊 Genre Performance & Volume Analysis")

  df_expanded = df.assign(
      Genre_List=df["Genres"].str.split(", ")
  ).explode("Genre_List")
  genre_summary = (
      df_expanded.groupby("Genre_List")
      .agg(
          Average_IMDb=("IMDb_Score", "mean"),
          Average_Popularity=("TMDB_Popularity", "mean"),
          Total_Titles=("Title", "count"),
      )
      .reset_index()
  )

  c1, c2 = st.columns(2)
  with c1:
    fig_g1 = px.bar(
        genre_summary.sort_values(by="Average_IMDb", ascending=True),
        x="Average_IMDb",
        y="Genre_List",
        orientation="h",
        title="Average IMDb Rating by Genre",
        color="Average_IMDb",
        color_continuous_scale="Cividis",
    )
    fig_g1.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_g1, use_container_width=True)

  with c2:
    fig_g2 = px.pie(
        genre_summary,
        names="Genre_List",
        values="Total_Titles",
        title="Genre Share in Catalog",
        color_discrete_sequence=px.colors.sequential.Darkmint,
    )
    fig_g2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_g2, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: RUNTIME WINDOW
# -----------------------------------------------------------------------------
with tab4:
  st.subheader("⏱️ Runtime Distribution vs User Engagement")

  fig_rt = px.scatter(
      df,
      x="Runtime_Min",
      y="IMDb_Score",
      color="Content_Type",
      size="TMDB_Popularity",
      hover_data=["Title", "Genres"],
      title="Runtime (Minutes) vs IMDb Score",
      color_discrete_sequence=["#8C5A3C", "#2D2115"],
  )
  fig_rt.update_layout(
      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
  )
  st.plotly_chart(fig_rt, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: RELEASE TIMING
# -----------------------------------------------------------------------------
with tab5:
  st.subheader("📅 Seasonal Launch & Release Month Analysis")

  month_order = [
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
  monthly_data = (
      df.groupby("Release_Month")
      .agg(
          Avg_Popularity=("TMDB_Popularity", "mean"),
          Avg_IMDb=("IMDb_Score", "mean"),
      )
      .reindex(month_order)
      .reset_index()
  )

  fig_rel = px.line(
      monthly_data,
      x="Release_Month",
      y="Avg_Popularity",
      markers=True,
      title="Popularity Trajectory Across Release Months",
      line_shape="spline",
      color_discrete_sequence=["#8C5A3C"],
  )
  fig_rel.update_layout(
      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
  )
  st.plotly_chart(fig_rel, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 6: ML PREDICTOR ENGINE
# -----------------------------------------------------------------------------
with tab6:
  st.subheader("🔮 Predictive Intelligence Engine")
  st.markdown(
      "Simulate film metrics and predict IMDb rating & TMDB popularity."
  )

  col_m1, col_m2 = st.columns(2)
  with col_m1:
    selected_genres_input = st.multiselect(
        "Select Genres:", options=list(genre_list), default=[genre_list[0]]
    )
    runtime_input = st.slider("Runtime (Minutes):", 60, 210, 135)

  with col_m2:
    season_input = st.selectbox(
        "Release Season:", ["Winter", "Spring", "Summer", "Fall"]
    )
    type_input = st.selectbox("Content Source:", ["Original", "Licensed"])

  if st.button("✨ Execute AI Forecast", use_container_width=True):
    if not selected_genres_input:
      st.warning("Please select at least one genre.")
    else:
      input_dict = {col: 0 for col in feature_columns}
      input_dict["Runtime_Min"] = runtime_input

      for g in selected_genres_input:
        if g in input_dict:
          input_dict[g] = 1

      season_col = f"Season_{season_input}"
      if season_col in input_dict:
        input_dict[season_col] = 1

      type_col = f"Content_Type_{type_input}"
      if type_col in input_dict:
        input_dict[type_col] = 1

      input_df = pd.DataFrame([input_dict])

      pred_rating = rf_rating.predict(input_df)[0]
      pred_pop = rf_pop.predict(input_df)[0]

      backend.log_prediction(
          selected_genres_input,
          runtime_input,
          season_input,
          type_input,
          round(pred_rating, 2),
          round(pred_pop, 2),
      )

      st.markdown("---")
      res1, res2 = st.columns(2)
      res1.metric("Forecasted IMDb Rating", f"⭐ {pred_rating:.2f} / 10")
      res2.metric("Forecasted TMDB Popularity", f"🔥 {pred_pop:.2f}")

# -----------------------------------------------------------------------------
# TAB 7: SAVED HISTORY
# -----------------------------------------------------------------------------
with tab7:
  st.subheader("💾 Audit & Activity History")

  hist_tab1, hist_tab2 = st.tabs(
      ["🎟️ Booking Transactions", "🔮 Prediction Records"]
  )

  with hist_tab1:
    booking_df = backend.get_booking_history()
    if not booking_df.empty:
      st.dataframe(booking_df, use_container_width=True)
    else:
      st.info("No transaction history recorded yet.")

  with hist_tab2:
    history_df = backend.get_prediction_history()
    if not history_df.empty:
      st.dataframe(history_df, use_container_width=True)
    else:
      st.info("No saved predictions logged yet.")
