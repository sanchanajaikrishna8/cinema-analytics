import hashlib
import io
import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MultiLabelBinarizer
import sqlite3
import streamlit as st

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Streamline Analytics - Cinema Intelligence",
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
      # Catalog Table (Updated with Cast, Languages, Theaters)
      cursor.execute("""
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Title TEXT NOT NULL,
                    Genres TEXT NOT NULL,
                    Cast TEXT DEFAULT 'N/A',
                    Primary_Language TEXT DEFAULT 'English',
                    Available_Languages TEXT DEFAULT 'English',
                    Theaters_Available TEXT DEFAULT 'N/A',
                    Runtime_Min INTEGER NOT NULL,
                    Release_Month TEXT NOT NULL,
                    Season TEXT NOT NULL,
                    Content_Type TEXT NOT NULL,
                    IMDb_Score REAL NOT NULL,
                    TMDB_Popularity REAL NOT NULL
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
      # Remove database ID for analysis
      if "id" in df.columns:
        df = df.drop(columns=["id"])
      return df

  def save_catalog_data(self, df):
    with self._get_connection() as conn:
      df.to_sql("movies", conn, if_exists="replace", index=False)

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


backend = AnalyticsBackend()

# -----------------------------------------------------------------------------
# 3. GLOBAL CUSTOM STYLING (Theming, Login, Side, Cover)
# -----------------------------------------------------------------------------
st.markdown(
    """
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
    
    /* Sidebar Brand & Header Card Design */
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
    
    /* User Profile Badge in Sidebar */
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
    
    /* Sidebar Styled Section Headers */
    .sidebar-section-title {
        color: #8C5A3C;
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 20px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 6px;
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
    .brand-logo-container {
        text-align: center;
        margin-bottom: 15px;
    }
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
        letter-spacing: -0.5px;
    }
    .login-tagline {
        color: #8C5A3C;
        font-size: 0.95rem;
        font-weight: 700;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .login-subtitle {
        color: #7A6555;
        font-size: 0.9rem;
        text-align: center;
        margin-bottom: 24px;
    }
    .credential-badge {
        background-color: #FAF7F2;
        border: 1px dashed #D4C3B3;
        border-radius: 10px;
        padding: 12px;
        margin-top: 24px;
        font-size: 0.82rem;
        color: #5C4A3E;
        text-align: center;
        line-height: 1.4;
    }

    /* Cover Hero Header Banner */
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
        letter-spacing: -1px;
    }
    .hero-tagline {
        color: #E2D5C3 !important;
        margin-top: 6px;
        font-size: 1.1rem;
        font-weight: 500;
    }
    .hero-logo {
        font-size: 3.5rem;
        background: rgba(255, 255, 255, 0.1);
        padding: 15px 22px;
        border-radius: 16px;
        backdrop-filter: blur(5px);
    }

    /* GENERAL DASHBOARD UI ELEMENT STYLES */
    h1, h2, h3, h4, h5, h6 {
        color: #2D2115 !important;
        font-weight: 700 !important;
        letter-spacing: -0.4px;
    }
    
    /* Tab Styling & Visibility Fix */
    button[data-baseweb="tab"] {
        color: #4A3B2C !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 10px 20px !important;
    }
    button[aria-selected="true"] {
        color: #8C5A3C !important;
        border-bottom: 3px solid #8C5A3C !important;
        background-color: rgba(140, 90, 60, 0.05) !important;
    }

    /* Executive Image Cards */
    .image-card {
        background-color: #FFFFFF;
        border-radius: 14px;
        border: 1px solid #EAE0D5;
        box-shadow: 0px 4px 14px rgba(0, 0, 0, 0.04);
        overflow: hidden;
        margin-bottom: 24px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .image-card:hover {
        transform: translateY(-2px);
        box-shadow: 0px 6px 20px rgba(140, 90, 60, 0.1);
    }
    .image-card img {
        width: 100%;
        height: 140px;
        object-fit: cover;
    }
    .card-content {
        padding: 20px;
    }
    .card-content h4 {
        margin-top: 0;
        margin-bottom: 8px;
        color: #8C5A3C !important;
        font-size: 1.15rem;
    }
    .card-content p {
        font-size: 1.02rem;
        margin-bottom: 6px;
        color: #2D2115 !important;
        line-height: 1.5;
    }

    /* Metrics Card Overhaul */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #EAE0D5;
        box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.03);
    }
    div[data-testid="stMetricLabel"] {
        color: #5C4A3E !important;
        font-weight: 600;
        font-size: 0.95rem;
    }
    div[data-testid="stMetricValue"] {
        color: #8C5A3C !important;
        font-weight: 800;
        font-size: 2rem !important;
    }

    /* Inputs, Selectboxes, and Labels Dark & Clear */
    label, div[data-baseweb="select"] span {
        color: #1E150C !important;
        font-weight: 600 !important;
    }

    /* Action Buttons */
    .stButton>button {
        background-color: #8C5A3C !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 12px 28px !important;
        box-shadow: 0px 4px 10px rgba(140, 90, 60, 0.25);
        transition: all 0.2s ease-in-out;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #6F452C !important;
        transform: translateY(-1px);
        box-shadow: 0px 6px 14px rgba(140, 90, 60, 0.35);
    }
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 4. AUTHENTICATION CONTROLLER (Login & Cover)
# -----------------------------------------------------------------------------
if 'authenticated' not in st.session_state:
  st.session_state.authenticated = False


