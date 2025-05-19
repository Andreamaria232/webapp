import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os
import json
import gspread
from google.oauth2.service_account import Credentials

print("VERSIONE AGGIORNATA - Questo dovrebbe essere il primo messaggio!")

# Legge le credenziali dalla variabile d'ambiente (Render)
creds_json = os.environ.get("GOOGLE_CREDS")

if not creds_json:
    raise ValueError("Errore: La variabile d'ambiente GOOGLE_CREDS non è impostata.")

try:
    creds_dict = json.loads(creds_json)
except json.JSONDecodeError as e:
    raise ValueError(f"Errore nel parsing delle credenziali JSON: {e}")

# Autenticazione con Google Sheets API
try:
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    print("Autenticazione riuscita!")
except Exception as e:
    raise ValueError(f"Errore di autenticazione: {e}")

# Collegamento al foglio Google Sheets
try:
    sheet = gc.open("DatiFumo").sheet1  # Assicurati che il nome sia esattamente quello del file su Google Sheets
    print("Accesso al foglio riuscito!")
except Exception as e:
    raise ValueError(f"Errore nell'accesso al foglio: {e}")

# Collegamento al foglio Google Sheets (devi scrivere il nome esatto del file)
sheet = gc.open("DatiFumo").sheet1  # ← qui inserisci il NOME ESATTO del file che contiene le risposte


def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def save_data(new_df):
    existing_records = sheet.get_all_records()
    existing_df = pd.DataFrame(existing_records)

    updated_df = pd.concat([existing_df, new_df], ignore_index=True)

    for i in range(len(new_df)):
        row = new_df.iloc[i].tolist()
        sheet.append_row(row)

def delete_file(file_path=None):
    sheet.clear()
    print("I dati su Google Sheets sono stati cancellati.")

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

if scelta_file == "Sì":
    uploaded_file = st.file_uploader("Carica il file CSV della giornata", type=["csv"])

    if uploaded_file: #Se scelgo di fare un upload del file si apre un ciclo if
        data_grezzi = pd.read_csv(uploaded_file)
        data_grezzi['tempo di lettura'] = pd.to_datetime(data_grezzi['tempo di lettura'])

        soglia = st.slider("Soglia per accensione LED", 0.0, 1.0, 0.8) #scelgo la soglia per il quale voglio "pulire" i dati dal rumore di fondo
        data_grezzi['LED binario'] = data_grezzi['stato del LED'].apply(lambda x: 1 if x > soglia else 0)

        # Selezione della data
        data_selezionata = None
        if st.checkbox("Voglio selezionare la data"):
            data_selezionata = st.date_input("Seleziona la data", min_value=datetime(2000, 1, 1))

        # Selezione stress
        stress = st.radio("Hai avuto una giornata stressante?", ["Non selezionato", "Sì", "No"])

        # Input sigarette
        sig_stimate = st.number_input("Quante sigarette pensi di aver fumato oggi?", min_value=0, max_value=100, value=0)
        
        #imput nicotina/s della sigaretta
        nicotina_s = st.number_input("Qual è la quantità di nicotina al secondo erogata dalla tua sigaretta?", min_value = 0.00, max_value = 100.00, value = 0.15)

        # Calcolo nicotina
        n_on = data_grezzi[data_grezzi['LED binario'] == 1].shape[0]
        nicotina_totale = n_on * nicotina_s

        # Controlli per salvataggio
        if data_selezionata and stress != "Non selezionato":
            if st.button("Salva nei dati storici"):
            # Aggiunta dei nuovi dati allo storico df
                nuova_riga = {
                "email": email,
                "data": data_selezionata,
                "stress": stress,
                "sigarette_stimate": sig_stimate,
                "nicotina_totale": nicotina_totale
                }
                df = pd.concat([df, pd.DataFrame([nuova_riga])], ignore_index=True)
                save_data(df)
                st.success(f"Dati del {data_selezionata} salvati correttamente!")
        else:
            st.warning("Seleziona una data e indica se la giornata è stata stressante per poter salvare.")
            
        col1, col2 = st.columns(2)
        
        with col1:

            # Grafico relativo al csv inserito
            st.subheader("Andamento della giornata")
            fig, ax = plt.subplots(figsize = (6, 4))
            ax.plot(data_grezzi['tempo di lettura'], data_grezzi['LED binario'], drawstyle='steps-post', color='black', linewidth = 1)
            ax.set_xlabel("Tempo", fontsize = 12)
            ax.set_ylabel("Stato del LED (0=spento, 1=acceso)", fontsize = 12)
            ax.tick_params(axis='both', labelsize=6)
            st.pyplot(fig)
        
        with col2:
            
            #Diagramma a torta per quantità di accensioni rilevate
            led_counts = data_grezzi['LED binario'].value_counts()
            st.markdown("### Utilizzo sigaretta")
            fig, ax = plt.subplots()
            ax.pie(led_counts, labels=['Spento', 'Acceso'], autopct='%1.1f%%', startangle=140, colors=['#D9534F', '#5BC0DE'])
            st.pyplot(fig)

#Grafico relativo alla quantità di nicotina nei diversi giorni
else:
    
    st.header("Inserimento manuale dei dati")
    
    #inserire la data
    data_selezionata = None
    if st.checkbox("Voglio selezionare la data"):
        data_selezionata = st.date_input("Seleziona la data", min_value=datetime(2000, 1, 1))

    # Selezione stress
    stress = st.radio("Hai avuto una giornata stressante?", ["Non selezionato", "Sì", "No"])

    # Calcolo nicotina manuale
    sig_stimate = st.number_input("Quante sigarette pensi di aver fumato oggi?", min_value=0, max_value=100, value=0)
    nicotina_per_sigaretta = st.number_input("Qual è la quantità di nicotina erogata dalla tua sigaretta?", min_value = 0.00, max_value = 100.00, value = 0.15)
    nicotina_totale = sig_stimate * nicotina_per_sigaretta
    st.info(f"Nicotina stimata: {nicotina_totale:.2f} mg (input manuale)")
    
    # Controlli per salvataggio
    if data_selezionata and stress != "Non selezionato":
        if st.button("Salva nei dati storici"):
        # Aggiunta dei nuovi dati allo storico df
            nuova_riga = {
            "email": email,
            "data": data_selezionata,
            "stress": stress,
            "sigarette_stimate": sig_stimate,
            "nicotina_totale": nicotina_totale
            }
            df = pd.concat([df, pd.DataFrame([nuova_riga])], ignore_index=True)
            save_data(df)
            st.success(f"Dati del {data_selezionata} salvati correttamente!")
    else:
        st.warning("Seleziona una data e indica se la giornata è stata stressante per poter salvare.")

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
        somma_sigarette = df_periodo['sig_stimate'].sum()
        st.markdown(f"**Media nicotina assunta nel periodo selezionato:** {media_nicotina:.2f} mg")
        st.markdown(f"**Totale nicotina assunta nel periodo selezionato:** {somma_nicotina:.2f} mg")
        st.markdown(f"**Totale sigarette fumate nel periodo selezionato:** {somma_sigarette:.0f}")
