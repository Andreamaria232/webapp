import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
import dropbox
from io import BytesIO
import random

DROPBOX_PATH = "/filefumo.xlsx" 

dbx = dropbox.Dropbox(
    oauth2_refresh_token=os.getenv("DROPBOX_REFRESH_TOKEN"),
    app_key=os.getenv("DROPBOX_APP_KEY"),
    app_secret=os.getenv("DROPBOX_APP_SECRET")
)

def get_excel_file():
    try:
        metadata, res = dbx.files_download(DROPBOX_PATH)
        return BytesIO(res.content)
    except dropbox.exceptions.ApiError as e:
        # Se il file non esiste ancora
        return BytesIO()

def load_data():
    try:
        data = pd.read_excel(get_excel_file())
    except:
        data = pd.DataFrame(columns=["email", "data", "stress", "sigarette_stimate", "nicotina_totale"])
    return data

#salva aggiungendo i nuovi dati, senza sovrascrivere quelli esistenti
def save_data(new_data):
    existing_data = load_data()

    # Rimuove duplicati per email + data (opzionale)
    existing_data = existing_data[~(
        (existing_data["email"] == new_data.iloc[0]["email"]) &
        (existing_data["data"] == new_data.iloc[0]["data"])
    )]

    updated_df = pd.concat([existing_data, new_data], ignore_index=True)
    output = BytesIO()
    updated_df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    dbx.files_upload(output.read(), DROPBOX_PATH, mode=dropbox.files.WriteMode.overwrite)

def delete_file():
    try:
        dbx.files_delete_v2(DROPBOX_PATH)
        st.success("File cancellato con successo da Dropbox.")
    except dropbox.exceptions.ApiError:
        st.warning("Nessun file da cancellare.")

# Layout iniziale della pagina web tramite streamlit
st.set_page_config(page_title="Monitoraggio Fumo", layout="wide")
st.title("Monitoraggio Quotidiano del Fumo")

email = st.text_input("Inserisci la tua email").strip().lower()

if not email or "@" not in email:
    st.warning("Per favore inserisci una email valida per continuare.")
    st.stop()

# Permetto al sistema di rilevare se ci sono dei dati salvati
df = load_data()

df = df[df["email"] == email]  # Mostra solo i dati dell’utente attuale

# Inserimento nuovi dati
st.header("Inserisci i dati della giornata")

scelta_file = st.radio("Vuoi caricare un file della giornata?", ["Sì", "No"], horizontal=True)

