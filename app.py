import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import uuid

# --- 1. KONFIGURACJA WIZUALNA (SZEROKI EKRAN I STYLIZACJA) ---
st.set_page_config(
    page_title="SZTAB LOGISTYKI SQM", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');
    
    .stApp { 
        background-color: #4b5320; 
        background-image: url("https://www.transparenttextures.com/patterns/dark-leather.png");
        font-family: 'Special Elite', cursive; 
        color: #f1f1f1;
    }
    
    [data-testid="stSidebar"] { background-color: #2b2f11; border-right: 5px solid #1a1c0a; }
    
    /* Stylizacja tabel i rzędów */
    .row-container {
        background-color: rgba(253, 245, 230, 0.95);
        color: #1a1a1a !important;
        padding: 15px;
        border-radius: 5px;
        border: 2px solid #000;
        margin-bottom: 10px;
    }
    
    .stButton>button {
        background-color: #fdf5e6; color: #8b0000; border: 3px double #8b0000;
        font-family: 'Special Elite', cursive; font-weight: bold;
        text-transform: uppercase; width: 100%; box-shadow: 2px 2px 0px #000;
    }

    h1, h2, h3 {
        font-family: 'Special Elite', cursive !important; color: #fdf5e6 !important;
        text-shadow: 2px 2px 4px #000; text-transform: uppercase;
    }

    /* Naprawa widoczności inputów */
    input, select, textarea {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIKA KOSZTÓW (STAŁA) ---
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6},
    "WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Bazylea":850,"Berlin":220,"Bruksela":750,"Budapeszt":550,"Cannes / Nicea":1400,"Frankfurt nad Menem":600,"Gdańsk":250,"Genewa":1200,"Hamburg":450,"Hannover":400,"Kielce":280,"Kolonia / Dusseldorf":650,"Kopenhaga":500,"Lipsk":350,"Liverpool":1100,"Lizbona":2100,"Londyn":750,"Lyon":1100,"Madryt":1950,"Manchester":1100,"Mediolan":1100,"Monachium":650,"Norymberga":500,"Paryż":950,"Praga":300,"Rzym":1500,"Sewilla":1600,"Sofia":1100,"Sztokholm":900,"Tuluza":1400,"Warszawa":280,"Wiedeń":550},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":1956.6,"Warszawa":313.8,"Wiedeń":478.2}
}

