# Telegram Store Bot

Täisfunktsionaalne Telegrami pood krüptovaluutade maksega.

## Funktsioonid

### Kliendile:
- Toodete sirvimine
- Ostukorv
- Krüptovaluutade maksed (BTC, ETH, SOL, LTC, USDT)
- Allahindluskoodid
- EUR-USD konverter

### Adminile:
- Toodete haldus (pildid, koordinaadid)
- Sisu haldus
- Makse seaded
- Allahindluskoodid
- Statistika
- Maksete kinnitamine

## Paigaldus

1. Lae failid alla
2. Paigalda sõltuvused: `pip install -r requirements.txt`
3. Loo `.env` fail oma andmetega
4. Käivita: `python main.py`

## Oluline:

- **Pildid ja koordinaadid saadetakse kliendile alles peale makse kinnitamist**
- Admin peab käsitsi kinnitama iga makse
- Kliendid näevad toote detaile ilma piltideta enne makset
