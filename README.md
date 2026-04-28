# Eloverblik (Home Assistant)

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/mbw2001/eloverblik)](https://github.com/mbw2001/eloverblik/releases)
[![License](https://img.shields.io/github/license/mbw2001/eloverblik)](LICENSE)

A minimal Home Assistant integration for importing electricity consumption from Eloverblik.dk with full Energy Dashboard support.

---

## ✨ Features

- Full historical import on first run  
- Incremental updates afterwards  
- Hourly resolution (fallback to daily)  
- Native Energy Dashboard support  
- Automatic discovery of all metering points  
- One device + sensor per metering point  

---

## 📦 Installation (HACS)

1. Open HACS  
2. Go to Integrations  
3. Click ⋮ → Custom repositories  
4. Add:

   https://github.com/mbw2001/eloverblik  
   Category: Integration  

5. Install **Eloverblik**  
6. Restart Home Assistant  

---

## ⚙️ Configuration

Add the integration via:

**Settings → Devices & Services → Add Integration → Eloverblik**

You only need:

- Refresh token  

---

## 🔑 Create token

Create your token here:

https://eloverblik.dk/customer/tokens

---

## 🧠 How it works

- First run: imports all historical data  
- Afterwards: only new data is fetched  
- Uses Home Assistant long-term statistics  

Each metering point becomes:

- A device  
- A sensor (kWh, total increasing)  

---

## ⚡ Energy Dashboard

1. Go to Settings → Energy  
2. Add your Eloverblik sensor(s)  

---

## 📝 Notes

- Data is delayed 1–3 days  
- Integration handles this automatically  
- Multiple meters supported automatically  

---

## 🐛 Troubleshooting

**Cannot connect**
- Verify token is valid  

**No data**
- Wait after initial setup  
- Check logs  

---

## 📄 License

MIT