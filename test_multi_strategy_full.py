"""Full-length test of the 11 non-trading strategies on 6720 bars (Mar-May)."""
import sys, json, time
from pathlib import Path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import pandas as pd
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.core.datetime import dt_to_unix_nanos
from src.optimizer_v3.core.multicore_backtest_engine import evaluate_chunk, ChunkData
import logging
logging.basicConfig(level=logging.WARNING)
for name in ['exit_debug','binding_debug','sl_check_debug','position_calc','tpsl_debug','wiring_config','wiring_test','wiring_debug']:
    logging.getLogger(name).setLevel(logging.ERROR)

BC = {"timeframe":"15m","starting_capital":10000,"risk_per_trade_pct":10,"min_risk_reward":1.2,"max_leverage":10,"max_bars_held":200,"tpsl_mode":"Fibonacci","sl_mode":"Static","confluence_threshold":40,"adaptive_sl":{"enabled":False}}

def load_bars():
    dfs = []
    for m in ["2026-03","2026-04","2026-05"]:
        p = ROOT/"data"/"binance"/m/f"BTCUSDT_PERP_15m_{m}.parquet"
        if p.exists(): dfs.append(pd.read_parquet(p))
    df = pd.concat(dfs).sort_values("timestamp").reset_index(drop=True)
    df = df[df["timestamp"] < "2026-05-10"]
    iid = InstrumentId(Symbol("BTC-USDT-PERP"), Venue("BINANCE"))
    bt = BarType(iid, BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST), AggregationSource.EXTERNAL)
    bars = []
    for _,r in df.iterrows():
        ts = dt_to_unix_nanos(pd.Timestamp(r["timestamp"]))
        bars.append(Bar(bt, Price(float(r["open"]),2), Price(float(r["high"]),2), Price(float(r["low"]),2), Price(float(r["close"]),2), Quantity(float(r["volume"]),8), ts, ts))
    return bars

def test(name, cfg, bars):
    side = "SHORT" if cfg.get("strategy_type")=="Bearish" else "LONG"
    try:
        t0 = time.time()
        r = evaluate_chunk(ChunkData(0,bars,0,len(bars),0), cfg, BC, side)
        e = time.time()-t0
        return {"name":name,"status":"OK" if r.trades else "NO_TRADES","trades":len(r.trades),"signals":r.signals_evaluated,"elapsed":round(e,1)}
    except Exception as ex:
        import traceback
        return {"name":name,"status":"CRASH","error":str(ex)[:100],"trace":traceback.format_exc()[-200:]}

bars = load_bars()
print(f"Loaded {len(bars)} bars")
results = []
for f in sorted((ROOT/"user_strategies").glob("*.json")):
    cfg = json.loads(f.read_text()); n=cfg.get("name",f.stem)
    results.append(test(n,cfg,bars))
for f in sorted((ROOT/"tests/strategies").glob("*.json")):
    cfg = json.loads(f.read_text()); n=cfg.get("name",f.stem)
    results.append(test(n,cfg,bars))

print(f"\n{'Strategy':45s} {'Status':10s} {'Trades':>7s} {'Time':>7s}")
print("-"*75)
ok=nt=cr=0
for r in results:
    print(f"{r['name']:45s} {r['status']:10s} {r['trades']:>7d} {r.get('elapsed',0):>6.1f}s")
    if r['status']=='OK': ok+=1
    elif r['status']=='NO_TRADES': nt+=1
    else: cr+=1
print("-"*75)
print(f"{ok} OK, {nt} no-trades, {cr} crashes across {len(results)} strategies")
