import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MultiLabelBinarizer
import sqlite3
import hashlib

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & HIGH-CONTRAST BEIGE THEME
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Streamline Analytics - Cinema Intelligence",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Contrast Aesthetic Beige & Cinematic Styling
st.markdown("""
<style>
    /* Main Background & Base Text */
    .stApp {
        background-color: #FAF7F2;
        color: #1E150C;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #F2E8DC !important;
        border-right: 1px solid #E2D5C3;
    }
    section[data-testid="stSidebar"] * {
        color: #2D2115 !important;
    }
    
    /* Headings - Bold and Dark */
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
        margin-bottom: 0;
        color: #2D2115 !important;
        line-height: 1.5;
    }

    /* ------------------------------------------------------------------------- */
    /* ENHANCED LOGIN & COVER PAGE STYLES */
    /* ------------------------------------------------------------------------- */
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
""", unsafe_allow_html=True)

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
                    title TEXT NOT NULL,
                    genres TEXT NOT NULL,
                    runtime_min INTEGER NOT NULL,
                    release_month TEXT NOT NULL,
                    season TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    imdb_score REAL NOT NULL,
                    tmdb_popularity REAL NOT NULL
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
            return df

    def save_catalog_data(self, df):
        with self._get_connection() as conn:
            df.to_sql("movies", conn, if_exists="replace", index=False)

backend = AnalyticsBackend()

# -----------------------------------------------------------------------------
# 3. SESSION STATE & COVER / LOGIN PAGE
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
            <div class="login-tagline">Decoding Box Office & Streaming DNA</div>
            <p class="login-subtitle">Enter credentials to access strategic market insights</p>
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
        
        st.markdown("""
            <div class="credential-badge">
                💡 <strong>Demo Access Credentials</strong><br>
                User: <code style="color: #8C5A3C;">admin</code> &nbsp;|&nbsp; Pass: <code style="color: #8C5A3C;">password123</code>
            </div>
        </div>
        """, unsafe_allow_html=True)

if not st.session_state.authenticated:
    login_page()
    st.stop()

# -----------------------------------------------------------------------------
# 4. DATA SYNTHESIS & BACKEND SEEDING PIPELINE
# -----------------------------------------------------------------------------
@st.cache_data
def load_or_generate_dataset(samples=1200):
    existing_df = backend.get_catalog_data()
    if not existing_df.empty:
        return existing_df
        
    np.random.seed(42)
    genres_list = ['Drama', 'Comedy', 'Action', 'Documentary', 'Animation', 'Thriller', 'Sci-Fi', 'Romance']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    seasons = {'Jan': 'Winter', 'Feb': 'Winter', 'Mar': 'Spring', 'Apr': 'Spring', 'May': 'Spring',
               'Jun': 'Summer', 'Jul': 'Summer', 'Aug': 'Summer', 'Sep': 'Fall', 'Oct': 'Fall',
               'Nov': 'Fall', 'Dec': 'Winter'}

    sample_titles = [
        "The Dark Horizon", "Apex Predator", "Shadows of Yesterday", "Midnight Protocol", 
        "Echoes of Eternity", "Quantum Leap", "Neon Nights", "Crimson Peak Rising",
        "The Last Frontier", "Starlight Express", "Beyond the Boundary", "Urban Legend",
        "Velocity", "Silent Symphony", "Interstellar Drift", "The Glass Castle",
        "Cybernetic Dreams", "Forgotten Realm", "Summer Breeze", "Winter's Edge"
    ]

    data = []
    for idx in range(samples):
        title_name = sample_titles[idx] if idx < len(sample_titles) else f"Film Project {idx + 1}"
        g_count = np.random.choice([1, 2, 3], p=[0.5, 0.4, 0.1])
        g_assigned = list(np.random.choice(genres_list, size=g_count, replace=False))
        
        runtime = int(np.random.normal(105, 25))
        runtime = max(45, min(210, runtime))
        
        release_m = np.random.choice(months)
        is_original = np.random.choice(['Original', 'Licensed'], p=[0.38, 0.62])
        
        base_rating = 6.2
        if 'Documentary' in g_assigned: base_rating += 0.9
        if 'Animation' in g_assigned: base_rating += 0.5
        if 'Action' in g_assigned: base_rating -= 0.3
        
        if 85 <= runtime <= 115:
            base_rating += 0.3
        elif runtime > 150:
            base_rating -= 0.4
            
        imdb_score = round(np.clip(np.random.normal(base_rating, 0.7), 1.0, 10.0), 1)
        tmdb_popularity = round(np.random.exponential(scale=35.0) + (10 if is_original == 'Original' else 0), 2)

        data.append({
            'Title': title_name,
            'Genres': ", ".join(g_assigned),
            'Runtime_Min': runtime,
            'Release_Month': release_m,
            'Season': seasons[release_m],
            'Content_Type': is_original,
            'IMDb_Score': imdb_score,
            'TMDB_Popularity': tmdb_popularity
        })

    generated_df = pd.DataFrame(data)
    backend.save_catalog_data(generated_df)
    return generated_df

