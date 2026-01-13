import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar

# --- KONFIGURACJA WIZUALNA ---
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")

# Niestandardowy CSS dla lepszego wyglądu
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #00458d;
        color: white;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #0066cc;
        border: 1px solid white;
    }
    .stDataFrame {
        border: 1px solid #31333f;
        border-radius: 10px;
    }
    .filter-container {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 5px solid #00458d;
    }
    h1, h2, h3 {
        color: #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM LOGIN (SIDEBAR) ---
st.sidebar.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150) # Przykładowe logo SQM
st.sidebar.title("🔐 PANEL DOSTĘPU")
user = st.sidebar.selectbox("👤 Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Podaj PIN:", type="password")
    if input_pin == user_pins.get(user):
        is_authenticated = True
    elif input_pin != "":
        st.sidebar.error("Błędny PIN")

if not is_authenticated:
    st.info("Zaloguj się, aby uzyskać dostęp do systemów SQM.")
    st.stop()

# --- REFRESH BUTTON ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 ODŚWIEŻ BAZĘ DANYCH"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio("📋 MENU GŁÓWNE", [
    "📅 HARMONOGRAM BIEŻĄCY", 
    "📆 WIDOK KALENDARZA", 
    "📊 OŚ CZASU (GANTT)", 
    "📁 ARCHIWUM", 
    "📌 NOTATKI"
])

# --- POBIERANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_all["Data końca"] = df_all["Data końca"].fillna(df_all["Pierwszy wyjazd"])

    df_notes_raw = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
    df_notes_raw["Data"] = pd.to_datetime(df_notes_raw["Data"], errors='coerce')
    df_notes_raw["Autor"] = df_notes_raw["Autor"].astype(str).str.upper().replace(['NAN', 'NONE', ''], 'NIEPRZYPISANE')
except Exception as e:
    st.error("Błąd połączenia z bazą danych.")
    st.stop()

# --- MODUŁ 1: HARMONOGRAM ---
if menu == "📅 HARMONOGRAM BIEŻĄCY":
    st.title("🚛 Harmonogram Operacyjny 2026")
    
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()

    # Stylizowane kontenery na filtry
    with st.container():
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)
        col_s, col_l = st.columns([2, 1])
        search = col_s.text_input("🔍 Szukaj targów / lokalizacji:")
        f_log = col_l.multiselect("👤 Pokaż logistyka:", options=sorted(df_active["Logistyk"].unique()))
        st.markdown('</div>', unsafe_allow_html=True)

    if search: df_active = df_active[df_active["Nazwa Targów"].str.contains(search, case=False)]
    if f_log: df_active = df_active[df_active["Logistyk"].isin(f_log)]

    my_tasks = df_active[df_active["Logistyk"] == user].copy()
    others_tasks = df_active[df_active["Logistyk"] != user].copy()

    st.subheader(f"✅ TWOJE PROJEKTY ({user})")
    edited_my = st.data_editor(
        my_tasks, 
        use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "Logistyk": st.column_config.TextColumn("Logistyk", disabled=True, default=user),
            "Pierwszy wyjazd": st.column_config.DateColumn("Start"),
            "Data końca": st.column_config.DateColumn("Koniec"),
            "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"]),
            "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK ✅", "NIE ❌", "NIE POTRZEBA"]),
        }
    )

    if st.button("💾 ZATWIERDŹ I ZAPISZ ZMIANY"):
        save_my = edited_my.copy()
        save_my["Logistyk"] = user
        for col in ["Pierwszy wyjazd", "Data końca"]:
            save_my[col] = pd.to_datetime(save_my[col]).dt.strftime('%Y-%m-%d').fillna('')
        
        rest_data = df_all[~df_all.index.isin(my_tasks.index)].copy()
        for col in ["Pierwszy wyjazd", "Data końca"]:
            rest_data[col] = pd.to_datetime(rest_data[col]).dt.strftime('%Y-%m-%d').fillna('')
        
        final = pd.concat([save_my, rest_data], ignore_index=True).drop_duplicates(subset=["Nazwa Targów", "Pierwszy wyjazd"])
        conn.update(worksheet="targi", data=final)
        st.cache_data.clear()
        st.success("Synchronizacja zakończona pomyślnie!")
        st.rerun()

    st.markdown("---")
    st.subheader("👀 POZOSTAŁE TRANSPORTY (Tylko podgląd)")
    st.dataframe(others_tasks, use_container_width=True, hide_index=True)

# --- MODUŁ 2: KALENDARZ ---
elif menu == "📆 WIDOK KALENDARZA":
    st.title("📅 Grafik Miesięczny SQM")
    df_cal = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].copy()
    events = []
    for _, r in df_cal.iterrows():
        c = "#00458d" if r["Logistyk"] == "DUKIEL" else ("#e67e22" if r["Logistyk"] == "KACZMAREK" else "#7f8c8d")
        events.append({"title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"), "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "backgroundColor": c, "borderColor": "white"})
    calendar(events=events, options={"locale": "pl", "firstDay": 1, "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,dayGridWeek"}})

# --- MODUŁ 3: GANTT ---
elif menu == "📊 OŚ CZASU (GANTT)":
    st.title("📊 Planowanie obłożenia naczep")
    df_viz = df_all[df_all["Status"] != "WRÓCIŁO"].dropna(subset=["Pierwszy wyjazd"]).copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk", template="plotly_dark",
                          color_discrete_map={"DUKIEL": "#00458d", "KACZMAREK": "#e67e22"})
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 5: NOTATKI ---
elif menu == "📌 NOTATKI":
    st.title("📌 Tablica Notatek i Zadań")
    col1, col2 = st.columns([1, 1])
    
    my_notes = df_notes_raw[df_notes_raw["Autor"] == user].copy()
    others_notes = df_notes_raw[df_notes_raw["Autor"] != user].copy()

    with col1:
        st.subheader("🖋️ Twoje notatki")
        ed_n = st.data_editor(my_notes, use_container_width=True, hide_index=True, num_rows="dynamic",
                              column_config={"Autor": st.column_config.TextColumn(disabled=True, default=user)})
        if st.button("💾 Zapisz moje notatki"):
            ed_n["Autor"] = user
            ed_n["Data"] = pd.to_datetime(ed_n["Data"]).dt.strftime('%Y-%m-%d').fillna('')
            others_n_save = others_notes.copy()
            others_n_save["Data"] = pd.to_datetime(others_n_save["Data"]).dt.strftime('%Y-%m-%d').fillna('')
            conn.update(worksheet="ogloszenia", data=pd.concat([ed_n, others_n_save], ignore_index=True))
            st.cache_data.clear()
            st.success("Zapisano!")
            st.rerun()

    with col2:
        st.subheader("👁️ Notatki zespołu")
        st.dataframe(others_notes, use_container_width=True, hide_index=True)
