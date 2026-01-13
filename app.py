import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar

# --- PREMIUM CONFIGURATION ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="expanded")

# Zaawansowany CSS dla nowoczesnego wyglądu
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #e0e0e0;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }

    /* Stylizacja Sidebaru */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.8);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Karty i Kontenery */
    .stMetric, .element-container {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Przyciski */
    .stButton>button {
        background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5);
        color: white;
    }

    /* Nagłówki */
    h1, h2, h3 {
        background: -webkit-linear-gradient(#fff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM LOGOWANIA ---
st.sidebar.markdown("<h2 style='text-align: center; color: #3b82f6;'>SQM PRO</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 ZALOGUJ JAKO:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Hasło (PIN):", type="password")
    if input_pin == user_pins.get(user):
        is_authenticated = True
    elif input_pin:
        st.sidebar.error("❌ Błędny PIN")

if not is_authenticated:
    st.markdown("<div style='text-align: center; padding-top: 100px;'><h1>SQM MULTIMEDIA SOLUTIONS</h1><p>Wprowadź dane logowania w panelu bocznym.</p></div>", unsafe_allow_html=True)
    st.stop()

# --- PANEL BOCZNY MENU ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 SYNCHRONIZUJ DANE"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio("Nawigacja:", [
    "🛰️ CENTRUM OPERACYJNE", 
    "📅 KALENDARZ WYJAZDÓW", 
    "📊 OŚ CZASU (GANTT)", 
    "📌 NOTATKI ZESPOŁU"
])

# --- POBIERANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_all["Data końca"] = df_all["Data końca"].fillna(df_all["Pierwszy wyjazd"])

    df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
    df_notes["Autor"] = df_notes["Autor"].astype(str).str.upper().replace(['NAN', 'NONE', ''], 'NIEPRZYPISANE')
except Exception:
    st.error("Błąd połączenia. Poczekaj 60 sekund (Limit Google).")
    st.stop()

# --- MODUŁ 1: CENTRUM OPERACYJNE ---
if menu == "🛰️ CENTRUM OPERACYJNE":
    st.title("🛰️ Centrum Operacyjne Logistyki")
    
    # Szybkie statystyki w kartach
    c1, c2, c3 = st.columns(3)
    active_count = len(df_all[df_all["Status"] != "WRÓCIŁO"])
    c1.metric("Aktywne Projekty", active_count)
    c2.metric("Twoje Transporty", len(df_all[df_all["Logistyk"] == user]))
    c3.metric("Status Bazy", "Połączona ✅")

    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()
    
    # Filtrowanie (Glassmorphism effect)
    with st.expander("🔍 FILTROWANIE I WYSZUKIWANIE"):
        f1, f2 = st.columns(2)
        search = f1.text_input("Szukaj projektu:")
        f_log = f2.multiselect("Pokaż logistyka:", options=df_active["Logistyk"].unique())

    if search: df_active = df_active[df_active["Nazwa Targów"].str.contains(search, case=False)]
    if f_log: df_active = df_active[df_active["Logistyk"].isin(f_log)]

    # Edycja tylko swoich
    st.subheader(f"🛠️ TWOJE ZADANIA ({user})")
    my_df = df_active[df_active["Logistyk"] == user].copy()
    
    edited_my = st.data_editor(
        my_df, 
        use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "Logistyk": st.column_config.TextColumn("Właściciel", disabled=True, default=user),
            "Pierwszy wyjazd": st.column_config.DateColumn("Wyjazd"),
            "Data końca": st.column_config.DateColumn("Powrót"),
            "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"]),
            "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
        }
    )

    if st.button("💾 ZAPISZ ZMIANY W BAZIE"):
        save_my = edited_my.copy()
        save_my["Logistyk"] = user
        for col in ["Pierwszy wyjazd", "Data końca"]:
            save_my[col] = pd.to_datetime(save_my[col]).dt.strftime('%Y-%m-%d').fillna('')
        
        others = df_all[~df_all.index.isin(my_df.index)].copy()
        for col in ["Pierwszy wyjazd", "Data końca"]:
            others[col] = pd.to_datetime(others[col]).dt.strftime('%Y-%m-%d').fillna('')
            
        final = pd.concat([save_my, others], ignore_index=True)
        conn.update(worksheet="targi", data=final)
        st.cache_data.clear()
        st.success("Dane zsynchronizowane!")
        st.rerun()

    st.markdown("---")
    st.subheader("👁️ TRANSPORTY PARTNERA")
    st.dataframe(df_active[df_active["Logistyk"] != user], use_container_width=True, hide_index=True)

# --- MODUŁ 2: KALENDARZ ---
elif menu == "📅 KALENDARZ WYJAZDÓW":
    st.title("📅 Grafik Operacyjny")
    df_cal = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].copy()
    events = []
    for _, r in df_cal.iterrows():
        color = "#3b82f6" if r["Logistyk"] == "DUKIEL" else "#f59e0b"
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": color,
            "borderColor": "white"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: GANTT (NAPRAWIONY) ---
elif menu == "📊 OŚ CZASU (GANTT)":
    st.title("📊 Obłożenie Naczep w Czasie")
    df_viz = df_all[df_all["Status"] != "WRÓCIŁO"].dropna(subset=["Pierwszy wyjazd"]).copy()
    if not df_viz.empty:
        # NAPRAWIONO: x_start i x_end zamiast start/end
        fig = px.timeline(
            df_viz, 
            x_start="Pierwszy wyjazd", 
            x_end="Data końca", 
            y="Nazwa Targów", 
            color="Logistyk",
            template="plotly_dark",
            color_discrete_map={"DUKIEL": "#3b82f6", "KACZMAREK": "#f59e0b"}
        )
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#e0e0e0")
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 4: NOTATKI ---
elif menu == "📌 NOTATKI ZESPOŁU":
    st.title("📌 Zadania i Komunikaty")
    
    col1, col2 = st.columns(2)
    
    my_n = df_notes[df_notes["Autor"] == user].copy()
    others_n = df_notes[df_notes["Autor"] != user].copy()

    with col1:
        st.subheader("Moje wpisy")
        ed = st.data_editor(my_n, use_container_width=True, hide_index=True, num_rows="dynamic",
                            column_config={"Autor": st.column_config.TextColumn(disabled=True, default=user)})
        if st.button("💾 Zapisz Notatki"):
            ed["Autor"] = user
            ed["Data"] = pd.to_datetime(ed["Data"]).dt.strftime('%Y-%m-%d').fillna('')
            others_save = others_n.copy()
            others_save["Data"] = pd.to_datetime(others_save["Data"]).dt.strftime('%Y-%m-%d').fillna('')
            conn.update(worksheet="ogloszenia", data=pd.concat([ed, others_save], ignore_index=True))
            st.cache_data.clear()
            st.success("Zaktualizowano!")
            st.rerun()

    with col2:
        st.subheader("Wpisy partnera")
        st.dataframe(others_n, use_container_width=True, hide_index=True)
