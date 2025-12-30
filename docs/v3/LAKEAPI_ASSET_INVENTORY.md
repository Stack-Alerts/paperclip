# LakeAPI Asset Inventory - V3 Migration
## Critical Infrastructure for Historical Data Acquisition

**Date:** December 30, 2025  
**Status:** Asset Preservation Plan  
**Priority:** HIGH - Critical for 6-year data management

---

## Executive Summary

LakeAPI infrastructure is **CRITICAL** and must be preserved in V3 migration. This represents our connection to historical BTC data worth $100K+ in value (6 years of orderbook, funding, liquidations, and OHLCV data).

---

## LakeAPI Files to Preserve

### Primary Scripts (✅ MUST KEEP)

#### Active Production Scripts
```
scripts/lake_api_scanner.py                              # ✅ KEEP - Path discovery & inventory
scripts/Lake_api_paths_BTC.md                            # ✅ KEEP - S3 path documentation
scripts/.lake_cache/                                     # ✅ KEEP - Cached inventory
└── lake_inventory.json                                  # ✅ KEEP - Path cache

scripts/data_download/
├── download_cryptolake_orderbook.py                     # ✅ KEEP - Orderbook downloader
└── download_with_lakeapi_chunked.py                     # ✅ KEEP - Chunked OHLCV downloader

docs/
└── LakeAPI_S3_DATA_Details.md                           # ✅ KEEP - Schema & authentication
```

#### Archived Scripts (⚠️ KEEP for Reference)
```
scripts/archived/
├── explore_cryptolake_structure.py                      # ⚠️ ARCHIVE - Historical reference
├── check_cryptolake_availability.py                     # ⚠️ ARCHIVE - Validation tool
├── test_lakeapi_tables.py                               # ⚠️ ARCHIVE - Testing
├── download_with_lakeapi.py                             # ⚠️ ARCHIVE - Legacy downloader
└── download_cryptolake_api.py                           # ⚠️ ARCHIVE - Original downloader
```

---

## Data Types from LakeAPI

### What We Have (6 Years Historical)

1. **OHLCV Data**
   - Location: `data/raw/btc_usdt_*m.parquet`
   - Timeframes: 1m, 5m, 15m, 1h, 4h, 1d
   - Size: ~100GB
   - Source: LakeAPI S3

2. **Orderbook Snapshots**
   - Location: `data/raw/orderbook_*.parquet`
   - Depth: Top 20-50 levels
   - Frequency: Varies by timeframe
   - Size: ~200GB
   - **UNIQUE VALUE:** Rare historical orderbook data

3. **Funding Rates**
   - Location: `data/raw/funding_*.parquet`
   - Exchange: Binance Futures
   - Frequency: 8-hour intervals
   - Size: ~1GB

4. **Liquidations**
   - Location: `data/raw/liquidations_*.parquet`
   - Type: Perpetual futures
   - Frequency: Event-based
   - Size: ~5GB

5. **Open Interest**
   - Location: `data/raw/open_interest_*.parquet`
   - Granularity: Per-exchange
   - Frequency: Varies
   - Size: ~2GB

**Total Data Value:** ~308GB of institutional-grade historical data

---

## V3 Migration Plan for LakeAPI

### Phase 1: Asset Preservation (Day 1)

**Task List:**
- [ ] Inventory all LakeAPI files
- [ ] Document S3 paths and credentials
- [ ] Verify AWS credentials still valid
- [ ] Test LakeAPI connectivity
- [ ] Check data freshness (last update dates)
- [ ] Document any API changes since last use

### Phase 2: Data Verification (Day 15)

**Task List:**
- [ ] Verify data integrity (checksums)
- [ ] Check for data gaps
- [ ] Validate data formats (parquet schema)
- [ ] Test data loading in VectorBT
- [ ] Document data quality issues
- [ ] Create data validation report

### Phase 3: Integration Testing (Day 16)

**Task List:**
- [ ] Test orderbook data access in V3
- [ ] Test funding rate data access
- [ ] Test liquidation data access
- [ ] Test open interest data access
- [ ] Create data loader utilities for V3
- [ ] Document data access patterns

### Phase 4: Automation (Day 17)

**Task List:**
- [ ] Create automated data update scripts
- [ ] Set up  cron jobs for daily updates
- [ ] Add data quality checks
- [ ] Create monitoring for data freshness
- [ ] Document update procedures

---

## V3 Project Structure (LakeAPI Integration)

```
BTC_Engine_v3/
├── scripts/
│   ├── lakeapi/                          # NEW: Centralized LakeAPI utilities
│   │   ├── scanner.py                    # MIGRATED: lake_api_scanner.py
│   │   ├── downloader.py                 # MIGRATED: download_with_lakeapi_chunked.py
│   │   ├── orderbook_downloader.py       # MIGRATED: download_cryptolake_orderbook.py
│   │   ├── config.py                     # NEW: LakeAPI configuration
│   │   └── cache/                        # MIGRATED: .lake_cache/
│   │       └── lake_inventory.json
│   │
│   ├── data_download/                    # Other downloaders
│   │   ├── download_binance_spot.py
│   │   └── (other exchange downloaders)
│   │
│   └── data_validation/                  # NEW: Data quality checks
│       ├── verify_integrity.py
│       └── check_freshness.py
│
├── data/                                 # PRESERVED FROM V2
│   ├── raw/                              # All LakeAPI data here
│   │   ├── btc_usdt_15m.parquet
│   │   ├── orderbook_*.parquet
│   │   ├── funding_*.parquet
│   │   ├── liquidations_*.parquet
│   │   └── open_interest_*.parquet
│   └── ...
│
├── docs/
│   ├── v3/
│   │   ├── LAKEAPI_GUIDE.md              # NEW: V3-specific guide
│   │   └── DATA_SCHEMA.md                # NEW: Data format docs
│   └── archive_v2/
│       ├── LakeAPI_S3_DATA_Details.md    # PRESERVED: Reference
│       └── Lake_api_paths_BTC.md         # PRESERVED: Path reference
│
└── .env                                  # AWS credentials
    AWS_ACCESS_KEY_ID=***
    AWS_SECRET_ACCESS_KEY=***
    LAKEAPI_BUCKET=***
```

