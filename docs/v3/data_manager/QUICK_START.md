# DATA MANAGER - QUICK START GUIDE

## 🚀 Get Started in 3 Steps

### Step 1: Setup Credentials

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your LakeAPI credentials:
```bash
# Get credentials from https://cryptolake.com
LAKEAPI_KEY=your_access_key_here
LAKEAPI_SECRET=your_secret_key_here
```

3. Verify credentials loaded:
```bash
python -c "from src.data_manager.config import print_config_summary; print_config_summary()"
```

### Step 2: Check Current Status

```bash
# Check what data you already have
python scripts/LakeAPI/download_synchronize_data.py --status

# Check LakeAPI usage (300GB/month limit)
python scripts/LakeAPI/download_synchronize_data.py --usage
```

### Step 3: Download Data

```bash
# Download trades from Nov 2024 to now
python scripts/LakeAPI/download_synchronize_data.py \
    --data-type trades \
    --start-date 2024-11-01

# Download all data types from Nov 2024
python scripts/LakeAPI/download_synchronize_data.py \
    --all \
    --start-date 2024-11-01

# Update current month only (refresh latest data)
python scripts/LakeAPI/download_synchronize_data.py --update-current
```

---

## 📊 Common Commands

### Check Data Freshness
```bash
# Check if data needs updating
python scripts/LakeAPI/download_synchronize_data.py --check-freshness
```

### View Usage Statistics
```bash
# See how much bandwidth used this month
python scripts/LakeAPI/download_synchronize_data.py --usage
```

### Sync Specific Data Type
```bash
# Sync only liquidations
python scripts/LakeAPI/download_synchronize_data.py \
    --data-type liquidations \
    --start-date 2024-11-01
```

### Force Re-download
```bash
# Re-download existing data (use sparingly!)
python scripts/LakeAPI/download_synchronize_data.py \
    --data-type trades \
    --start-date 2024-12-01 \
    --end-date 2024-12-31 \
    --force
```

---

## 🔍 Understanding the Output

### Download Process
```
📥 Downloading trades 2024-12...
   Period: 2024-12-01 to 2024-12-31
✅ Downloaded 1,523,891 rows, 245.3 MB
```

### Usage Tracking
```
LakeAPI Usage (2026-01):
  Used: 45.3 GB / 300 GB (15.1%)
  Remaining: 254.7 GB
  Downloads: 23
```

### Sync Status
```
✅ trades          
   Months: 15
   Range: 2023-10 to 2026-01
   Last sync: 2026-01-08T12:30:00
```

---

## ⚠️ Important Notes

### 300GB Monthly Limit
- LakeAPI has a 300GB/month transfer limit
- Usage tracker automatically prevents exceeding limit
- Resets at start of each month
- Check usage frequently: `--usage`

### Incremental Downloads
- Script only downloads **missing months**
- Skips existing files automatically
- Use `--force` only when necessary
- Saves bandwidth and time

### Current Month Updates
- Current month data updated automatically
- Gets latest ticks/trades
- Use `--update-current` for manual refresh
- Recommended: Run daily for fresh data

### Data Location
```
data/raw/
├── trades/
│   └── BTC-USDT_trades_2024-12.parquet
├── liquidations/
│   └── BTC-USDT_liquidations_2024-12.parquet
├── funding/
├── open_interest/
└── orderbook/
```

---

## 🛠️ Troubleshooting

### "Credentials not found in .env"
**Solution:** Create `.env` file with your LakeAPI credentials

### "Download would exceed limit"
**Solution:** Wait for next month or delete unneeded files

### "No data returned"
**Possible causes:**
- Month is in the future
- No data available for that period
- Network issue

### Permission Denied
**Solution:** Make script executable
```bash
chmod +x scripts/LakeAPI/download_synchronize_data.py
```

---

## 📖 Next Steps

1. ✅ **Download Historical Data**
   - Start with trades (most important)
   - Add liquidations for signals
   - Add funding/OI for analysis

2. ⏭️ **Aggregate to Bars** (Coming soon)
   - Convert ticks to OHLCV bars
   - Multiple timeframes (5min, 15min, 1h, etc.)
   - Required for NautilusTrader

3. ⏭️ **Validation** (Coming soon)
   - Verify data integrity
   - Check for gaps
   - Quality assurance

4. ⏭️ **NautilusTrader Integration** (Coming soon)
   - Convert to Nautilus format
   - Ready for backtesting
   - Strategy development

---

## 💡 Pro Tips

### Bandwidth Management
1. Start with small date range
2. Check usage after each download
3. Download most important data first (trades)
4. Less important data last (orderbook is huge!)

### Automation
```bash
# Add to cron for daily updates
0 1 * * * /path/to/venv/bin/python /path/to/scripts/LakeAPI/download_synchronize_data.py --update-current
```

### Monitoring
```bash
# Create simple monitoring script
#!/bin/bash
python scripts/LakeAPI/download_synchronize_data.py --check-freshness
python scripts/LakeAPI/download_synchronize_data.py --usage
```

---

## 📞 Need Help?

- Documentation: `/docs/v3/data_manager/`
- Plan: `INSTITUTIONAL_DATA_MANAGEMENT_PLAN.md`
- Architecture: `DIRECTORY_STRUCTURE.md`
- Testing: `TESTING_FRAMEWORK.md`

---

**Ready to download data?** Start with Step 1 above! 🚀