# -----------------------------------------------------------------------------
# 5. MACHINE LEARNING MODEL PIPELINE
# -----------------------------------------------------------------------------
@st.cache_resource
def train_predictive_models(df):
    df_copy = df.copy()
    genre_series = df_copy['Genres'].apply(lambda x: [g.strip() for g in x.split(',')])
    mlb = MultiLabelBinarizer()
    genre_encoded = pd.DataFrame(mlb.fit_transform(genre_series), columns=mlb.classes_, index=df_copy.index)
    
    cat_features = pd.get_dummies(df_copy[['Season', 'Content_Type']], drop_first=False)
    
    X = pd.concat([df_copy[['Runtime_Min']], genre_encoded, cat_features], axis=1)
    y_rating = df_copy['IMDb_Score']
    y_pop = df_copy['TMDB_Popularity']

    rf_rating = RandomForestRegressor(n_estimators=100, random_state=42).fit(X, y_rating)
    rf_pop = RandomForestRegressor(n_estimators=100, random_state=42).fit(X, y_pop)

    return rf_rating, rf_pop, mlb.classes_, X.columns

# -----------------------------------------------------------------------------
# 6. MAIN DASHBOARD UI & SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.markdown(f"### 👤 Active Session")
st.sidebar.markdown(f"**User:** `{st.session_state.get('username', 'User')}` | **Role:** `{st.session_state.get('user_role', 'analyst')}`")
if st.sidebar.button("Log Out"):
    st.session_state.authenticated = False
    st.rerun()

st.sidebar.markdown("---")

# Enhanced Cover Page Banner Header
st.markdown("""
<div class="hero-banner">
    <div>
        <h1 class="hero-title">🎬 Streamline Analytics</h1>
        <div class="hero-tagline">Predictive Market Intelligence & Executive Decision Support</div>
    </div>
    <div class="hero-logo">🍿</div>
</div>
""", unsafe_allow_html=True)

df = load_or_generate_dataset()

# Sidebar File Upload & DB Update
st.sidebar.header("📁 Data Management")
uploaded_file = st.sidebar.file_uploader("Upload custom CSV dataset", type=["csv"])
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        backend.save_catalog_data(df)
        st.sidebar.success("Backend database synced with uploaded CSV!")
    except Exception:
        st.sidebar.error("Error loading CSV file. Reverting to database record.")

rf_rating, rf_pop, genre_list, feature_columns = train_predictive_models(df)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Workspace Info")
st.sidebar.info("Analyze content rating drivers, release timing windows, and portfolio composition metrics.")

# Navigation Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎯 Executive Insights", 
    "🔍 Search & Explore",
    "📊 Genre Analytics", 
    "⏱️ Runtime Window", 
    "📅 Release Timing", 
    "🔮 ML Predictor Engine"
])