---

## Critical Configuration

### AWS Credentials (SECURE)

**Location:** `.env` file (never commit to git)

```bash
# LakeAPI S3 Access
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
LAKEAPI_BUCKET=cryptolake-historical-data
LAKEAPI_REGION=us-east-1
```

### S3 Paths (From Lake_api_paths_BTC.md)

**Common Patterns:**
```
s3://cryptolake-historical-data/binance/spot/btc_usdt/ohlcv/1m/
s3://cryptolake-historical-data/binance/spot/btc_usdt/orderbook/
s3://cryptolake-historical-data/binance/futures/btc_usdt/funding/
s3://cryptolake-historical-data/binance/futures/btc_usdt/liquidations/
s3://cryptolake-historical-data/binance/futures/btc_usdt/open_interest/
```

---

## Data Update Procedures

### Daily Updates (Automated)

```bash
# Cron job (runs daily at 2 AM)
0 2 * * * python3 ~/BTC_Engine_v3/scripts/lakeapi/downloader.py --update-daily

# Manual update (when needed)
python3 scripts/lakeapi/downloader.py --start-date 2025-12-29 --end-date 2025-12-30
```

### Orderbook Updates (Weekly)

```bash
# Weekly orderbook snapshot download (Sundays, 3 AM)
0 3 * * 0 python3 ~/BTC_Engine_v3/scripts/lakeapi/orderbook_downloader.py --update-weekly
```

---

## Testing Checklist

### Pre-Migration Testing (V2)

- [ ] Verify all LakeAPI scripts run successfully
- [ ] Download 1 day of test data
- [ ] Verify data schema matches expectations
- [ ] Document any API changes or deprecations
- [ ] Check AWS billing (ensure no surprise costs)

### Post-Migration Testing (V3)

- [ ] Test LakeAPI connectivity from V3
- [ ] Load historical data into VectorBT
- [ ] Verify data formats compatible
- [ ] Test orderbook data in pattern detectors
- [ ] Benchmark data loading speed
- [ ] Verify no data corruption during migration

---

## Risk Assessment

### High Risk Items

1. **AWS Credentials Expiration**
   - Risk: Cannot access historical data
   - Mitigation: Verify credentials before migration
   - Backup: Have alternative data sources ready

2. **S3 Path Changes**
   - Risk: Scripts break if LakeAPI changes paths
   - Mitigation: Cache known paths, have fallback discovery
   - Backup: Contact LakeAPI support for updates

3. **Data Corruption During Migration**
   - Risk: Lose historical data
   - Mitigation: Checksums before/after
   - Backup: Keep V2 data intact until verified

### Medium Risk Items

1. **API Rate Limits**
   - Risk: Throttled or blocked downloads
   - Mitigation: Implement rate limiting in code
   - Backup: Download in smaller chunks

2. **Storage Costs**
   - Risk: AWS S3 costs increase
   - Mitigation: Monitor usage, optimize downloads
   - Backup: Budget for data storage

---

## Success Criteria

**LakeAPI Migration is Complete When:**

- [ ] All LakeAPI scripts migrated to V3
- [ ] AWS credentials configured and tested
- [ ] All historical data accessible in V3
- [ ] Data loading tested with VectorBT
- [ ] Automated update scripts running
- [ ] Data quality checks passing
- [ ] Documentation updated
- [ ] Team trained on V3 data access

---

## Contacts & Resources

### LakeAPI Support
- Website: https://cryptolake.com
- Support: support@cryptolake.com
- Documentation: https://docs.cryptolake.com

### Internal
- AWS Account Owner: [Your Team]
- Data Engineer: [Responsible Person]
- Migration Lead: [Project Manager]

---

## Appendix: File Locations

### V2 Locations (Current)
```
/home/sirrus/projects/BTC_Engine_LLM/scripts/lake_api_scanner.py
/home/sirrus/projects/BTC_Engine_LLM/scripts/Lake_api_paths_BTC.md
/home/sirrus/projects/BTC_Engine_LLM/scripts/.lake_cache/
/home/sirrus/projects/BTC_Engine_LLM/scripts/data_download/download_cryptolake_orderbook.py
/home/sirrus/projects/BTC_Engine_LLM/scripts/data_download/download_with_lakeapi_chunked.py
/home/sirrus/projects/BTC_Engine_LLM/docs/LakeAPI_S3_DATA_Details.md
/home/sirrus/projects/BTC_Engine_LLM/data/raw/
```

### V3 Locations (Target)
```
/home/sirrus/projects/BTC_Engine_v3/scripts/lakeapi/
/home/sirrus/projects/BTC_Engine_v3/data/raw/ (symlink or copy from V2)
/home/sirrus/projects/BTC_Engine_v3/docs/v3/LAKEAPI_GUIDE.md
/home/sirrus/projects/BTC_Engine_v3/.env
```

---

**Document Owner:** BTC_Engine Development Team  
**Last Updated:** December 30, 2025  
**Status:** Ready for Migration  
**Priority:** CRITICAL - Do Not Lose This Data!
