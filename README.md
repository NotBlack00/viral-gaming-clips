# VIRAL GAMING CLIPS

Editor automatico gratuito per registrazioni gaming, con priorità al riconoscimento di eventi Fortnite. Il PC Windows esegue analisi e rendering; il tablet o un altro PC controllano l'app da qualsiasi rete tramite un collegamento Internet temporaneo protetto da password.

## Download della versione Windows

1. Apri la pagina [Releases](https://github.com/NotBlack00/viral-gaming-clips/releases).
2. Scarica **VIRAL_GAMING_CLIPS_Windows.zip** dall'ultima release.
3. Estrai lo ZIP in una cartella del PC Windows.
4. Fai doppio clic su **VIRAL_GAMING_CLIPS.exe**.
5. Al primo avvio l'eseguibile prepara Python 3.12, crea un ambiente isolato e installa automaticamente le librerie necessarie.
6. Scarica automaticamente Cloudflare Tunnel e avvia il motore video sul PC.
7. Nella finestra nera compariranno un link Internet temporaneo e una password. Invia entrambi privatamente a chi deve controllare l'app.

Non chiudere la finestra nera: chiuderla interrompe il motore e il collegamento remoto. Per terminare, premi CTRL+C.

## Accesso da un'altra rete

- Il PC che elabora i video può essere a casa del tuo amico e il tablet in un'altra casa: non devono condividere la stessa rete Wi-Fi.
- Apri il link HTTPS temporaneo da Chrome sul tablet o da un altro PC.
- Inserisci la password temporanea mostrata nella finestra del PC ospitante.
- Il collegamento cambia quando l'app viene riavviata: usa il nuovo link e la nuova password.
- Non pubblicare link o password in chat pubbliche.

Il tunnel è fornito gratuitamente da Cloudflare Quick Tunnels e non richiede di configurare router o aprire porte. È un collegamento temporaneo, non un servizio sempre attivo né un dominio permanente.

## Selezionare i video sul PC ospitante

Nell'interfaccia seleziona **Il video è già sul PC Windows** e premi **SCEGLI VIDEO DAL PC**. La finestra di selezione file si apre sul computer che ospita l'app, anche se il comando è stato premuto dal tablet. Il video resta sul disco del PC e non viene caricato dal tablet.

In alternativa puoi usare il caricamento dal browser, ma per registrazioni da molti GB è preferibile il selettore locale. Il limite configurato per il caricamento via browser è 4 GB; la dimensione realmente gestibile dipende da RAM, disco, browser e connessione.

## Riconoscimento Fortnite

Il motore combina:
- OCR del testo HUD per cercare parole chiave del kill feed, eliminazioni, Knocked e Victory Royale (in inglese e alcune varianti italiane);
- variazioni del movimento tra fotogrammi;
- picchi di energia audio;
- punteggio combinato e selezione di finestre non sovrapposte.

L'OCR dipende dalla lingua, dalla posizione e dalla leggibilità dell'HUD. Non è un modello che comprende perfettamente il gameplay: i candidati vanno controllati nell'anteprima e alcuni eventi potrebbero non essere rilevati.

## Montaggio automatico

- Esporta ogni momento come MP4 separato.
- Esportazione verticale 9:16 a 1080×1920, adatta a TikTok e YouTube Shorts.
- Modalità sfondo sfocato che mantiene visibile l’intero gameplay.
- Modalità ritaglio verticale dinamico: analizza il movimento tra fotogrammi e sposta dolcemente l’inquadratura verso le aree più attive, con interpolazione per evitare scatti.
- Il tracciamento dinamico segue l’area d’azione, non riconosce ancora semanticamente il personaggio o il mirino; va verificato sulle registrazioni reali.
- Preset **Fortnite Hype**: zoom, breve shake e flash sul momento selezionato.
- Preset **Pulito**: composizione verticale senza impatto aggressivo.
- Sottotitoli italiani opzionali con evidenziazione parola per parola tramite Whisper.
- Download singolo o ZIP di tutte le clip.

## Requisiti e prestazioni

- Windows 10/11 a 64 bit e connessione Internet al primo avvio.
- L'eseguibile prepara automaticamente Python 3.12 e le dipendenze.
- SSD e RAM libera sufficienti. Per registrazioni di oltre un'ora è consigliato un PC con almeno 16 GB di RAM.
- Il rendering prova a usare NVIDIA NVENC se FFmpeg lo supporta; se l'encoder non parte, passa automaticamente a x264 su CPU.
- L'analisi di registrazioni di 2 ore può richiedere diversi minuti o più, in base a risoluzione, codec e hardware.
- Per sottotitoli Whisper, la prima esecuzione scarica il modello scelto.
- I file esportati sono salvati nella cartella `outputs` del progetto.

## Sicurezza e privacy

- L'interfaccia richiede una password casuale generata a ogni avvio.
- Il link del tunnel è temporaneo e non va condiviso pubblicamente.
- Il video selezionato dal disco resta sul PC ospitante. I dati dell'interfaccia e i download delle clip passano attraverso il collegamento Internet Cloudflare: non usare il tunnel per contenuti che non vuoi far transitare da un servizio terzo.
- Il PC ospitante deve restare acceso e connesso a Internet durante l'elaborazione.
- Il programma non apre porte sul router e non richiede che i dispositivi siano sulla stessa rete locale.
