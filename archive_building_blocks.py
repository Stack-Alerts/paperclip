#!/usr/bin/env python3
"""
Archive selected expert review, block script, and documentation files.

Default: DRY RUN (no files are moved, only listed).
Use --execute to actually move files.

Run from the project root, i.e. where src/ and docs/ live.
"""

from pathlib import Path
import argparse
import shutil

# Root-relative paths to archive
FILES_TO_ARCHIVE = [
    # --- 1–10 ---
    "01_ema_20_50_cross_expert_review.md",
    "src/detectors/building_blocks/moving_averages/ema_20_50_cross.py",
    "docs/v3/building_blocks/moving_averages/20_50_EMA_Cross.md",

    "02_ema_20_50_trend_expert_review.md",
    "src/detectors/building_blocks/moving_averages/ema_20_50_trend.py",
    "docs/v3/building_blocks/moving_averages/20_50_EMA_Trend_Tracker.md",

    "03_ema_50_vector_expert_review.md",
    "src/detectors/building_blocks/moving_averages/ema_50_vector.py",
    "docs/v3/building_blocks/moving_averages/50_EMA_Vector_Break.md",

    "04_ema_55_vector_expert_review.md",
    "src/detectors/building_blocks/moving_averages/ema_55_vector.py",
    "docs/v3/building_blocks/moving_averages/55_EMA_Vector_Break.md",

    "05_ema_200_trend_expert_review.md",
    "src/detectors/building_blocks/moving_averages/ema_200_trend.py",
    "docs/v3/building_blocks/moving_averages/200_EMA_Trend.md",

    "06_ema_255_vector_expert_review.md",
    "src/detectors/building_blocks/moving_averages/ema_255_vector.py",
    "docs/v3/building_blocks/moving_averages/255_EMA_Vector_Break.md",

    "07_ema_800_vector_expert_review.md",
    "src/detectors/building_blocks/moving_averages/ema_800_vector.py",
    "docs/v3/building_blocks/moving_averages/800_EMA_Vector_Break.md",

    "08_macd_signal_expert_review.md",
    "src/detectors/building_blocks/oscillators/macd_signal.py",
    "docs/v3/building_blocks/oscillators/MACD_Signal.md",

    "09_rsi_divergence_expert_review.md",
    "src/detectors/building_blocks/oscillators/rsi.py",
    "docs/v3/building_blocks/oscillators/RSI.md",

    "10_stochastic_rsi_expert_review.md",
    "src/detectors/building_blocks/oscillators/stochastic.py",
    "docs/v3/building_blocks/oscillators/Stochastic.md",

    # --- 11–20 ---
    "11_order_block_expert_review.md",
    "src/detectors/building_blocks/price_action/order_block.py",
    "docs/v3/building_blocks/price_action/Order_Block.md",

    "12_fair_value_gap_expert_review.md",
    "src/detectors/building_blocks/price_action/fair_value_gap.py",
    "docs/v3/building_blocks/price_action/Fair_Value_Gap.md",

    "13_liquidity_sweep_expert_review.md",
    "src/detectors/building_blocks/smc_ict/liquidity_sweep.py",
    "docs/v3/building_blocks/smc_ict/Liquidity_Sweep.md",

    "14_breaker_block_expert_review.md",
    "src/detectors/building_blocks/smc_ict/breaker_block.py",
    "docs/v3/building_blocks/smc_ict/Breaker_Block.md",

    "15_ichimoku_cloud_expert_review.md",
    "src/detectors/building_blocks/trend_momentum/ichimoku_cloud.py",
    "docs/v3/building_blocks/trend_momentum/Ichimoku_Cloud.md",

    "16_adx_expert_review.md",
    "src/detectors/building_blocks/trend_momentum/adx.py",
    "docs/v3/building_blocks/trend_momentum/ADX.md",

    "17_break_of_structure_expert_review.md",
    "src/detectors/building_blocks/smc_ict/break_of_structure.py",
    "docs/v3/building_blocks/smc_ict/Break_Of_Structure.md",

    "18_market_structure_shift_expert_review.md",
    "src/detectors/building_blocks/smc_ict/market_structure_shift.py",
    "docs/v3/building_blocks/smc_ict/Market_Structure_Shift.md",

    "19_displacement_expert_review.md",
    "src/detectors/building_blocks/smc_ict/displacement.py",
    "docs/v3/building_blocks/smc_ict/Displacement.md",

    "20_inducement_expert_review.md",
    "src/detectors/building_blocks/smc_ict/inducement.py",
    "docs/v3/building_blocks/smc_ict/Inducement.md",

    # --- 21–30 ---
    "21_optimal_trade_entry_expert_review.md",
    "src/detectors/building_blocks/smc_ict/optimal_trade_entry.py",
    "docs/v3/building_blocks/smc_ict/Optimal_Trade_Entry.md",

    "22_swing_failure_pattern_expert_review.md",
    "src/detectors/building_blocks/smc_ict/swing_failure_pattern.py",
    "docs/v3/building_blocks/smc_ict/Swing_Failure_Pattern.md",

    "23_premium_discount_expert_review.md",
    "src/detectors/building_blocks/market_structure/premium_discount_zones.py",
    "docs/v3/building_blocks/market_structure/Premium_Discount_Zones.md",

    "24_change_of_character_expert_review.md",
    "src/detectors/building_blocks/smc_ict/change_of_character.py",
    "docs/v3/building_blocks/smc_ict/Change_Of_Character.md",

    "25_mitigation_block_expert_review.md",
    "src/detectors/building_blocks/smc_ict/mitigation_block.py",
    "docs/v3/building_blocks/smc_ict/Mitigation_Block.md",

    "26_balanced_price_range_expert_review.md",
    "src/detectors/building_blocks/smc_ict/balanced_price_range.py",
    "docs/v3/building_blocks/smc_ict/Balanced_Price_Range.md",

    "27_vwap_expert_review.md",
    "src/detectors/building_blocks/institutional/vwap.py",
    "docs/v3/building_blocks/institutional/VWAP.md",

    "28_atr_expert_review.md",
    "src/detectors/building_blocks/volatility/atr.py",
    "docs/v3/building_blocks/volatility/ATR.md",

    "29_adr_expert_review.md",
    "src/detectors/building_blocks/volatility/adr.py",
    "docs/v3/building_blocks/volatility/ADR.md",

    "30_bollinger_bands_expert_review.md",
    "src/detectors/building_blocks/volatility/bollinger_bands.py",
    "docs/v3/building_blocks/volatility/Bollinger_Bands.md",

    # --- 31–40 ---
    "31_double_top_expert_review.md",
    "src/detectors/building_blocks/patterns/double_top.py",
    "docs/v3/building_blocks/patterns/Double_Top.md",

    "32_double_bottom_expert_review.md",
    "src/detectors/building_blocks/patterns/double_bottom.py",
    "docs/v3/building_blocks/patterns/Double_Bottom.md",

    "33_triple_top_expert_review.md",
    "src/detectors/building_blocks/patterns/triple_top.py",
    "docs/v3/building_blocks/patterns/Triple_Top.md",

    "34_triple_bottom_expert_review.md",
    "src/detectors/building_blocks/patterns/triple_bottom.py",
    "docs/v3/building_blocks/patterns/Triple_Bottom.md",

    "35_head_and_shoulders_expert_review.md",
    "src/detectors/building_blocks/patterns/head_and_shoulders.py",
    "docs/v3/building_blocks/patterns/Head_And_Shoulders.md",

    "36_inverse_head_and_shoulders_expert_review.md",
    "src/detectors/building_blocks/patterns/inverse_head_and_shoulders.py",
    "docs/v3/building_blocks/patterns/Inverse_Head_And_Shoulders.md",

    "37_cup_and_handle_expert_review.md",
    "src/detectors/building_blocks/patterns/cup_and_handle.py",
    "docs/v3/building_blocks/patterns/Cup_And_Handle.md",

    "38_rounding_bottom_expert_review.md",
    "src/detectors/building_blocks/patterns/rounding_bottom.py",
    "docs/v3/building_blocks/patterns/Rounding_Bottom.md",

    "39_flag_pattern_expert_review.md",
    "src/detectors/building_blocks/patterns/flag_pattern.py",
    "docs/v3/building_blocks/patterns/Flag_Pattern.md",

    "40_pennant_pattern_expert_review.md",
    "src/detectors/building_blocks/patterns/pennant_pattern.py",
    "docs/v3/building_blocks/patterns/Pennant_Pattern.md",

    # --- 41–50 ---
    "41_symmetrical_triangle_expert_review.md",
    "src/detectors/building_blocks/patterns/symmetrical_triangle.py",
    "docs/v3/building_blocks/patterns/Symmetrical_Triangle.md",

    "42_ascending_triangle_expert_review.md",
    "src/detectors/building_blocks/patterns/ascending_triangle.py",
    "docs/v3/building_blocks/patterns/Ascending_Triangle.md",

    "43_descending_triangle_expert_review.md",
    "src/detectors/building_blocks/patterns/descending_triangle.py",
    "docs/v3/building_blocks/patterns/Descending_Triangle.md",

    "44_falling_wedge_expert_review.md",
    "src/detectors/building_blocks/patterns/falling_wedge.py",
    "docs/v3/building_blocks/patterns/Falling_Wedge.md",

    "45_rising_wedge_expert_review.md",
    "src/detectors/building_blocks/patterns/rising_wedge.py",
    "docs/v3/building_blocks/patterns/Rising_Wedge.md",

    "46_hod_expert_review.md",
    "src/detectors/building_blocks/price_levels/hod.py",
    "docs/v3/building_blocks/price_levels/HOD.md",

    "47_how_expert_review.md",
    "src/detectors/building_blocks/price_levels/how.py",
    "docs/v3/building_blocks/price_levels/HOW.md",

    "48_lod_expert_review.md",
    "src/detectors/building_blocks/price_levels/lod.py",
    "docs/v3/building_blocks/price_levels/LOD.md",

    "49_low_expert_review.md",
    "src/detectors/building_blocks/price_levels/low.py",
    "docs/v3/building_blocks/price_levels/LOW.md",

    "50_asia_session_50_percent_expert_review.md",
    "src/detectors/building_blocks/price_levels/asia_session_50_percent.py",
    "docs/v3/building_blocks/price_levels/Asia_Session_50_Percent.md",

    # --- 51–60 ---
    "51_elliott_wave_count_expert_review.md",
    "src/detectors/building_blocks/elliott_wave/elliott_wave_count.py",
    "docs/v3/building_blocks/ELLIOTT_WAVE_COUNT_COMPLETE_GUIDE.md",

    "52_elliott_wave_oscillator_expert_review.md",
    "src/detectors/building_blocks/elliott_wave/elliott_wave_oscillator.py",
    "docs/v3/building_blocks/elliott_wave/Elliott_Wave_Oscillator.md",

    "53_wyckoff_accumulation_expert_review.md",
    "src/detectors/building_blocks/wyckoff/wyckoff_accumulation.py",
    "docs/v3/building_blocks/wyckoff/Wyckoff_Accumulation.md",

    "54_wyckoff_distribution_expert_review.md",
    "src/detectors/building_blocks/wyckoff/wyckoff_distribution.py",
    "docs/v3/building_blocks/wyckoff/Wyckoff_Distribution.md",

    "55_wyckoff_reaccumulation_expert_review.md",
    "src/detectors/building_blocks/wyckoff/wyckoff_reaccumulation.py",
    "docs/v3/building_blocks/wyckoff/Wyckoff_Reaccumulation.md",

    "56_fibonacci_retracements_expert_review.md",
    "src/detectors/building_blocks/fibonacci/fibonacci_retracements.py",
    "docs/v3/building_blocks/fibonacci/Fibonacci_Retracements.md",

    "57_anchored_vwap_expert_review.md",
    "src/detectors/building_blocks/institutional/anchored_vwap.py",
    "docs/v3/building_blocks/institutional/Anchored_VWAP.md",

    "58_ema_crossover_expert_review.md",
    "src/detectors/building_blocks/institutional/ema_crossover.py",
    "docs/v3/building_blocks/institutional/EMA_Crossover.md",

    "59_market_depth_expert_review.md",
    "src/detectors/building_blocks/institutional/market_depth.py",
    "docs/v3/building_blocks/institutional/Market_Depth.md",

    "60_order_flow_imbalance_expert_review.md",
    "src/detectors/building_blocks/institutional/order_flow_imbalance.py",
    "docs/v3/building_blocks/institutional/Order_Flow_Imbalance.md",

    # --- 61–70 ---
    "61_premium_discount_zones_expert_review.md",
    "src/detectors/building_blocks/market_structure/premium_discount_zones.py",
    "docs/v3/building_blocks/market_structure/Premium_Discount_Zones.md",

    "62_range_liquidity_expert_review.md",
    "src/detectors/building_blocks/market_structure/range_liquidity.py",
    "docs/v3/building_blocks/market_structure/Range_Liquidity.md",

    "63_swing_points_expert_review.md",
    "src/detectors/building_blocks/market_structure/swing_points.py",
    "docs/v3/building_blocks/market_structure/Swing_Points.md",

    "64_kill_zones_expert_review.md",
    "src/detectors/building_blocks/sessions/kill_zones.py",
    "docs/v3/building_blocks/sessions/Kill_Zones.md",

    "65_session_time_expert_review.md",
    "src/detectors/building_blocks/sessions/session_time.py",
    "docs/v3/building_blocks/sessions/Session_Time.md",

    "66_us_settlement_expert_review.md",
    "src/detectors/building_blocks/sessions/us_settlement.py",
    "docs/v3/building_blocks/sessions/US_Settlement.md",

    "67_supply_demand_zones_expert_review.md",
    "src/detectors/building_blocks/supply_demand/supply_demand_zones.py",
    "docs/v3/building_blocks/supply_demand/Supply_Demand_Zones.md",

    "68_initial_balance_breakout_expert_review.md",
    "src/detectors/building_blocks/patterns/initial_balance_breakout.py",
    "docs/v3/building_blocks/patterns/Initial_Balance_Breakout.md",

    "69_liquidity_expert_review.md",
    "src/detectors/building_blocks/market_structure/liquidity.py",
    "docs/v3/building_blocks/market_structure/Liquidity.md",

    "70_trailing_stop_expert_review.md",
    "src/detectors/building_blocks/risk_management/trailing_stop.py",
    "docs/v3/building_blocks/risk_management/Trailing_Stop.md",

    # --- 71–80 ---
    "71_macd_price_forecasting_expert_review.md",
    "src/detectors/building_blocks/signals/macd_price_forecasting.py",
    "docs/v3/building_blocks/signals/MACD_Price_Forecasting.md",

    "72_adaptive_momentum_oscillator_expert_review.md",
    "src/detectors/building_blocks/signals/adaptive_momentum_oscillator.py",
    "docs/v3/building_blocks/signals/Adaptive_Momentum_Oscillator.md",

    "73_power_hour_trends_expert_review.md",
    "src/detectors/building_blocks/market_structure/power_hour_trends.py",
    "docs/v3/building_blocks/market_structure/Power_Hour_Trends.md",

    "74_ict_silver_bullet_expert_review.md",
    "src/detectors/building_blocks/signals/ict_silver_bullet.py",
    "docs/v3/building_blocks/signals/ICT_Silver_Bullet.md",

    "75_asfx_a2_vwap_expert_review.md",
    "src/detectors/building_blocks/signals/asfx_a2_vwap.py",
    "docs/v3/building_blocks/signals/ASFX_A2_VWAP.md",

    "76_three_bar_reversal_expert_review.md",
    "src/detectors/building_blocks/patterns/three_bar_reversal.py",
    "docs/v3/building_blocks/patterns/Three_Bar_Reversal.md",

    "77_candle_2_close_expert_review.md",
    "src/detectors/building_blocks/patterns/candle_2_close.py",
    "docs/v3/building_blocks/patterns/Candle_2_Close.md",

    "78_internal_pivot_pattern_expert_review.md",
    "src/detectors/building_blocks/patterns/internal_pivot_pattern.py",
    "docs/v3/building_blocks/patterns/Internal_Pivot_Pattern.md",

    "79_swing_breakout_sequence_expert_review.md",
    "src/detectors/building_blocks/patterns/swing_breakout_sequence.py",
    "docs/v3/building_blocks/patterns/Swing_Breakout_Sequence.md",

    "80_wave_consolidation_expert_review.md",
    "src/detectors/building_blocks/market_structure/wave_consolidation.py",
    "docs/v3/building_blocks/market_structure/Wave_Consolidation.md",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Archive selected expert review, block script, and doc files."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Project root directory (default: current directory).",
    )
    parser.add_argument(
        "--archive-dir",
        type=str,
        default="archive",
        help="Archive directory relative to root (default: 'archive').",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually move files instead of dry-run preview.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    root = Path(args.root).resolve()
    archive_root = root / args.archive_dir

    print(f"Project root: {root}")
    print(f"Archive dir:  {archive_root}")
    print(f"Mode:         {'EXECUTE (moving files)' if args.execute else 'DRY RUN (no changes)'}")
    print("-" * 80)

    existing = []
    missing = []

    for rel in FILES_TO_ARCHIVE:
        src = root / rel
        if src.exists():
            existing.append((rel, src))
        else:
            missing.append(rel)

    if missing:
        print("Missing (will be skipped):")
        for rel in missing:
            print(f"  - {rel}")
        print("-" * 80)

    if not existing:
        print("No existing files to process. Exiting.")
        return

    print("Files to archive:")
    for rel, src in existing:
        dst = archive_root / rel
        print(f"  {src}  ->  {dst}")
    print("-" * 80)

    if not args.execute:
        print("DRY RUN complete. No files were moved.")
        print("Re-run with --execute to actually move files.")
        return

    # Ensure archive directory tree exists and move files
    for rel, src in existing:
        dst = archive_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        print(f"Moving: {src}  ->  {dst}")
        shutil.move(str(src), str(dst))

    print("-" * 80)
    print(f"Done. Moved {len(existing)} file(s) into '{archive_root}'.")


if __name__ == "__main__":
    main()
