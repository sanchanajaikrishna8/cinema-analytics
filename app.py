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
    page_title="Streamline Analytics & Ticket Booking",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# 2. COMPLETE BACKEND ENGINE (SQLite Persistence & Booking Systems)
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
      # Catalog Table (Includes Karnataka/India Details & Cast Visuals)
      cursor.execute("""
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Title TEXT NOT NULL,
                    Genres TEXT NOT NULL,
                    Cast TEXT DEFAULT 'N/A',
                    Cast_Image TEXT DEFAULT '',
                    Primary_Language TEXT DEFAULT 'Kannada',
                    Available_Languages TEXT DEFAULT 'Kannada, English, Hindi',
                    City TEXT DEFAULT 'Bengaluru',
                    Theaters_Available TEXT DEFAULT 'PVR Forum Mall (Koramangala), INOX Lido Mall (MG Road)',
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
      # Booked Tickets Table
      cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    username TEXT,
                    movie_title TEXT,
                    city TEXT,
                    theater TEXT,
                    seats TEXT,
                    total_price REAL,
                    payment_method TEXT
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

  def save_booking(
      self, username, movie, city, theater, seats, total_price, payment_method
  ):
    with self._get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO bookings 
                (username, movie_title, city, theater, seats, total_price, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
          (
              username,
              movie,
              city,
              theater,
              ", ".join(seats),
              total_price,
              payment_method,
          ),
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
          "SELECT * FROM bookings ORDER BY timestamp DESC", conn
      )


backend = AnalyticsBackend()

# -----------------------------------------------------------------------------
# 3. GLOBAL CUSTOM STYLING (Theming & Interactive UI)
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
    }

    .hero-banner {
        background: linear-gradient(135deg, #2D2115 0%, #4A3B2C 50%, #8C5A3C 100%);
        padding: 30px 40px;
        border-radius: 20px;
        margin-bottom: 24px;
        color: white;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .hero-title {
        color: #FFFFFF !important;
        margin: 0;
        font-size: 2.2rem;
        font-weight: 800;
    }
    .hero-tagline {
        color: #E2D5C3 !important;
        margin-top: 4px;
        font-size: 1rem;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #2D2115 !important;
        font-weight: 700 !important;
    }
    
    /* Seat Map Styles */
    .screen-container {
        width: 100%;
        text-align: center;
        background: #D8C8B8;
        color: #2D2115;
        padding: 6px 0;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: bold;
        letter-spacing: 2px;
        margin-bottom: 25px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
    }
    .cast-img {
        width: 100%;
        height: 220px;
        object-fit: cover;
        border-radius: 12px;
        margin-bottom: 12px;
    }

    .stButton>button {
        background-color: #8C5A3C !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 700 !important;
        padding: 10px 20px !important;
    }
    .stButton>button:hover {
        background-color: #6F452C !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 4. AUTHENTICATION CONTROLLER
# -----------------------------------------------------------------------------
if 'authenticated' not in st.session_state:
  st.session_state.authenticated = False


def login_page():
  st.markdown('<br><br>', unsafe_allow_html=True)
  col1, col2, col3 = st.columns([1, 1.2, 1])
  with col2:
    st.markdown(
        """
        <div style="background-color: white; padding: 40px; border-radius: 20px; border: 1px solid #EAE0D5; text-align: center;">
            <div style="font-size: 3rem; margin-bottom: 10px;">🎟️</div>
            <h2 style="margin-bottom: 0;">Streamline Analytics</h2>
            <p style="color: #8C5A3C; font-weight: bold; font-size: 0.9rem;">Karnataka & India Box Office Edition</p>
        """,
        unsafe_allow_html=True,
    )
    username = st.text_input('Username', key='login_user')
    password = st.text_input('Password', type='password', key='login_pass')

    if st.button('Sign In', use_container_width=True):
      user_info = backend.authenticate_user(username, password)
      if user_info:
        st.session_state.authenticated = True
        st.session_state.username = user_info[0]
        st.session_state.user_role = user_info[1]
        st.rerun()
      else:
        st.error('Invalid username or password.')


if not st.session_state.authenticated:
  login_page()
  st.stop()


# -----------------------------------------------------------------------------
# 5. KARNATAKA / INDIA DATASET GENERATOR & BACKEND SEEDING
# -----------------------------------------------------------------------------
@st.cache_data
def load_or_generate_dataset():
  existing_df = backend.get_catalog_data()
  if not existing_df.empty:
    return existing_df

  # Movies focused around Indian/Karnataka context
  karnataka_movies = [
      {
          'Title': 'KGF: Chapter 2',
          'Genres': 'Action, Drama, Crime',
          'Cast': 'Yash, Sanjay Dutt, Srinidhi Shetty',
          'Cast_Image': (
              'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=800&q=80'
          ),
          'Primary_Language': 'Kannada',
          'Available_Languages': 'Kannada, Hindi, Telugu, Tamil, Malayalam',
          'City': 'Bengaluru',
          'Theaters_Available': (
              'PVR Director\'s Cut (Forum Rex Walk), INOX Mantri Square'
              ' (Malleswaram), Cinepolis (Nexus Shantiniketan)'
          ),
          'Runtime_Min': 168,
          'Release_Month': 'Apr',
          'Season': 'Spring',
          'Content_Type': 'Original',
          'IMDb_Score': 8.3,
          'TMDB_Popularity': 95.4,
      },
      {
          'Title': 'Kantara',
          'Genres': 'Action, Thriller, Mythological',
          'Cast': 'Rishab Shetty, Sapthami Gowda, Kishore',
          'Cast_Image': (
              'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=800&q=80'
          ),
          'Primary_Language': 'Kannada',
          'Available_Languages': 'Kannada, Hindi, Telugu, Tamil',
          'City': 'Mangaluru',
          'Theaters_Available': (
              'PVR Forum Fiza Mall, Bharath Cinemas (Shivam Road), Big Cinema'
          ),
          'Runtime_Min': 148,
          'Release_Month': 'Sep',
          'Season': 'Fall',
          'Content_Type': 'Original',
          'IMDb_Score': 8.2,
          'TMDB_Popularity': 88.1,
      },
      {
          'Title': '777 Charlie',
          'Genres': 'Adventure, Comedy, Drama',
          'Cast': 'Rakshit Shetty, Sangeetha Sringeri, Charlie',
          'Cast_Image': (
              'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=800&q=80'
          ),
          'Primary_Language': 'Kannada',
          'Available_Languages': 'Kannada, Malayalam, Hindi, Tamil',
          'City': 'Mysuru',
          'Theaters_Available': (
              'DRC Cinemas (BM Habitat Mall), INOX Mall of Mysore'
          ),
          'Runtime_Min': 164,
          'Release_Month': 'Jun',
          'Season': 'Summer',
          'Content_Type': 'Original',
          'IMDb_Score': 8.7,
          'TMDB_Popularity': 76.5,
      },
      {
          'Title': 'RRR',
          'Genres': 'Action, Drama, Historical',
          'Cast': 'N.T. Rama Rao Jr., Ram Charan, Alia Bhatt',
          'Cast_Image': (
              'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=800&q=80'
          ),
          'Primary_Language': 'Telugu',
          'Available_Languages': 'Telugu, Kannada, Hindi, Tamil',
          'City': 'Bengaluru',
          'Theaters_Available': (
              'Ur Vashi Theatre (Lalbagh Road), PVR Vega City (Bannerghatta'
              ' Road)'
          ),
          'Runtime_Min': 187,
          'Release_Month': 'Mar',
          'Season': 'Spring',
          'Content_Type': 'Licensed',
          'IMDb_Score': 7.8,
          'TMDB_Popularity': 92.0,
      },
      {
          'Title': 'Sapta Sagarada Dhaati',
          'Genres': 'Romance, Drama',
          'Cast': 'Rakshit Shetty, Rukmini Vasanth',
          'Cast_Image': (
              'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=800&q=80'
          ),
          'Primary_Language': 'Kannada',
          'Available_Languages': 'Kannada, Telugu, Tamil',
          'City': 'Hubballi',
          'Theaters_Available': (
              'PVR Urban Oasis Mall, Cinepolis Laxmi Mall'
          ),
          'Runtime_Min': 142,
          'Release_Month': 'Sep',
          'Season': 'Fall',
          'Content_Type': 'Original',
          'IMDb_Score': 8.4,
          'TMDB_Popularity': 64.2,
      },
  ]

  generated_df = pd.DataFrame(karnataka_movies)
  backend.save_catalog_data(generated_df)
  return generated_df


# -----------------------------------------------------------------------------
# 6. MACHINE LEARNING PIPELINE
# -----------------------------------------------------------------------------
@st.cache_resource
def train_predictive_models(df):
  if df.empty:
    return None, None, [], []
  df_copy = df.copy()
  genre_series = df_copy['Genres'].apply(
      lambda x: [g.strip() for g in x.split(',')]
  )
  mlb = MultiLabelBinarizer()
  genre_encoded = pd.DataFrame(
      mlb.fit_transform(genre_series),
      columns=mlb.classes_,
      index=df_copy.index,
  )
  cat_features = pd.get_dummies(
      df_copy[['Season', 'Content_Type']], drop_first=False
  )
  X = pd.concat([df_copy[['Runtime_Min']], genre_encoded, cat_features], axis=1)

  rf_rating = RandomForestRegressor(
      n_estimators=100, random_state=42
  ).fit(X, df_copy['IMDb_Score'])
  rf_pop = RandomForestRegressor(
      n_estimators=100, random_state=42
  ).fit(X, df_copy['TMDB_Popularity'])

  return rf_rating, rf_pop, mlb.classes_, X.columns


# Load Data & Models
df = load_or_generate_dataset()
rf_rating, rf_pop, genre_list, feature_columns = train_predictive_models(df)

# Sidebar
with st.sidebar:
  st.markdown(
      '<div class="sidebar-brand-card"><h3>🎬 Cinema Core</h3><p>Karnataka &'
      ' India Hub</p></div>',
      unsafe_allow_html=True,
  )
  username = st.session_state.get('username', 'User')
  st.markdown(
      f'<div class="user-profile-badge"><div'
      f' class="user-avatar">{username[0].upper()}</div><div><strong>{username.capitalize()}</strong></div></div>',
      unsafe_allow_html=True,
  )
  if st.button('🚪 Sign Out', use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()

# Cover Hero Header
st.markdown(
    """
<div class="hero-banner">
    <div>
        <h1 class="hero-title">🎬 Cinema Core India & Karnataka</h1>
        <div class="hero-tagline">Movie Booking Engine & Strategic Predictive Analytics</div>
    </div>
    <div style="font-size: 3rem;">🎟️</div>
</div>
""",
    unsafe_allow_html=True,
)

# Navigation Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    '🎟️ Book Tickets (Karnataka)',
    '🔍 Search & Cast Gallery',
    '📊 Analytics & Insights',
    '🔮 ML Predictor Engine',
    '📜 History & Bookings',
])

# -----------------------------------------------------------------------------
# TAB 1: INTERACTIVE TICKET BOOKING ENGINE (Karnataka Focus)
# -----------------------------------------------------------------------------
with tab1:
  st.subheader('🍿 Book Movie Tickets in Karnataka')

  step_col1, step_col2 = st.columns([1, 1.5])

  with step_col1:
    st.markdown('### Step 1: Location & Theater')
    city_selected = st.selectbox(
        'Select City in Karnataka:',
        options=['Bengaluru', 'Mysuru', 'Mangaluru', 'Hubballi', 'Belagavi'],
    )

    # Filter movies by availability
    available_movies = df['Title'].tolist()
    movie_selected = st.selectbox('Select Movie:', options=available_movies)

    movie_info = df[df['Title'] == movie_selected].iloc[0]

    # Dynamic theater assignment based on city selection
    theaters = [t.strip() for t in movie_info['Theaters_Available'].split(',')]
    theater_selected = st.selectbox('Select Theater:', options=theaters)

    show_time = st.selectbox(
        'Select Showtime:',
        options=[
            '10:30 AM (Morning)',
            '01:45 PM (Matinee)',
            '05:15 PM (Evening)',
            '09:30 PM (Night)',
        ],
    )

  with step_col2:
    st.markdown('### Step 2: Interactive Seat Selection')
    st.markdown('<div class="screen-container">SCREEN THIS WAY</div>', unsafe_allow_html=True)

    # Pricing structure definition
    PRICING = {'Executive': 180, 'VIP': 350, 'Recliner': 550}

    st.markdown('**Select Category & Seats:**')
    st.caption(
        f"🟢 Recliner: ₹{PRICING['Recliner']} | 🔵 VIP: ₹{PRICING['VIP']} | 🟡"
        f" Executive: ₹{PRICING['Executive']}"
    )

    # Generate Seat Grid
    rows = ['A', 'B', 'C', 'D', 'E']
    cols = [1, 2, 3, 4, 5, 6]

    selected_seats = []

    for r in rows:
      category = (
          'Recliner'
          if r in ['A']
          else ('VIP' if r in ['B', 'C'] else 'Executive')
      )
      st.markdown(f'**Row {r}** ({category} - ₹{PRICING[category]}):')
      grid_cols = st.columns(6)
      for idx, c in enumerate(cols):
        seat_id = f'{r}{c}'
        # Checkbox for interactive seat selection
        if grid_cols[idx].checkbox(seat_id, key=f'seat_{seat_id}'):
          selected_seats.append((seat_id, PRICING[category]))

  st.markdown('---')
  st.markdown('### Step 3: Checkout & Payment')

  if selected_seats:
    total_amount = sum([s[1] for s in selected_seats])
    seat_names = [s[0] for s in selected_seats]

    pay_col1, pay_col2 = st.columns(2)
    with pay_col1:
      st.info(f"""
            **Booking Summary:**  
            * **Movie:** {movie_selected}  
            * **Location:** {city_selected} | {theater_selected}  
            * **Showtime:** {show_time}  
            * **Selected Seats:** {', '.join(seat_names)}  
            * **Total Payable:** **₹{total_amount}** (Incl. GST)
            """)

    with pay_col2:
      payment_method = st.radio(
          'Select Payment Method:',
          options=['UPI (GPay / PhonePe / Paytm)', 'Credit / Debit Card', 'Net Banking'],
          horizontal=True,
      )

      if payment_method == 'UPI (GPay / PhonePe / Paytm)':
        upi_id = st.text_input('Enter UPI ID:', value='user@upi')
      else:
        card_num = st.text_input('Card Number:', placeholder='XXXX-XXXX-XXXX-XXXX')

      if st.button('💳 Pay Now & Confirm Booking', use_container_width=True):
        backend.save_booking(
            username=st.session_state.username,
            movie=movie_selected,
            city=city_selected,
            theater=theater_selected,
            seats=seat_names,
            total_price=total_amount,
            payment_method=payment_method,
        )
        st.balloons()
        st.success(
            f'🎉 Payment Successful via {payment_method}! Ticket confirmed for'
            f' {", ".join(seat_names)}.'
        )
  else:
    st.warning('Please select at least one seat to proceed with payment.')

# -----------------------------------------------------------------------------
# TAB 2: SEARCH & CAST VISUAL GALLERY
# -----------------------------------------------------------------------------
with tab2:
  st.subheader('🔍 Movies & Cast Gallery')

  selected_title = st.selectbox('Select Movie Details:', options=df['Title'].values)
  movie_data = df[df['Title'] == selected_title].iloc[0]

  c_info1, c_info2 = st.columns([1, 2])
  with c_info1:
    if movie_data['Cast_Image']:
      st.markdown(
          f'<img src="{movie_data["Cast_Image"]}" class="cast-img" alt="Cast">',
          unsafe_allow_html=True,
      )
    st.markdown(f"### {movie_data['Title']}")
    st.markdown(f"**🎭 Star Cast:** {movie_data['Cast']}")
    st.markdown(f"**🗣️ Primary Language:** {movie_data['Primary_Language']}")
    st.markdown(f"**🌍 Languages:** {movie_data['Available_Languages']}")

  with c_info2:
    st.markdown('### Screening Details')
    st.markdown(
        f"**📍 Key Karnataka Cities:** {movie_data.get('City', 'Bengaluru')}"
    )
    st.markdown(
        f"**🏛️ Available Theaters:** {movie_data['Theaters_Available']}"
    )
    st.markdown(f"**⏱️ Runtime:** {movie_data['Runtime_Min']} Mins")

    m1, m2 = st.columns(2)
    with m1:
      st.metric('IMDb Rating', f"{movie_data['IMDb_Score']} / 10")
    with m2:
      st.metric('TMDB Popularity', f"{movie_data['TMDB_Popularity']}")

# -----------------------------------------------------------------------------
# TAB 3: ANALYTICS & INSIGHTS
# -----------------------------------------------------------------------------
with tab3:
  st.subheader('📊 Catalog Analytics')
  fig_g = px.bar(
      df,
      x='IMDb_Score',
      y='Title',
      orientation='h',
      color='Primary_Language',
      title='IMDb Ratings across Indian Releases',
  )
  st.plotly_chart(fig_g, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: ML PREDICTOR ENGINE
# -----------------------------------------------------------------------------
with tab4:
  st.subheader('🔮 Machine Learning Score Predictor')
  p_genres = st.multiselect(
      'Target Genres', options=list(genre_list), default=['Action', 'Drama']
  )
  p_runtime = st.slider('Runtime (Mins)', 60, 210, 150)
  p_season = st.selectbox('Release Season', ['Spring', 'Summer', 'Fall', 'Winter'])
  p_type = st.radio('Content Type', ['Original', 'Licensed'], horizontal=True)

  if st.button('Execute ML Model', use_container_width=True):
    input_data = dict.fromkeys(feature_columns, 0)
    input_data['Runtime_Min'] = p_runtime
    for g in p_genres:
      if g in input_data:
        input_data[g] = 1
    if f'Season_{p_season}' in input_data:
      input_data[f'Season_{p_season}'] = 1
    if f'Content_Type_{p_type}' in input_data:
      input_data[f'Content_Type_{p_type}'] = 1

    X_pred = pd.DataFrame([input_data])
    pred_rating = rf_rating.predict(X_pred)[0]
    pred_pop = rf_pop.predict(X_pred)[0]

    st.metric('Predicted IMDb Score', f'{pred_rating:.2f} / 10')
    st.metric('Predicted Popularity', f'{pred_pop:.2f}')
    backend.log_prediction(
        p_genres,
        p_runtime,
        p_season,
        p_type,
        round(pred_rating, 2),
        round(pred_pop, 2),
    )

# -----------------------------------------------------------------------------
# TAB 5: HISTORY & BOOKINGS
# -----------------------------------------------------------------------------
with tab5:
  st.subheader('📜 Ticket Booking History & Logs')
  booking_df = backend.get_booking_history()
  if not booking_df.empty:
    st.dataframe(booking_df, use_container_width=True)
  else:
    st.info('No tickets booked yet.')