# Caricamento multiplo
uploaded_files = st.file_uploader("Carica uno o più file CSV", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    st.write(f"Hai caricato **{len(uploaded_files)}** file.")
    
    if st.button("Salva tutti automaticamente"):
        # Punto di partenza: 1 gennaio dell’anno corrente
        start_date = datetime(datetime.now().year, 1, 1)
        
        dati_da_salvare = []

        for i, uploaded_file in enumerate(uploaded_files):
            try:
                # Leggi file
                data_grezzi = pd.read_csv(uploaded_file)
                data_grezzi['tempo di lettura'] = pd.to_datetime(data_grezzi['tempo di lettura'])

                # Parametri fissi
                soglia = 0.8
                nicotina_s = 0.3
                data_grezzi['LED binario'] = data_grezzi['stato del LED'].apply(lambda x: 1 if x > soglia else 0)

                # Calcoli
                n_on = data_grezzi[data_grezzi['LED binario'] == 1].shape[0]
                nicotina_totale = n_on * nicotina_s
                data_selezionata = start_date + timedelta(days=i)  # Data univoca per ogni file

                # Randomizzazione
                stress = random.choice(["Sì", "No"])
                sig_stimate = random.randint(13, 20) if n_on > 0 else 0

                nuova_riga = {
                    "email" : email,
                    "data": data_selezionata.date(),
                    "stress": stress,
                    "sigarette_stimate": sig_stimate,
                    "nicotina_totale": nicotina_totale
                }

                

                # Nel ciclo:
                nuova_riga["email"] = email  # Aggiungi email
                dati_da_salvare.append(nuova_riga)
            except Exception as e:
                st.error(f"Errore nel file {uploaded_file.name}: {str(e)}")
                
        # Fuori dal ciclo:
        if dati_da_salvare:
            nuovo_df = pd.DataFrame(dati_da_salvare)
            save_data(nuovo_df)
            
if not df.empty:
        st.header("Consumo di nicotina nel tempo")
        # Scelta modalità di visualizzazione
        modalita = st.radio("Modalità di visualizzazione", ["Settimanale (lun-dom)", "Mensile"], horizontal=True)

        df['data'] = pd.to_datetime(df['data'])

        # Set indice per semplificare raggruppamenti
        df.set_index('data', inplace=True)

        # Ordinamento cronologico
        df.sort_index(inplace=True)

        # Identificazione settimane o mesi disponibili
        if modalita == "Settimanale (lun-dom)":
            # Raggruppa per settimana (lunedì come inizio)
            df['settimana'] = df.index.to_period('W-MON')
            settimane = sorted(df['settimana'].unique())
            idx = st.session_state.get("settimana_idx", len(settimane) - 1)

            col_1, col_2, col_3 = st.columns([1, 1, 6])
            with col_1:
                if st.button("← Indietro") and idx > 0:
                    idx -= 1
            with col_2:
                if st.button("→ Avanti") and idx < len(settimane) - 1:
                    idx += 1

            st.session_state["settimana_idx"] = idx
            settimana_selezionata = settimane[idx]
            st.subheader(f"Settimana: {settimana_selezionata.start_time.strftime('%d %b')} - {settimana_selezionata.end_time.strftime('%d %b')}")

            df_periodo = df[df['settimana'] == settimana_selezionata]

            # Reset dell'indice per il grafico
            df_periodo = df_periodo.reset_index()
            df_periodo['giorno'] = df_periodo['data'].dt.strftime('%d-%m')

            # Grafico settimanale
            fig, ax = plt.subplots(figsize=(9, 4))
            ax.plot(df_periodo['giorno'], df_periodo['nicotina_totale'], marker='x', alpha=0.5, color='blue', label="Nicotina Totale")

            for i, row in df_periodo.iterrows():
                if row['nicotina_totale'] > 0:
                    ax.annotate(f"{int(row['sigarette_stimate'])}", (row['giorno'], row['nicotina_totale']),
                                textcoords="offset points", xytext=(0, 5), ha='center', fontsize=8, color='darkgreen')

            stress_mask = df_periodo['stress'] == "Sì"
            ax.scatter(df_periodo.loc[stress_mask, 'giorno'], df_periodo.loc[stress_mask, 'nicotina_totale'],
                       color='red', label="Giorni Stressanti")

            media_nicotina = df_periodo['nicotina_totale'].mean()
            ax.axhline(media_nicotina, color='gray', linestyle='--', label=f"Media: {media_nicotina:.2f} mg")

            ax.set_xlabel("Giorno")
            ax.set_ylabel("Nicotina Totale (mg)")
            ax.set_title("Consumo di Nicotina - Periodo selezionato")
            ax.legend()
            st.pyplot(fig)

        else:
            # Raggruppa per mese
            df['mese'] = df.index.to_period('M')
            mesi = sorted(df['mese'].unique())
            idx = st.session_state.get("mese_idx", len(mesi) - 1)

            col_1, col_2, col_3 = st.columns([1, 1, 6])
            with col_1:
                if st.button("← Indietro") and idx > 0:
                    idx -= 1
            with col_2:
                if st.button("→ Avanti") and idx < len(mesi) - 1:
                    idx += 1

            st.session_state["mese_idx"] = idx
            mese_selezionato = mesi[idx]
            st.subheader(f"Mese: {mese_selezionato.start_time.strftime('%B %Y')}")

            df_periodo = df[df['mese'] == mese_selezionato]

            # Reset dell'indice per il grafico
            df_periodo = df_periodo.reset_index()
            df_periodo['giorno'] = df_periodo['data'].dt.strftime('%d-%m')

            # Grafico mensile
            fig, ax = plt.subplots(figsize=( 9, 4))
            ax.plot(df_periodo['giorno'], df_periodo['nicotina_totale'], marker='x', alpha=0.5, color='blue', label="Nicotina Totale")

            for i, row in df_periodo.iterrows():
                if row['nicotina_totale'] > 0:
                    ax.annotate(f"{int(row['sigarette_stimate'])}", (row['giorno'], row['nicotina_totale']),
                                textcoords="offset points", xytext=(0, 5), ha='center', fontsize=8, color='darkgreen')

            stress_mask = df_periodo['stress'] == "Sì"
            ax.scatter(df_periodo.loc[stress_mask, 'giorno'], df_periodo.loc[stress_mask, 'nicotina_totale'],
                       color='red', label="Giorni Stressanti")

            media_nicotina = df_periodo['nicotina_totale'].mean()
            ax.axhline(media_nicotina, color='gray', linestyle='--', label=f"Media: {media_nicotina:.2f} mg")

            ax.set_xlabel("Giorno")
            ax.set_ylabel("Nicotina Totale (mg)")
            ax.set_title("Consumo di Nicotina - Periodo selezionato")
            ax.legend()

            # Riduci numero di etichette asse X solo qui
            tick_interval = 7
            ax.set_xticks(df_periodo['giorno'][::tick_interval])
            plt.setp(ax.get_xticklabels(), ha='right')

            st.pyplot(fig)

        somma_nicotina = df_periodo['nicotina_totale'].sum()
        somma_sigarette = df_periodo['sigarette_stimate'].sum()
        st.markdown(f"**Media nicotina assunta nel periodo selezionato:** {media_nicotina:.2f} mg")
        st.markdown(f"**Totale nicotina assunta nel periodo selezionato:** {somma_nicotina:.2f} mg")
        st.markdown(f"**Totale sigarette fumate nel periodo selezionato:** {somma_sigarette:.0f}")

