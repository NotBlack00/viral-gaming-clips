# VIRAL GAMING CLIPS

Generatore gratuito di clip gaming verticali a partire da registrazioni lunghe.

## Avvio semplice su Windows

1. Installa Python 3.11 (o 3.12) da https://www.python.org/downloads/ e seleziona "Add Python to PATH".
2. Scarica il repository con Code → Download ZIP ed estrai la cartella.
3. Fai doppio clic su Avvia_Viral_Gaming_Clips.bat.
4. Attendi l'installazione: si aprirà l'interfaccia nel browser.
5. Seleziona il video, scegli durata e numero di clip, poi premi "Trova i momenti migliori e crea le clip".

L'elaborazione avviene sul PC: non serve Render e non viene richiesto un servizio cloud. Per video molto grandi è preferibile avviare l'app su un PC Windows, non da telefono.

## Funzioni della prima versione

- Analisi dell'audio per individuare picchi di energia e momenti candidati.
- Esportazione di clip MP4 separate.
- Formato verticale 9:16 con ritaglio centrale automatico.
- Sottotitoli italiani opzionali tramite Whisper locale (tiny, base o small).
- File esportati nella cartella outputs.

## Limiti

Il rilevamento audio è una prima euristica: un picco può corrispondere a un'esplosione o alla musica, non necessariamente a un momento virale. Il ritaglio è centrato e non segue ancora automaticamente il giocatore o l'azione. I sottotitoli sono trascritti e visualizzati in blocchi, non animati parola per parola. Non è ancora un sistema di selezione semantica delle kill o delle battute.

## Requisiti

- Windows 10/11 e Python 3.11 o 3.12.
- Spazio libero per il video sorgente, l'audio temporaneo e le clip.
- Per video lunghi è consigliato un PC con almeno 16 GB di RAM.

## Privacy e costi

Strumenti gratuiti/open source e analisi locale. Il modello Whisper viene scaricato al primo utilizzo dei sottotitoli. Usa solo video per cui hai i diritti o l'autorizzazione del proprietario.