def login_page():
  st.markdown('<br><br>', unsafe_allow_html=True)
  col1, col2, col3 = st.columns([1, 1.2, 1])

  with col2:
    st.markdown(
        """
        <div class="login-card">
            <div class="brand-logo-container">
                <div class="movie-logo-icon">🎬</div>
            </div>
            <h2 class="login-title">Streamline Analytics</h2>
            <div class="login-tagline">Decoding Box Office & Streaming DNA</div>
            <p class="login-subtitle">Enter credentials to access strategic market insights</p>
        """,
        unsafe_allow_html=True,
    )

    username = st.text_input(
        'Username', key='login_user', placeholder='Enter your username'
    )
    password = st.text_input(
        'Password', type='password', key='login_pass', placeholder='••••••••'
    )

    st.markdown(
        "<div style='margin-top: 16px;'></div>", unsafe_allow_html=True
    )
    if st.button('Sign In to Portal', use_container_width=True):
      user_info = backend.authenticate_user(username, password)
      if user_info:
        st.session_state.authenticated = True
        st.session_state.username = user_info[0]
        st.session_state.user_role = user_info[1]
        st.rerun()
      else:
        st.error('Invalid username or password.')

    st.markdown(
        """
            <div class="credential-badge">
                💡 <strong>Demo Access Credentials</strong><br>
                User: <code style="color: #8C5A3C;">admin</code> &nbsp;|&nbsp; Pass: <code style="color: #8C5A3C;">password123</code>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if not st.session_state.authenticated:
  login_page()
  st.stop()


# -----------------------------------------------------------------------------
# 5. DATA SYNTHESIS & BACKEND SEEDING PIPELINE
# -----------------------------------------------------------------------------
@st.cache_data
def load_or_generate_dataset(samples=1200):
  """Loads data from backend DB. If DB is empty, seeds it with synthetic data."""
  existing_df = backend.get_catalog_data()

  if not existing_df.empty:
    return existing_df

  # --- Seeding Logic (only runs once if DB is fresh) ---
  np.random.seed(42)
  genres_list = [
      'Drama',
      'Comedy',
      'Action',
      'Documentary',
      'Animation',
      'Thriller',
      'Sci-Fi',
      'Romance',
  ]
  months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
  ]
  seasons_map = {
      'Jan': 'Winter',
      'Feb': 'Winter',
      'Mar': 'Spring',
      'Apr': 'Spring',
      'May': 'Spring',
      'Jun': 'Summer',
      'Jul': 'Summer',
      'Aug': 'Summer',
      'Sep': 'Fall',
      'Oct': 'Fall',
      'Nov': 'Fall',
      'Dec': 'Winter',
  }

  sample_titles = [
      'The Dark Horizon',
      'Apex Predator',
      'Shadows of Yesterday',
      'Midnight Protocol',
      'Echoes of Eternity',
      'Quantum Leap',
      'Neon Nights',
      'Crimson Peak Rising',
  ]

  actors_pool = [
      'Keanu Reeves',
      'Zendaya',
      'Oscar Isaac',
      'Cate Blanchett',
      'Joaquin Phoenix',
      'Ryan Reynolds',
      'Emma Stone',
      'Hiroyuki Sanada',
  ]
  languages_pool = [
      'English',
      'Spanish',
      'French',
      'Japanese',
      'German',
      'Italian',
      'Portuguese',
  ]
  theaters_pool = [
      'AMC Lincoln Square',
      'Regal LA Live',
      'BFI IMAX London',
      'Cineworld Leicester Square',
      'TOHO Cinemas Shinjuku',
      'AMC Empire 25',
  ]

  data = []
  for idx in range(samples):
    title_name = (
        sample_titles[idx]
        if idx < len(sample_titles)
        else f'Film Project {idx + 1}'
    )
    g_count = np.random.choice([1, 2, 3], p=[0.5, 0.4, 0.1])
    g_assigned = list(
        np.random.choice(genres_list, size=g_count, replace=False)
    )

    runtime = int(np.random.normal(105, 25))
    runtime = max(45, min(210, runtime))

    release_m = np.random.choice(months)
    is_original = np.random.choice(['Original', 'Licensed'], p=[0.38, 0.62])

    base_rating = 6.2
    if 'Documentary' in g_assigned:
      base_rating += 0.9
    if 'Animation' in g_assigned:
      base_rating += 0.5

    imdb_score = round(np.clip(np.random.normal(base_rating, 0.7), 1.0, 10.0), 1)
    tmdb_popularity = round(
        np.random.exponential(scale=35.0)
        + (10 if is_original == 'Original' else 0),
        2,
    )

    cast_selection = ', '.join(
        np.random.choice(actors_pool, size=2, replace=False)
    )
    primary_lang = np.random.choice(
        languages_pool, p=[0.6, 0.1, 0.1, 0.05, 0.05, 0.05, 0.05]
    )
    avail_langs = (
        f'{primary_lang}, '
        + ', '.join(np.random.choice(languages_pool, size=2, replace=False))
    )
    theaters = ', '.join(np.random.choice(theaters_pool, size=2, replace=False))

    data.append({
        'Title': title_name,
        'Genres': ', '.join(g_assigned),
        'Cast': cast_selection,
        'Primary_Language': primary_lang,
        'Available_Languages': avail_langs,
        'Theaters_Available': theaters,
        'Runtime_Min': runtime,
        'Release_Month': release_m,
        'Season': seasons_map[release_m],
        'Content_Type': is_original,
        'IMDb_Score': imdb_score,
        'TMDB_Popularity': tmdb_popularity,
    })

  generated_df = pd.DataFrame(data)
  backend.save_catalog_data(generated_df)  # Commit to backend
  return generated_df


# -----------------------------------------------------------------------------
# 6. MACHINE LEARNING MODEL PIPELINE
# -----------------------------------------------------------------------------
@st.cache_resource
def train_predictive_models(df):
  """Trains Random Forest models based on the current catalog data."""
  if df.empty:
    return None, None, [], []

  df_copy = df.copy()

  # Preprocess Genres (Multi-label encoding)
  genre_series = df_copy['Genres'].apply(
      lambda x: [g.strip() for g in x.split(',')]
  )
  mlb = MultiLabelBinarizer()
  genre_encoded = pd.DataFrame(
      mlb.fit_transform(genre_series),
      columns=mlb.classes_,
      index=df_copy.index,
  )

  # One-hot encode categorical fields
  cat_features = pd.get_dummies(
      df_copy[['Season', 'Content_Type']], drop_first=False
  )

  # Feature matrix X and targets Y
  X = pd.concat([df_copy[['Runtime_Min']], genre_encoded, cat_features], axis=1)
  y_rating = df_copy['IMDb_Score']
  y_pop = df_copy['TMDB_Popularity']

  # Train Rating Predictor
  rf_rating = RandomForestRegressor(n_estimators=100, random_state=42)
  rf_rating.fit(X, y_rating)

  # Train Popularity Predictor
  rf_pop = RandomForestRegressor(n_estimators=100, random_state=42)
  rf_pop.fit(X, y_pop)

  return rf_rating, rf_pop, mlb.classes_, X.columns


# -----------------------------------------------------------------------------
# 7. MAIN DASHBOARD SIDEBAR & UI
# -----------------------------------------------------------------------------

# --- ENHANCED SIDEBAR ---
with st.sidebar:
  # Top Brand Header Card
  st.markdown(
      """
    <div class="sidebar-brand-card">
        <h3>🎬 Cinema Core</h3>
        <p>Control Panel & Data Suite</p>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # Active User Profile Badge
  username = st.session_state.get('username', 'User')
  user_role = st.session_state.get('user_role', 'Analyst')
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

  if st.button('🚪 Sign Out', use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()

  st.markdown('<br>', unsafe_allow_html=True)

  # Section 1: Data Management Design Card
  st.markdown(
      """
    <div class="sidebar-section-title">📁 Data Operations</div>
    """,
      unsafe_allow_html=True,
  )

  uploaded_file = st.file_uploader(
      'Upload custom CSV dataset',
      type=['csv'],
      help='Overwrite backend DB with new movie catalog.',
  )
  if uploaded_file is not None:
    try:
      # Read uploaded CSV
      new_df = pd.read_csv(uploaded_file)
      # Validate basic schema
      required_cols = {
          'Title',
          'Genres',
          'Runtime_Min',
          'Season',
          'Content_Type',
          'IMDb_Score',
          'TMDB_Popularity',
      }
      if required_cols.issubset(new_df.columns):
        # Save to Backend Database
        backend.save_catalog_data(new_df)
        st.success('Database synced with CSV!')
        # Clear cache to force reload and model retrain
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
      else:
        st.error(f"Invalid CSV. Must contain: {', '.join(required_cols)}")
    except Exception as e:
      st.error('Error loading CSV file.')

  st.markdown('---')

  # Section 2: Platform Info Card
  st.markdown(
      """
    <div class="sidebar-section-title">📌 System Status</div>
    """,
      unsafe_allow_html=True,
  )

  st.info("""
    **Engine:** Active  
    **Database:** SQLite Persistence  
    **ML Pipeline:** Random Forest
    """)

# --- MAIN INTERFACE ---

# Load Data from Backend
df = load_or_generate_dataset()
# Train/Load Models based on current data
rf_rating, rf_pop, genre_list, feature_columns = train_predictive_models(df)

# Enhanced Cover Page Banner Header
st.markdown(
    """
<div class="hero-banner">
    <div>
        <h1 class="hero-title">🎬 Streamline Analytics</h1>
        <div class="hero-tagline">Predictive Market Intelligence & Executive Decision Support</div>
    </div>
    <div class="hero-logo">🍿</div>
</div>
""",
    unsafe_allow_html=True,
)

if df.empty:
  st.warning(
      'The database is currently empty. Please upload a CSV dataset in the'
      ' sidebar to populate the catalog and train models.'
  )
  st.stop()

# Navigation Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    '🎯 Executive Insights',
    '🔍 Search & Explore',
    '📊 Genre Analytics',
    '⏱️ Runtime Window',
    '📅 Release Timing',
    '🔮 ML Predictor Engine',
    '💾 Saved History',
])

