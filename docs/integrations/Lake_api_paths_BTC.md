docs/v3/LakeAPI/README_DATA_ACQUISITION.md                       # ✅ - Documentation
docs/v3/LakeAPI/RESUMABILITY_AND_BANDWIDTH.md                    # ✅ - Documentation
docs/LakeAPI_S3_DATA_Details.md                                  # ✅ - Schema & authentication

.lake_cache/                                                     # ✅ - Cached inventory (critical all lakeapi download scripts must use this location)


scripts/LakeAPI/
├── download_cryptolake_orderbook.py                             # ✅ - Orderbook downloader
└── download_with_lakeapi_chunked.py                             # ✅ - Chunked OHLCV downloader
└── lake_api_scanner.py                                          # ✅ - Path discovery & inventory
