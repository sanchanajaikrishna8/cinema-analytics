import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Cinema Analytics Dashboard", layout="wide")

# ---------------------------------------------------------
# 1. SAMPLE DATASET WITH CAST, LANGUAGES & THEATERS
# ---------------------------------------------------------
@st.cache_data
def load_movie_data():
    movies = [
        {
            "Title": "Cyber Odyssey 2099",
            "Genre": "Sci-Fi",
            "Rating": 8.7,
            "Budget ($M)": 150,
            "Box Office ($M)": 480,
            "Cast": "Keanu Reeves, Zendaya, Oscar Isaac",
            "Director": "Denis Villeneuve",
            "Primary Language": "English",
            "Available Languages": "English, Spanish, French, Japanese",
            "Theaters Available": ["AMC Lincoln Square", "Regal LA Live", "IMAX Melbourne"],
            "Lat": 34.0403, "Lon": -118.2696 # LA coordinates
        },
        {
            "Title": "Shadows of Kyoto",
            "Genre": "Action",
            "Rating": 8.2,
            "Budget ($M)": 45,
            "Box Office ($M)": 190,
            "Cast": "Hiroyuki Sanada, Anna Sawai, Ken Watanabe",
            "Director": "Chad Stahelski",
            "Primary Language": "Japanese",
            "Available Languages": "Japanese, English (Subbed), German",
            "Theaters Available": ["TOHO Cinemas Shinjuku", "AMC Empire 25"],
            "Lat": 35.6938, "Lon": 139.7034 # Tokyo coordinates
        },
        {
            "Title": "The Last Symphony",
            "Genre": "Drama",
            "Rating": 9.0,
            "Budget ($M)": 25,
            "Box Office ($M)": 115,
            "Cast": "Cate Blanchett, Joaquin Phoenix",
            "Director": "Todd Field",
            "Primary Language": "English",
            "Available Languages": "English, Italian, German",
            "Theaters Available": ["BFI IMAX London", "Cineworld Leicester Square"],
            "Lat": 51.5033, "Lon": -0.1135 # London coordinates
        },
        {
            "Title": "Laughter Therapy",
            "Genre": "Comedy",
            "Rating": 7.4,
            "Budget ($M)": 20,
            "Box Office ($M)": 85,
            "Cast": "Ryan Reynolds, Emma Stone",
            "Director": "Shawn Levy",
            "Primary Language": "English",
            "Available Languages": "English, Spanish, Portuguese",
            "Theaters Available": ["Regal Union Square", "AMC Burbank 16"],
            "Lat": 40.7359, "Lon": -73.9911 # NYC coordinates
        }
    ]
    return pd.DataFrame(movies)

df = load_movie_data()

# ---------------------------------------------------------
# 2. SIDEBAR FILTERS
# ---------------------------------------------------------
st.sidebar.title("🎬 Filter Menu")

genre_filter = st.sidebar.multiselect(
    "Select Genre",
    options=df["Genre"].unique(),
    default=df["Genre"].unique()
)

lang_filter = st.sidebar.multiselect(
    "Select Primary Language",
    options=df["Primary Language"].unique(),
    default=df["Primary Language"].unique()
)

filtered_df = df[
    (df["Genre"].isin(genre_filter)) & 
    (df["Primary Language"].isin(lang_filter))
]

# ---------------------------------------------------------
# 3. MAIN DASHBOARD UI
# ---------------------------------------------------------
st.title("🎥 Cinema Analytics & Theater Intelligence Platform")
st.markdown("Explore cast, localized languages, theater availability, and box office metrics.")

# Top Metrics Row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Movies Loaded", len(filtered_df))
col2.metric("Avg Box Office ($M)", f"${filtered_df['Box Office ($M)'].mean():.1f}M" if len(filtered_df)>0 else "$0")
col3.metric("Top IMDb Rating", f"{filtered_df['Rating'].max()}" if len(filtered_df)>0 else "N/A")
col4.metric("Languages Represented", len(filtered_df["Primary Language"].unique()))

st.divider()

# Navigation Tabs
tab1, tab2, tab3 = st.tabs(["🍿 Movies & Theater Finder", "📊 Financial Analytics", "🤖 Success Predictor"])

# TAB 1: MOVIES, CAST & THEATER LOCATIONS
with tab1:
    st.subheader("Movie Directory & Screening Locations")
    
    selected_movie = st.selectbox("Select a Movie to View Details:", filtered_df["Title"].unique())
    
    if selected_movie:
        movie_info = filtered_df[filtered_df["Title"] == selected_movie].iloc[0]
        
        info_col1, info_col2 = st.columns([1, 1])
        
        with info_col1:
            st.markdown(f"### **{movie_info['Title']}** ({movie_info['Genre']})")
            st.write(f"⭐ **IMDb Rating:** {movie_info['Rating']}/10")
            st.write(f"🎬 **Director:** {movie_info['Director']}")
            st.write(f"🎭 **Main Cast:** {movie_info['Cast']}")
            st.write(f"🗣️ **Primary Language:** {movie_info['Primary Language']}")
            st.write(f"🌍 **Subtitles / Dubbing:** {movie_info['Available Languages']}")
            st.write(f"🏛️ **Exhibiting Theaters:** {', '.join(movie_info['Theaters Available'])}")
        
        with info_col2:
            st.write("📍 **Primary Exhibition Location**")
            map_data = pd.DataFrame([{"lat": movie_info["Lat"], "lon": movie_info["Lon"]}])
            st.map(map_data, zoom=10)

# TAB 2: FINANCIAL PERFORMANCE
with tab2:
    st.subheader("Budget vs. Revenue Performance")
    fig = px.bar(
        filtered_df, 
        x="Title", 
        y=["Budget ($M)", "Box Office ($M)"], 
        barmode="group",
        title="Production Cost vs Global Box Office Returns",
        labels={"value": "USD ($ Millions)", "variable": "Metric"}
    )
    st.plotly_chart(fig, use_container_width=True)

# TAB 3: MACHINE LEARNING PREDICTOR
with tab3:
    st.subheader("Predict Box Office Success")
    st.write("Estimate revenue based on budget, expected rating, and language scope.")
    
    in_budget = st.slider("Production Budget ($M)", 5, 250, 50)
    in_rating = st.slider("Expected Audience Rating", 1.0, 10.0, 7.5)
    in_langs = st.slider("Target Distribution Languages", 1, 10, 3)
    
    # Simple predictive heuristic engine
    predicted_box_office = (in_budget * 1.8) + (in_rating * 15) + (in_langs * 8)
    
    st.success(f"📈 **Predicted World Box Office:** ${predicted_box_office:.2f} Million")