# -----------------------------------------------------------------------------
# TAB 1: EXECUTIVE INSIGHTS
# -----------------------------------------------------------------------------
with tab1:
  st.subheader('Key Findings & Strategic Recommendations')
  st.markdown('<br>', unsafe_allow_html=True)

  col1, col2 = st.columns(2)

  with col1:
    # Card 1: Top Genre
    df_expanded = df.assign(
        Genre_List=df['Genres'].str.split(', ')
    ).explode('Genre_List')
    genre_scores = df_expanded.groupby('Genre_List')['IMDb_Score'].mean().sort_values(
        ascending=False
    )
    top_g = genre_scores.index[0]

    st.markdown(
        f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80" alt="Cinema">
            <div class="card-content">
                <h4>1. Top Performing Genre: {top_g}</h4>
                <p><strong>{top_g}</strong> leads average ratings at <strong>{genre_scores.iloc[0]:.2f} / 10</strong>. Targeted niche titles consistently command superior satisfaction compared to saturated mass-market genres.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Card 2: Runtime
    df['Runtime_Bin'] = pd.cut(
        df['Runtime_Min'],
        bins=[0, 80, 100, 120, 140, 240],
        labels=[
            '<80 min',
            '80-100 min',
            '100-120 min',
            '120-140 min',
            '140+ min',
        ],
    )
    best_bin = (
        df.groupby('Runtime_Bin', observed=False)['IMDb_Score'].mean().idxmax()
    )

    st.markdown(
        f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?auto=format&fit=crop&w=800&q=80" alt="Film Reel">
            <div class="card-content">
                <h4>2. Optimal Duration Window: {best_bin}</h4>
                <p>Titles in the <strong>{best_bin}</strong> duration bracket exhibit optimal audience retention, delivering high completion rates without risking viewer fatigue.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  with col2:
    # Card 3: Seasonality
    season_perf = df.groupby('Season')['TMDB_Popularity'].mean().sort_values(
        ascending=False
    )

    st.markdown(
        f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1518676599625-5832a514d026?auto=format&fit=crop&w=800&q=80" alt="Winter Season">
            <div class="card-content">
                <h4>3. Peak Launch Window: {season_perf.index[0]}</h4>
                <p>Releases during <strong>{season_perf.index[0]}</strong> achieve peak engagement (Avg Popularity: <strong>{season_perf.iloc[0]:.1f}</strong>), leveraging holiday viewership spikes.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Card 4: Catalog Mix
    lic_counts = df['Content_Type'].value_counts(normalize=True) * 100
    orig_pct = lic_counts.get('Original', 0)
    lic_pct = lic_counts.get('Licensed', 0)

    st.markdown(
        f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?auto=format&fit=crop&w=800&q=80" alt="Streaming">
            <div class="card-content">
                <h4>4. Catalog Composition Ratio</h4>
                <p>Portfolio consists of <strong>{lic_pct:.1f}% Licensed</strong> and <strong>{orig_pct:.1f}% Originals</strong>. Originals demonstrate 2.4x higher long-tail organic engagement.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# TAB 2: SEARCH & EXPLORE MENU
# -----------------------------------------------------------------------------
with tab2:
  st.subheader('🔍 Movie Search & Catalog Explorer')
  st.markdown('Search existing titles or filter by genre and language:')

  col_search1, col_search2, col_search3 = st.columns([2, 1, 1])
  with col_search1:
    search_query = st.text_input(
        'Search movie title or cast',
        placeholder='Type a movie title or actor (e.g. Horizon, Keanu)...',
    )
  with col_search2:
    genre_filter = st.multiselect('Filter by Genre', options=list(genre_list))
  with col_search3:
    lang_filter = st.multiselect(
        'Filter by Language',
        options=(
            list(df['Primary_Language'].unique())
            if 'Primary_Language' in df.columns
            else []
        ),
    )

  filtered_df = df.copy()
  if search_query:
    title_match = filtered_df['Title'].str.contains(
        search_query, case=False, na=False
    )
    cast_match = (
        filtered_df['Cast'].str.contains(search_query, case=False, na=False)
        if 'Cast' in filtered_df.columns
        else False
    )
    filtered_df = filtered_df[title_match | cast_match]
  if genre_filter:
    pattern = '|'.join(genre_filter)
    filtered_df = filtered_df[
        filtered_df['Genres'].str.contains(pattern, case=False, na=False)
    ]
  if lang_filter and 'Primary_Language' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Primary_Language'].isin(lang_filter)]

  st.markdown(f'**Found {len(filtered_df)} titles matching criteria**')

  if len(filtered_df) > 0:
    selected_title = st.selectbox(
        'Select a film to view detailed breakdown:',
        options=filtered_df['Title'].values,
    )
    movie_data = filtered_df[filtered_df['Title'] == selected_title].iloc[0]

    st.markdown('---')
    card_col1, card_col2 = st.columns([1, 2])

    with card_col1:
      st.markdown(
          f"""
            <div class="image-card">
                <img src="https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&w=800&q=80" alt="Movie Poster">
                <div class="card-content">
                    <h4>{movie_data['Title']}</h4>
                    <p><strong>Genres:</strong> {movie_data['Genres']}</p>
                    <p><strong>🎭 Cast:</strong> {movie_data.get('Cast', 'N/A')}</p>
                    <p><strong>🗣️ Primary Language:</strong> {movie_data.get('Primary_Language', 'N/A')}</p>
                    <p><strong>🌍 Available Languages:</strong> {movie_data.get('Available_Languages', 'N/A')}</p>
                    <p><strong>🏛️ Theaters Available:</strong> {movie_data.get('Theaters_Available', 'N/A')}</p>
                    <p><strong>Runtime:</strong> {movie_data['Runtime_Min']} mins</p>
                    <p><strong>Type:</strong> {movie_data['Content_Type']}</p>
                    <p><strong>Release Window:</strong> {movie_data['Release_Month']} ({movie_data['Season']})</p>
                </div>
            </div>
            """,
          unsafe_allow_html=True,
      )

    with card_col2:
      st.markdown('### Title Analytics')
      m1, m2 = st.columns(2)
      with m1:
        st.metric(
            'IMDb Rating',
            f"{movie_data['IMDb_Score']} / 10",
            delta=(
                f"{round(movie_data['IMDb_Score'] - df['IMDb_Score'].mean(), 2)} vs Avg"
            ),
        )
      with m2:
        st.metric(
            'TMDB Popularity Score',
            f"{movie_data['TMDB_Popularity']}",
            delta=(
                f"{round(movie_data['TMDB_Popularity'] - df['TMDB_Popularity'].mean(), 2)} vs Avg"
            ),
        )

      st.markdown('**Catalog Data Snapshot**')
      display_cols = [
          c
          for c in [
              'Title',
              'Genres',
              'Cast',
              'Primary_Language',
              'Theaters_Available',
              'Runtime_Min',
              'Season',
              'Content_Type',
              'IMDb_Score',
              'TMDB_Popularity',
          ]
          if c in filtered_df.columns
      ]
      st.dataframe(filtered_df[display_cols].head(10), use_container_width=True)
  else:
    st.warning(
        'No titles match your search criteria. Try adjusting your query or'
        ' filters.'
    )

# -----------------------------------------------------------------------------
# TAB 3: GENRE PERFORMANCE
# -----------------------------------------------------------------------------
with tab3:
  st.subheader('Genre Ratings & Popularity Breakdown')

  df_expanded = df.assign(
      Genre_List=df['Genres'].str.split(', ')
  ).explode('Genre_List')
  g_summary = (
      df_expanded.groupby('Genre_List')
      .agg(
          Avg_Rating=('IMDb_Score', 'mean'),
          Avg_Popularity=('TMDB_Popularity', 'mean'),
          Count=('Title', 'count'),
      )
      .reset_index()
      .sort_values(by='Avg_Rating', ascending=True)
  )

  fig_g = px.bar(
      g_summary,
      x='Avg_Rating',
      y='Genre_List',
      orientation='h',
      text_auto='.2f',
      color='Avg_Rating',
      color_continuous_scale=['#E2D5C3', '#8C5A3C'],
  )
  fig_g.update_layout(
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      font=dict(color='#1E150C', size=13),
      xaxis_title='Average IMDb Score',
      yaxis_title='Genre',
      coloraxis_showscale=False,
      margin=dict(l=20, r=20, t=20, b=20),
  )

  fig_pop = px.scatter(
      g_summary,
      x='Avg_Rating',
      y='Avg_Popularity',
      size='Count',
      text='Genre_List',
      color='Avg_Popularity',
      color_continuous_scale=['#E2D5C3', '#8C5A3C'],
      size_max=40,
  )
  fig_pop.update_traces(textposition='top center')
  fig_pop.update_layout(
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      font=dict(color='#1E150C', size=13),
      xaxis_title='Average IMDb Rating',
      yaxis_title='Average TMDB Popularity',
      coloraxis_showscale=False,
      margin=dict(l=20, r=20, t=20, b=20),
  )

  col1, col2 = st.columns(2)
  with col1:
    st.markdown('#### Average IMDb Score by Genre')
    st.plotly_chart(fig_g, use_container_width=True)
  with col2:
    st.markdown('#### Genre Rating vs. Popularity Distribution')
    st.plotly_chart(fig_pop, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: RUNTIME WINDOW ANALYSIS
# -----------------------------------------------------------------------------
with tab4:
  st.subheader('⏱️ Runtime Window Impact Analysis')

  fig_run = px.box(
      df,
      x='Runtime_Bin',
      y='IMDb_Score',
      color='Runtime_Bin',
      color_discrete_sequence=[
          '#E2D5C3',
          '#C5A880',
          '#8C5A3C',
          '#6F452C',
          '#4A3B2C',
      ],
  )
  fig_run.update_layout(
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      font=dict(color='#1E150C', size=13),
      xaxis_title='Runtime Window',
      yaxis_title='IMDb Score',
      showlegend=False,
      margin=dict(l=20, r=20, t=20, b=20),
  )

  fig_scatter_run = px.scatter(
      df,
      x='Runtime_Min',
      y='IMDb_Score',
      color='Content_Type',
      trendline='ols',
      color_discrete_map={'Original': '#8C5A3C', 'Licensed': '#4A3B2C'},
      opacity=0.6,
  )
  fig_scatter_run.update_layout(
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      font=dict(color='#1E150C', size=13),
      xaxis_title='Exact Runtime (Minutes)',
      yaxis_title='IMDb Score',
      margin=dict(l=20, r=20, t=20, b=20),
  )

  col1, col2 = st.columns(2)
  with col1:
    st.markdown('#### IMDb Score Variance across Runtime Brackets')
    st.plotly_chart(fig_run, use_container_width=True)
  with col2:
    st.markdown('#### Exact Duration vs. Rating Trend')
    st.plotly_chart(fig_scatter_run, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: RELEASE TIMING & SEASONALITY
# -----------------------------------------------------------------------------
with tab5:
  st.subheader('📅 Release Timing & Seasonal Performance')

  season_order = ['Spring', 'Summer', 'Fall', 'Winter']
  df_season = (
      df.groupby('Season')
      .agg(Avg_Popularity=('TMDB_Popularity', 'mean'), Avg_Rating=('IMDb_Score', 'mean'))
      .reindex(season_order)
      .reset_index()
  )

  fig_s_pop = px.bar(
      df_season,
      x='Season',
      y='Avg_Popularity',
      color='Season',
      color_discrete_sequence=[
          '#E2D5C3',
          '#C5A880',
          '#8C5A3C',
          '#4A3B2C',
      ],
      text_auto='.1f',
  )
  fig_s_pop.update_layout(
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      font=dict(color='#1E150C', size=13),
      xaxis_title='Season',
      yaxis_title='Average Popularity',
      showlegend=False,
      margin=dict(l=20, r=20, t=20, b=20),
  )

  month_order = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
  ]
  df_month = (
      df.groupby('Release_Month')
      .agg(Avg_Popularity=('TMDB_Popularity', 'mean'))
      .reindex(month_order)
      .reset_index()
  )

  fig_m_pop = px.line(
      df_month,
      x='Release_Month',
      y='Avg_Popularity',
      markers=True,
      line_shape='spline',
  )
  fig_m_pop.update_traces(line_color='#8C5A3C', line_width=3, marker_size=8)
  fig_m_pop.update_layout(
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      font=dict(color='#1E150C', size=13),
      xaxis_title='Release Month',
      yaxis_title='Average TMDB Popularity',
      margin=dict(l=20, r=20, t=20, b=20),
  )

  col1, col2 = st.columns(2)
  with col1:
    st.markdown('#### Seasonal Audience Engagement')
    st.plotly_chart(fig_s_pop, use_container_width=True)
  with col2:
    st.markdown('#### Monthly Popularity Curve')
    st.plotly_chart(fig_m_pop, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 6: ML PREDICTOR ENGINE
# -----------------------------------------------------------------------------
with tab6:
  st.subheader('🔮 Machine Learning Performance Predictor')
  st.markdown(
      'Adjust proposed project variables below to forecast projected IMDb'
      ' rating and TMDB popularity scores using the Random Forest backend'
      ' engine.'
  )

  col_in1, col_in2 = st.columns(2)

  with col_in1:
    p_genres = st.multiselect(
        'Select Target Genres',
        options=list(genre_list),
        default=['Drama', 'Action'],
    )
    p_runtime = st.slider(
        'Target Runtime (minutes)',
        min_value=45,
        max_value=210,
        value=110,
        step=5,
    )

  with col_in2:
    p_season = st.selectbox(
        'Planned Release Season', options=['Spring', 'Summer', 'Fall', 'Winter']
    )
    p_type = st.radio(
        'Catalog Strategy',
        options=['Original', 'Licensed'],
        horizontal=True,
    )

  st.markdown('<br>', unsafe_allow_html=True)

  if st.button('🚀 Execute Predictive Model', use_container_width=True):
    if not p_genres:
      st.error('Please select at least one genre.')
    else:
      # Construct single row feature vector matching training feature columns
      input_data = dict.fromkeys(feature_columns, 0)

      # Runtime
      input_data['Runtime_Min'] = p_runtime

      # Genres
      for g in p_genres:
        if g in input_data:
          input_data[g] = 1

      # Season
      season_col = f'Season_{p_season}'
      if season_col in input_data:
        input_data[season_col] = 1

      # Type
      type_col = f'Content_Type_{p_type}'
      if type_col in input_data:
        input_data[type_col] = 1

      # Convert to DataFrame
      X_pred = pd.DataFrame([input_data])

      # Run Prediction
      pred_rating = rf_rating.predict(X_pred)[0]
      pred_popularity = rf_pop.predict(X_pred)[0]

      # Log result into database
      backend.log_prediction(
          genres=p_genres,
          runtime=p_runtime,
          season=p_season,
          c_type=p_type,
          imdb=round(pred_rating, 2),
          pop=round(pred_popularity, 2),
      )

      st.markdown('### Projected Performance Metrics')
      res_col1, res_col2 = st.columns(2)

      with res_col1:
        st.metric(
            label='Predicted IMDb Score',
            value=f'{pred_rating:.2f} / 10',
            delta=f'{round(pred_rating - df["IMDb_Score"].mean(), 2)} vs Catalog Average',
        )

      with res_col2:
        st.metric(
            label='Predicted TMDB Popularity',
            value=f'{pred_popularity:.2f}',
            delta=f'{round(pred_popularity - df["TMDB_Popularity"].mean(), 2)} vs Catalog Average',
        )

      st.success('Prediction generated and saved to history!')

# -----------------------------------------------------------------------------
# TAB 7: SAVED HISTORY
# -----------------------------------------------------------------------------
with tab7:
  st.subheader('💾 Prediction History Log')
  st.markdown(
      'Historical record of user-executed model predictions stored in the'
      ' database:'
  )

  history_df = backend.get_prediction_history()
  if not history_df.empty:
    st.dataframe(history_df, use_container_width=True)
  else:
    st.info('No predictions logged yet. Run the ML Predictor Engine to generate history records.')
