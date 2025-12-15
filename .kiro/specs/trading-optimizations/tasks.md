# Implementation Plan

- [x] 1. Set up optimizations module structure
  - Create `src/kinetic_empire/optimizations/` directory
  - Create `__init__.py` with exports
  - Create `config.py` with all optimization configurations
  - _Requirements: All_

- [x] 2. Implement Trailing Stop Optimizer (Tier 1 - Critical)
  - [x] 2.1 Create trailing_optimizer.py with TrailingOptConfig and TrailingOptimizer class
    - Implement `should_activate(profit_pct)` returning True when profit >= 1.5%
    - Implement `get_trail_multiplier(profit_pct)` returning 1.5x or 1.0x based on 3% threshold
    - Implement `calculate_trail_stop(peak_price, atr, profit_pct)`
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 2.2 Write property test for trailing activation threshold
    - **Property 1: Trailing Stop Activation Threshold**
    - **Validates: Requirements 1.1**
  - [x] 2.3 Write property test for trailing tightening
    - **Property 2: Trailing Stop Tightening**
    - **Validates: Requirements 1.2, 1.3**

- [x] 3. Implement Partial Profit Taker (Tier 1 - Critical)
  - [x] 3.1 Create profit_taker.py with PartialProfitConfig and PartialProfitTaker class
    - Implement `check_tp_levels(entry, current, atr, direction)` returning TPResult
    - Implement `get_close_percentage(tp_level)` returning 0.25 for TP1/TP2
    - Track TP1/TP2 state per position
    - _Requirements: 2.1, 2.2, 2.4_
  - [x] 3.2 Write property test for partial profit taking levels
    - **Property 3: Partial Profit Taking Levels**
    - **Validates: Requirements 2.1, 2.2, 2.4**

- [x] 4. Implement Half-Kelly Sizer (Tier 1 - Critical)
  - [x] 4.1 Create half_kelly.py with HalfKellySizer class
    - Implement `calculate_half_kelly(win_rate, rr_ratio)` returning 0.5 * full Kelly
    - Implement `clamp_stake(stake_pct, min_pct, max_pct)`
    - Implement `get_stake_percentage(pair, trade_history)`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 4.2 Write property test for Half-Kelly calculation
    - **Property 4: Half-Kelly Calculation**
    - **Validates: Requirements 3.1, 3.2, 3.3**

- [x] 5. Checkpoint - Ensure Tier 1 tests pass
  - All Tier 1 tests pass (15/15 passed)

- [x] 6. Implement Volume Tiered Sizer (Tier 2 - High Value)
  - [x] 6.1 Create volume_sizer.py with VolumeTierConfig and VolumeTieredSizer class
    - Implement `get_volume_tier(volume_ratio)` returning VolumeTier enum
    - Implement `get_volume_multiplier(volume_ratio)` returning 0.8/1.0/1.1/1.2
    - Implement `adjust_position_size(base_size, volume_ratio)`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 6.2 Write property test for volume tier multiplier
    - **Property 5: Volume Tier Multiplier**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [x] 7. Implement Regime-Adaptive Stop Manager (Tier 2 - High Value)
  - [x] 7.1 Create regime_stops.py with RegimeAdaptiveStops class
    - Implement `get_atr_multiplier(regime, trend_type)` returning 1.5/2.0/2.5
    - Implement `calculate_stop_loss(entry, atr, regime, trend, direction)`
    - Ensure existing stops are not modified on regime change
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - [x] 7.2 Write property test for regime-adaptive ATR multiplier
    - **Property 6: Regime-Adaptive ATR Multiplier**
    - **Validates: Requirements 5.1, 5.2, 5.3**
  - [x] 7.3 Write property test for existing stops preservation
    - **Property 7: Existing Stops Preservation**
    - **Validates: Requirements 5.4**

- [x] 8. Implement RSI Zone Optimizer (Tier 2 - High Value)
  - [x] 8.1 Create rsi_zones.py with RSIZoneConfig and RSIZoneOptimizer class
    - Implement `get_rsi_bounds(regime)` returning (min, max) tuple
    - Implement `is_valid_rsi(rsi, regime)` returning True if RSI in valid range
    - BULL: 35-70, BEAR: 45-60
    - _Requirements: 6.1, 6.2, 6.3_
  - [x] 8.2 Write property test for RSI zone validation
    - **Property 8: RSI Zone Validation**
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [x] 9. Checkpoint - Ensure Tier 2 tests pass
  - All Tier 2 tests pass (15/15 passed)