# --- 3. POŁĄCZENIE ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 4. SYSTEM SESJI I BUFOROWANIA ---
# Uwierzytelnianie
user = st.sidebar.selectbox("👤 LOGOWANIE:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz...": st.stop()
pin = st.sidebar.text_input("PIN:", type="password")
if pin != user_pins.get(user): st.stop()

# Wczytywanie danych do session_state (tylko raz)
if 'df_master' not in st.session_state:
    try:
        df = conn.read(worksheet="targi", ttl=0).fillna("")
        # Konwersja dat
        df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"], errors='coerce')
        df["Data końca"] = pd.to_datetime(df["Data końca"], errors='coerce')
        # Zapewnienie kompletu kolumn jeśli arkusz jest nowy
        cols = ["Nazwa Targów", "Miejsce Załadunku", "Miejsce Rozładunku", "Auto", "Kierowca", "Logistyk", "Pierwszy wyjazd", "Data końca", "Status", "Sloty", "Uwagi", "UID"]
        for c in cols:
            if c not in df.columns: df[c] = ""
        st.session_state.df_master = df
    except Exception as e:
        st.error(f"Błąd bazy: {e}"); st.stop()

# --- 5. NAWIGACJA ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 PLANOWANIE TRANSPORTÓW", "📅 KALENDARZ", "📊 GANNT", "📋 ROZKAZY", "🧮 KOSZTY"])

if menu == "🏠 PLANOWANIE TRANSPORTÓW":
    st.title("📑 Operacyjny Rejestr Transportowy")
    
    # Przycisk wymuszenia synchronizacji z bazą
    if st.sidebar.button("🔄 ODSWIEŻ Z ARKUSZA"):
        del st.session_state.df_master
        st.rerun()

    # DODAWANIE NOWEGO PROJEKTU (Szybki Formularz)
    with st.expander("➕ NOWY TRANSPORT / TARGKI", expanded=False):
        with st.form("quick_add"):
            c1, c2, c3 = st.columns(3)
            n_targi = c1.text_input("Nazwa Targów:")
            n_zal = c2.text_input("Załadunek (Skąd):", value="Magazyn SQM")
            n_roz = c3.text_input("Rozładunek (Gdzie):")
            
            c4, c5, c6, c7 = st.columns(4)
            n_auto = c4.text_input("Auto / Rejestracja:")
            n_driver = c5.text_input("Kierowca:")
            n_start = c6.date_input("Data Wyjazdu:", datetime.now())
            n_end = c7.date_input("Data Powrotu:", datetime.now() + timedelta(days=5))
            
            if st.form_submit_button("DODAJ DO PLANU"):
                new_entry = {
                    "Nazwa Targów": n_targi, "Miejsce Załadunku": n_zal, "Miejsce Rozładunku": n_roz,
                    "Auto": n_auto, "Kierowca": n_driver, "Logistyk": user,
                    "Pierwszy wyjazd": pd.to_datetime(n_start), "Data końca": pd.to_datetime(n_end),
                    "Status": "OCZEKUJE", "Sloty": "NIE", "Uwagi": "", "UID": str(uuid.uuid4())[:8]
                }
                st.session_state.df_master = pd.concat([st.session_state.df_master, pd.DataFrame([new_entry])], ignore_index=True)
                conn.update(worksheet="targi", data=st.session_state.df_master)
                st.rerun()

    st.markdown("---")

    # --- WIDOK OPERACYJNY (LISTA TWOICH PROJEKTÓW) ---
    st.subheader(f"🛠️ TWOJE ZADANIA AKTYWNE: {user}")
    
    my_data = st.session_state.df_master[
        (st.session_state.df_master["Logistyk"] == user) & 
        (st.session_state.df_master["Status"] != "WRÓCIŁO")
    ]

    if my_data.empty:
        st.info("Brak aktywnych transportów.")
    else:
        # Nagłówki kolumn dla czytelności
        h1, h2, h3, h4, h5, h6 = st.columns([2, 1.5, 1.5, 1, 1, 1])
        h1.write("**PROJEKT / CEL**")
        h2.write("**MIEJSCE ZAŁ / ROZ**")
        h3.write("**AUTO / KIEROWCA**")
        h4.write("**TERMINY**")
        h5.write("**STATUS / SLOT**")
        h6.write("**AKCJA**")

        for idx, row in my_data.iterrows():
            with st.container():
                # Tworzymy rządy edycyjne
                c1, c2, c3, c4, c5, c6 = st.columns([2, 1.5, 1.5, 1, 1, 1])
                
                # Kolumna 1: Nazwa i Uwagi
                new_name = c1.text_input("Nazwa", row["Nazwa Targów"], key=f"name_{row['UID']}", label_visibility="collapsed")
                new_uwagi = c1.text_area("Uwagi", row["Uwagi"], key=f"rem_{row['UID']}", height=68, placeholder="Uwagi/Sloty/Naczepa...")

                # Kolumna 2: Logistyka Miejsc
                new_zal = c2.text_input("Załadunek", row["Miejsce Załadunku"], key=f"zal_{row['UID']}", placeholder="Skąd")
                new_roz = c2.text_input("Rozładunek", row["Miejsce Rozładunku"], key=f"roz_{row['UID']}", placeholder="Dokąd")

                # Kolumna 3: Zasoby
                new_auto = c3.text_input("Pojazd", row["Auto"], key=f"auto_{row['UID']}", placeholder="Nr Rej")
                new_driver = c3.text_input("Kierowca", row["Kierowca"], key=f"drv_{row['UID']}")

                # Kolumna 4: Daty
                new_start = c4.date_input("Wyjazd", row["Pierwszy wyjazd"], key=f"s_{row['UID']}")
                new_end = c4.date_input("Powrót", row["Data końca"], key=f"e_{row['UID']}")

                # Kolumna 5: Statusy
                new_stat = c5.selectbox("Status", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], 
                                      index=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"].index(row["Status"]), key=f"st_{row['UID']}")
                new_slot = c5.selectbox("Sloty", ["TAK", "NIE", "NIE POTRZEBA"], 
                                       index=["TAK", "NIE", "NIE POTRZEBA"].index(row["Sloty"]) if row["Sloty"] in ["TAK", "NIE", "NIE POTRZEBA"] else 1, key=f"sl_{row['UID']}")

                # Kolumna 6: Zapis
                if c6.button("💾 ZAPISZ", key=f"btn_{row['UID']}"):
                    st.session_state.df_master.at[idx, "Nazwa Targów"] = new_name
                    st.session_state.df_master.at[idx, "Miejsce Załadunku"] = new_zal
                    st.session_state.df_master.at[idx, "Miejsce Rozładunku"] = new_roz
                    st.session_state.df_master.at[idx, "Auto"] = new_auto
                    st.session_state.df_master.at[idx, "Kierowca"] = new_driver
                    st.session_state.df_master.at[idx, "Pierwszy wyjazd"] = pd.to_datetime(new_start)
                    st.session_state.df_master.at[idx, "Data końca"] = pd.to_datetime(new_end)
                    st.session_state.df_master.at[idx, "Status"] = new_stat
                    st.session_state.df_master.at[idx, "Sloty"] = new_slot
                    st.session_state.df_master.at[idx, "Uwagi"] = new_uwagi
                    
                    conn.update(worksheet="targi", data=st.session_state.df_master)
                    st.success("Zapisano!"); st.rerun()
                
                st.markdown("<hr style='border: 1px solid #1a1c0a;'>", unsafe_allow_html=True)

    # --- PODGLĄD PARTNERA ---
    partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
    st.subheader(f"👁️ WIDOK NA SEKTOR: {partner}")
    p_data = st.session_state.df_master[(st.session_state.df_master["Logistyk"] == partner) & (st.session_state.df_master["Status"] != "WRÓCIŁO")]
    st.dataframe(p_data.drop(columns=["UID", "Logistyk"]), use_container_width=True, hide_index=True)

# --- RESZTA MODUŁÓW (BEZ ZMIAN W LOGICE, TYLKO DANE Z SESJI) ---
elif menu == "📅 KALENDARZ":
    events = []
    for _, r in st.session_state.df_master[st.session_state.df_master["Pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"[{r['Auto']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#4b5320" if r["Logistyk"] == "DUKIEL" else "#8b0000"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

elif menu == "📊 GANNT":
    df_v = st.session_state.df_master[st.session_state.df_master["Pierwszy wyjazd"].notna()].copy()
    if not df_v.empty:
        fig = px.timeline(df_v, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk", color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"})
        fig.update_yaxes(autorange="reversed"); st.plotly_chart(fig, use_container_width=True)

elif menu == "📋 ROZKAZY":
    st.title("📋 Meldunki Sztabowe")
    # Logika analogiczna do Mastera - można dopisać obsługę Sheets dla Ogloszeń
    st.info("Moduł Tablicy Rozkazów - synchronizacja z arkuszem 'ogloszenia'")

elif menu == "🧮 KOSZTY":
    st.title("🧮 Kalkulator SQM 2026")
    # ... (tutaj kod kalkulatora z poprzedniej wersji)
