# --- POPRAWKA ŁADOWANIA DANYCH (WSTAW TO W MIEJSCE POBIERANIA) ---
try:
    # Pobieramy dane i wymuszamy, by kolumny dat były czytane jako tekst/datetime
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    
    # KLUCZOWE: Konwersja dat na format datetime, błędy zamieniamy na NaT (puste)
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    
    # Upewniamy się, że kolumny tekstowe nie mają wartości NaN (Streamlit ich nie lubi w Selectbox)
    cols_to_fix = ["Status", "Logistyk", "Sloty", "Transport"]
    for col in cols_to_fix:
        if col in df_all.columns:
            df_all[col] = df_all[col].fillna("").astype(str)
except Exception as e:
    st.error(f"BŁĄD SYSTEMU: {e}")
    st.stop()

# --- EDYTOR PROJEKTÓW (POPRAWIONY) ---
st.subheader("📋 PROTOKÓŁ PROJEKTÓW")

config = {
    "Status": st.column_config.SelectboxColumn(
        "STATUS", 
        options=["", "OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], 
        required=True
    ),
    "Logistyk": st.column_config.SelectboxColumn(
        "REFERENT", 
        options=["", "DUKIEL", "KACZMAREK"], 
        required=True
    ),
    "Sloty": st.column_config.SelectboxColumn(
        "SLOTY", 
        options=["", "TAK", "NIE", "NIE POTRZEBA", "W TRAKCIE"]
    ),
    "Transport": st.column_config.SelectboxColumn(
        "TRANSPORT", 
        options=["", "WŁASNY BUS", "WŁASNY SOLO", "WŁASNY FTL", "ZEWNĘTRZNY"]
    ),
    "Pierwszy wyjazd": st.column_config.DateColumn(
        "WYJAZD",
        format="YYYY-MM-DD"
    ),
    "Data końca": st.column_config.DateColumn(
        "POWRÓT",
        format="YYYY-MM-DD"
    ),
    "Nazwa Targów": st.column_config.TextColumn("NAZWA TARGÓW")
}

# Edytor z zabezpieczeniem typów
edited_df = st.data_editor(
    df_all, 
    column_config=config, 
    use_container_width=True, 
    hide_index=True, 
    num_rows="dynamic",
    key="data_editor_main"
)