- [x] 10. Implement Dynamic Blacklist Manager (Tier 3 - Enhancement)
  - [x] 10.1 Create dynamic_blacklist.py with DynamicBlacklistManager class
    - Implement `get_blacklist_duration(loss_pct)` returning 15/30/60 minutes
    - Implement `record_loss(symbol, loss_pct, timestamp)`
    - Implement `is_blacklisted(symbol)` checking expiration
    - Implement `cleanup_expired()` removing expired entries
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  - [x] 10.2 Write property test for blacklist duration by loss severity
    - **Property 9: Blacklist Duration by Loss Severity**
    - **Validates: Requirements 7.1, 7.2, 7.3**
  - [x] 10.3 Write property test for blacklist expiration
    - **Property 10: Blacklist Expiration**
    - **Validates: Requirements 7.4**

- [x] 11. Implement Fear & Greed Adjuster (Tier 3 - Enhancement)
  - [x] 11.1 Create fg_adjuster.py with FearGreedAdjuster class
    - Implement `get_size_multiplier(fg_index)` returning 0.7 if < 25, 1.0 otherwise
    - Implement `get_trail_multiplier(fg_index, base_mult)` returning 1.0 if > 75
    - Implement `should_adjust(fg_index)` returning True at extremes
    - Handle None fg_index gracefully (return standard params)
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [x] 11.2 Write property test for F&G adjustments
    - **Property 11: Fear & Greed Adjustments**
    - **Validates: Requirements 8.1, 8.2, 8.3**
  - [x] 11.3 Write property test for F&G fallback
    - **Property 12: F&G Fallback**
    - **Validates: Requirements 8.4**

- [x] 12. Implement Micro Alignment Bonus (Tier 3 - Enhancement)
  - [x] 12.1 Create micro_bonus.py with MicroAlignmentBonus class
    - Implement `check_alignment(trend_1m, trend_5m, signal_direction)` returning bool
    - Implement `get_size_bonus(is_aligned)` returning 0.05 if aligned, 0.0 otherwise
    - Implement `get_stop_reduction(is_aligned)` returning 0.5 if aligned, 0.0 otherwise
    - Implement `should_reject(trend_1m, trend_5m, signal_direction)` for contradictions
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [x] 12.2 Write property test for micro alignment bonus
    - **Property 13: Micro Alignment Bonus**
    - **Validates: Requirements 9.1, 9.2**
  - [x] 12.3 Write property test for micro contradiction rejection
    - **Property 14: Micro Contradiction Rejection**
    - **Validates: Requirements 9.3**

- [x] 13. Implement Entry Confirmation Manager (Tier 3 - Enhancement)
  - [x] 13.1 Create entry_confirm.py with EntryConfirmConfig and EntryConfirmationManager class
    - Implement `create_pending(symbol, direction, price)` creating PendingEntry
    - Implement `check_confirmation(symbol, current_price, candles)` returning (execute, reason)
    - Cancel if price moves > 0.3% against signal
    - Execute after 1 candle without adverse movement
    - _Requirements: 10.1, 10.2, 10.3_
  - [x] 13.2 Write property test for entry confirmation delay
    - **Property 15: Entry Confirmation Delay**
    - **Validates: Requirements 10.1, 10.2, 10.3**

- [x] 14. Checkpoint - Ensure Tier 3 tests pass
  - All 15 property tests pass

- [x] 15. Integration with existing modules
  - [x] 15.1 Update risk/trailing.py to use TrailingOptimizer
    - Import and use TrailingOptimizer for activation threshold and multiplier
    - Maintain backward compatibility with existing TrailingConfig
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - [x] 15.2 Update risk/kelly.py to use HalfKellySizer
    - Modify calculate_kelly_fraction to use Half-Kelly by default
    - Add config option to toggle between full and half Kelly
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 15.3 Update strategy/entry.py to use RSIZoneOptimizer
    - Replace hardcoded RSI bounds with regime-aware bounds
    - Integrate with existing check_pullback method
    - _Requirements: 6.1, 6.2, 6.3_
  - [x] 15.4 Update signal_quality/blacklist_manager.py to use DynamicBlacklistManager
    - Replace fixed duration with loss-severity-based duration
    - Maintain existing interface for backward compatibility
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 16. Update configuration files
  - [x] 16.1 Add optimization parameters to unified/config.py
    - Add trailing_activation_pct, tp1_atr_mult, tp2_atr_mult
    - Add volume_tier thresholds and multipliers
    - Add RSI zone bounds per regime
    - Add blacklist duration tiers
    - _Requirements: All_
  - [x] 16.2 Update config.py with new risk parameters
    - Add half_kelly_enabled flag
    - Add fg_adjustment_enabled flag
    - Add micro_bonus_enabled flag
    - _Requirements: All_

- [x] 17. Final Checkpoint - Ensure all tests pass
  - All 76 tests pass (15 property tests + 61 existing tests)