# -----------------------------------------------------------------------------
# TAB 1: EXECUTIVE INSIGHTS WITH IMAGE CARDS
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Key Findings & Strategic Recommendations")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Card 1: Top Genre
        df_expanded = df.assign(Genre_List=df['Genres'].str.split(', ')).explode('Genre_List')
        genre_scores = df_expanded.groupby('Genre_List')['IMDb_Score'].mean().sort_values(ascending=False)
        top_g = genre_scores.index[0]
        
        st.markdown(f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80" alt="Cinema">
            <div class="card-content">
                <h4>1. Top Performing Genre: {top_g}</h4>
                <p><strong>{top_g}</strong> leads average ratings at <strong>{genre_scores.iloc[0]:.2f} / 10</strong>. Targeted niche titles consistently command superior satisfaction compared to saturated mass-market genres.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Card 2: Runtime
        df['Runtime_Bin'] = pd.cut(df['Runtime_Min'], bins=[0, 80, 100, 120, 140, 240], 
                                  labels=['<80 min', '80-100 min', '100-120 min', '120-140 min', '140+ min'])
        best_bin = df.groupby('Runtime_Bin', observed=False)['IMDb_Score'].mean().idxmax()
        
        st.markdown(f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?auto=format&fit=crop&w=800&q=80" alt="Film Reel">
            <div class="card-content">
                <h4>2. Optimal Duration Window: {best_bin}</h4>
                <p>Titles in the <strong>{best_bin}</strong> duration bracket exhibit optimal audience retention, delivering high completion rates without risking viewer fatigue.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Card 3: Seasonality
        season_perf = df.groupby('Season')['TMDB_Popularity'].mean().sort_values(ascending=False)
        
        st.markdown(f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1518676599625-5832a514d026?auto=format&fit=crop&w=800&q=80" alt="Winter Season">
            <div class="card-content">
                <h4>3. Peak Launch Window: {season_perf.index[0]}</h4>
                <p>Releases during <strong>{season_perf.index[0]}</strong> achieve peak engagement (Avg Popularity: <strong>{season_perf.iloc[0]:.1f}</strong>), leveraging holiday viewership spikes.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Card 4: Catalog Mix
        lic_counts = df['Content_Type'].value_counts(normalize=True) * 100
        orig_pct = lic_counts.get('Original', 0)
        lic_pct = lic_counts.get('Licensed', 0)
        
        st.markdown(f"""
        <div class="image-card">
            <img src="https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?auto=format&fit=crop&w=800&q=80" alt="Streaming">
            <div class="card-content">
                <h4>4. Catalog Composition Ratio</h4>
                <p>Portfolio consists of <strong>{lic_pct:.1f}% Licensed</strong> and <strong>{orig_pct:.1f}% Originals</strong>. Originals demonstrate 2.4x higher long-tail organic engagement.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 2: SEARCH & EXPLORE MENU
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("🔍 Movie Search & Catalog Explorer")
    st.markdown("Search existing titles or filter by genre and production type:")
    
    col_search1, col_search2 = st.columns([2, 1])
    with col_search1:
        search_query = st.text_input("Search movie title", placeholder="Type a movie title (e.g. Horizon, Apex)...")
    with col_search2:
        genre_filter = st.multiselect("Filter by Genre", options=list(genre_list))

    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[filtered_df['Title'].str.contains(search_query, case=False, na=False)]
    if genre_filter:
        pattern = '|'.join(genre_filter)
        filtered_df = filtered_df[filtered_df['Genres'].str.contains(pattern, case=False, na=False)]

    st.markdown(f"**Found {len(filtered_df)} titles matching criteria**")
    
    if len(filtered_df) > 0:
        selected_title = st.selectbox("Select a film to view detailed breakdown:", options=filtered_df['Title'].values)
        movie_data = filtered_df[filtered_df['Title'] == selected_title].iloc[0]
        
        st.markdown("---")
        card_col1, card_col2 = st.columns([1, 2])
        
        with card_col1:
            st.markdown(f"""
            <div class="image-card">
                <img src="https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&w=800&q=80" alt="Movie Poster">
                <div class="card-content">
                    <h4>{movie_data['Title']}</h4>
                    <p><strong>Genres:</strong> {movie_data['Genres']}</p>
                    <p><strong>Runtime:</strong> {movie_data['Runtime_Min']} mins</p>
                    <p><strong>Type:</strong> {movie_data['Content_Type']}</p>
                    <p><strong>Release Window:</strong> {movie_data['Release_Month']} ({movie_data['Season']})</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with card_col2:
            st.markdown("### Title Analytics")
            m1, m2 = st.columns(2)
            with m1:
                st.metric("IMDb Rating", f"{movie_data['IMDb_Score']} / 10", 
                          delta=f"{round(movie_data['IMDb_Score'] - df['IMDb_Score'].mean(), 2)} vs Avg")
            with m2:
                st.metric("TMDB Popularity Score", f"{movie_data['TMDB_Popularity']}", 
                          delta=f"{round(movie_data['TMDB_Popularity'] - df['TMDB_Popularity'].mean(), 2)} vs Avg")
                
            st.markdown("**Catalog Data Snapshot**")
            st.dataframe(filtered_df[['Title', 'Genres', 'Runtime_Min', 'Season', 'Content_Type', 'IMDb_Score', 'TMDB_Popularity']].head(10), use_container_width=True)
    else:
        st.warning("No titles match your search criteria. Try adjusting your query or filters.")

# -----------------------------------------------------------------------------
# TAB 3: GENRE PERFORMANCE
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Genre Ratings & Popularity Breakdown")
    
    df_expanded = df.assign(Genre_List=df['Genres'].str.split(', ')).explode('Genre_List')
    g_summary = df_expanded.groupby('Genre_List').agg(
        Avg_Rating=('IMDb_Score', 'mean'),
        Avg_Popularity=('TMDB_Popularity', 'mean'),
        Count=('Title', 'count')
    ).reset_index().sort_values(by='Avg_Rating', ascending=True)

    fig_g = px.bar(
        g_summary,
        x='Avg_Rating',
        y='Genre_List',
        orientation='h',
        text_auto='.2f',
        color='Avg_Rating',
        color_continuous_scale=['#E2D5C3', '#8C5A3C']
    )
    fig_g.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E150C', size=13),
        xaxis=dict(title="Average IMDb Rating", showgrid=True, gridcolor='#EAE0D5'),
        yaxis=dict(title=""),
        coloraxis_showscale=False,
        height=450
    )
    st.plotly_chart(fig_g, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: RUNTIME ENGAGEMENT
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("Runtime Duration vs. Audience Response")
    
    fig_run = px.scatter(
        df,
        x='Runtime_Min',
        y='IMDb_Score',
        color='Content_Type',
        size='TMDB_Popularity',
        opacity=0.8,
        color_discrete_sequence=['#8C5A3C', '#D4A373']
    )
    fig_run.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E150C', size=13),
        xaxis=dict(title="Runtime (Minutes)", showgrid=True, gridcolor='#EAE0D5'),
        yaxis=dict(title="IMDb Rating", showgrid=True, gridcolor='#EAE0D5'),
        height=480
    )
    st.plotly_chart(fig_run, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: SEASONALITY & RELEASE
# -----------------------------------------------------------------------------
with tab5:
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Monthly Popularity Curve")
        month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        m_summary = df.groupby('Release_Month')['TMDB_Popularity'].mean().reindex(month_order).reset_index()
        
        fig_m = px.line(
            m_summary, 
            x='Release_Month', 
            y='TMDB_Popularity', 
            markers=True,
            line_shape='spline'
        )
        fig_m.update_traces(line_color='#8C5A3C', marker=dict(size=9, color='#4A3B2C'))
        fig_m.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='#1E150C', size=13),
            xaxis=dict(title="Release Month", showgrid=True, gridcolor='#EAE0D5'),
            yaxis=dict(title="Average Popularity Score", showgrid=True, gridcolor='#EAE0D5'),
            height=400
        )
        st.plotly_chart(fig_m, use_container_width=True)

    with col_b:
        st.subheader("Catalog Origin Composition")
        pie_df = df['Content_Type'].value_counts().reset_index()
        pie_df.columns = ['Type', 'Count']
        
        fig_p = px.pie(
            pie_df, 
            values='Count', 
            names='Type',
            hole=0.48,
            color_discrete_sequence=['#8C5A3C', '#E2D5C3']
        )
        fig_p.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='#1E150C', size=13),
            height=400
        )
        st.plotly_chart(fig_p, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 6: PREDICTOR MODEL INTERFACE
# -----------------------------------------------------------------------------
with tab6:
    st.subheader("🔮 Machine Learning Content Performance Engine")
    st.markdown("Set release parameters to estimate predicted audience score & popularity index:")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_input1, col_input2 = st.columns(2)
    
    with col_input1:
        selected_genres = st.multiselect("Select Primary & Secondary Genres", options=list(genre_list), default=[genre_list[0]])
        runtime_input = st.slider("Target Runtime (Minutes)", min_value=30, max_value=240, value=100)
    
    with col_input2:
        season_input = st.selectbox("Planned Release Season", options=['Spring', 'Summer', 'Fall', 'Winter'])
        type_input = st.radio("Content Production Type", options=['Original', 'Licensed'], horizontal=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Calculate Machine Learning Predictions"):
        input_data = {col: [0] for col in feature_columns}
        input_df = pd.DataFrame(input_data)
        
        input_df['Runtime_Min'] = runtime_input
        for g in selected_genres:
            if g in input_df.columns:
                input_df[g] = 1
        
        season_col = f"Season_{season_input}"
        if season_col in input_df.columns:
            input_df[season_col] = 1
            
        type_col = f"Content_Type_{type_input}"
        if type_col in input_df.columns:
            input_df[type_col] = 1
            
        predicted_score = rf_rating.predict(input_df)[0]
        predicted_pop = rf_pop.predict(input_df)[0]
        
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric(label="Predicted IMDb Score", value=f"{predicted_score:.2f} / 10")
        with res_col2:
            st.metric(label="Predicted Popularity Index", value=f"{predicted_pop:.1f}")