# VIRAL GAMING CLIPS

Editor automatico gratuito per registrazioni gaming, con priorità al riconoscimento di eventi Fortnite. Il PC Windows esegue analisi e rendering; il tablet può essere usato come pannello di controllo via Wi-Fi.

## Architettura consigliata

- **PC Windows:** conserva il video, analizza i fotogrammi e crea le clip.
- **Lenovo Tab M11 / smartphone:** apre l'interfaccia nel browser sulla rete locale.
- **Nessun servizio cloud a pagamento:** i video non devono essere caricati su Streamlit Community Cloud.

## Avvio sul PC Windows

1. Scarica il repository con **Code → Download ZIP** ed estrailo sul PC.
2. Installa Python 3.11 o 3.12 da https://www.python.org/downloads/ (seleziona **Add Python to PATH**).
3. Fai doppio clic su `Avvia_Viral_Gaming_Clips.bat`.
4. Al primo avvio verranno installate le librerie gratuite; attendi il completamento.
5. Il terminale mostrerà l'indirizzo locale dell'app, normalmente `http://localhost:8501`.

## Apri il pannello dal Lenovo Tab M11

1. Collega PC e tablet alla **stessa rete Wi-Fi**.
2. Sul PC apri il Prompt dei comandi e digita `ipconfig`.
3. Cerca l'indirizzo **IPv4** della scheda Wi-Fi, ad esempio `192.168.1.25`.
4. Sul tablet apri Chrome e visita `http://192.168.1.25:8501`, sostituendo l'esempio con l'IP reale del PC.
5. Se Windows Firewall chiede l'autorizzazione, consenti l'accesso sulle reti private.

Non usare il vecchio link `.streamlit.app` per video pesanti: quello è un servizio cloud remoto e non usa la potenza del tuo PC.

## Come elaborare registrazioni grandi

Nell'interfaccia seleziona **Il video è già sul PC Windows** e premi **SCEGLI VIDEO DAL PC**. La finestra di selezione file si aprirà sul computer Windows anche se hai premuto il pulsante dal tablet. Scegli la registrazione Fortnite.

Così il video non viene trasferito dal tablet: il motore lo legge direttamente dal disco del PC. In alternativa puoi caricare un file dal dispositivo, ma per registrazioni da molti GB è preferibile usare il selettore locale.

Il limite configurato per il caricamento via browser è 4 GB; la dimensione realmente gestibile dipende da RAM, disco, browser e rete. Per video molto lunghi usa il percorso locale sul PC.

## Riconoscimento Fortnite

Il motore combina:
- OCR del testo HUD per cercare parole chiave del kill feed, eliminazioni, Knocked e Victory Royale (in inglese e alcune varianti italiane);
- variazioni del movimento tra fotogrammi;
- picchi di energia audio;
- punteggio combinato e selezione di finestre non sovrapposte.

L'OCR dipende dalla lingua, dalla posizione e dalla leggibilità dell'HUD. Non è un modello che comprende perfettamente il gameplay: i candidati vanno controllati nell'anteprima e alcuni eventi potrebbero non essere rilevati.

## Montaggio automatico

- Esporta ogni momento come MP4 separato.
- Composizione verticale 9:16 con gameplay intero e sfondo sfocato.
- Preset **Fortnite Hype**: zoom, breve shake e flash sul momento selezionato.
- Preset **Pulito**: composizione verticale senza impatto aggressivo.
- Sottotitoli italiani opzionali con evidenziazione parola per parola tramite Whisper.
- Download singolo o ZIP di tutte le clip.

## Requisiti e limiti

- Windows 10/11, Python 3.11 o 3.12.
- SSD e RAM libera sufficienti. Per registrazioni di oltre un'ora è consigliato un PC con almeno 16 GB di RAM.
- Il rendering usa FFmpeg e CPU; non è garantito che sfrutti la GPU NVIDIA.
- L'analisi di registrazioni di 2 ore può richiedere diversi minuti o più, in base a risoluzione, codec e hardware.
- Per sottotitoli Whisper, la prima esecuzione scarica il modello scelto.
- I file esportati sono salvati nella cartella `outputs` del progetto.

## Privacy

Quando usi il percorso locale, il video resta sul disco del PC. Se usi il caricamento browser dalla rete locale, il file viene trasferito al PC attraverso la tua rete Wi-Fi. Non caricare registrazioni private su link cloud pubblici.
