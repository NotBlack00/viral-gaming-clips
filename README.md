# VIRAL GAMING CLIPS

Generatore gratuito di clip gaming verticali, con una prima interfaccia web utilizzabile da Android, iPhone e PC.

## Prova dal tablet Android (gratuita)

1. Apri [Streamlit Community Cloud](https://share.streamlit.io/) e accedi con GitHub.
2. Premi **Create app**.
3. Seleziona il repository **NotBlack00/viral-gaming-clips**, branch **main** e file **app.py**.
4. Premi **Deploy** e attendi l'installazione.
5. Apri il link `.streamlit.app` ottenuto con Chrome sul Lenovo Tab M11.

Il repository è pubblico e l'app può essere pubblicata gratuitamente su Streamlit Community Cloud. Il deploy deve essere avviato dal proprietario dell'account: non è stato avviato automaticamente.

## Limiti della demo gratuita online

- Video massimo: **100 MB**.
- Durata massima: **3 minuti**.
- Massimo 5 clip per elaborazione.
- Il video viene caricato sul server Streamlit per essere elaborato: non caricare video privati o sensibili.
- Le risorse gratuite del server sono limitate; elaborazioni pesanti potrebbero interrompersi.
- I file generati sono temporanei: scarica subito le clip.

Il video originale da circa 1,35 GB e oltre due ore **non è adatto a questa demo cloud gratuita**. Per quello servirà l'elaborazione locale su PC o un'infrastruttura diversa.

## Funzioni del prototipo

- Analisi dell'audio per individuare picchi di energia.
- Esportazione di clip MP4 separate.
- Formato verticale 9:16 con ritaglio centrale.
- Sottotitoli italiani opzionali tramite Whisper.

## Limiti tecnici

Il rilevamento audio è una prima euristica: un picco può corrispondere a un'esplosione o alla musica, non necessariamente a un momento virale. Il ritaglio è centrato e non segue ancora il giocatore o l'azione. I sottotitoli sono visualizzati in blocchi, non animati parola per parola.

## Avvio locale su Windows

1. Installa Python 3.11 o 3.12.
2. Scarica il repository come ZIP ed estrailo.
3. Avvia `Avvia_Viral_Gaming_Clips.bat`.
4. Apri l'indirizzo locale mostrato nel browser.

Per video lunghi è preferibile usare un PC con memoria e spazio liberi sufficienti.
