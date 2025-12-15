# Implementation Plan

- [x] 1. Create Signal Quality Gate configuration and models
  - [x] 1.1 Create `src/kinetic_empire/signal_quality/config.py` with QualityGateConfig dataclass
    - Define all threshold constants (confidence, RSI, stop loss percentages, leverage caps)
    - Include blacklist timing configuration
    - _Requirements: 1.1, 1.2, 1.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3_
  - [x] 1.2 Create `src/kinetic_empire/signal_quality/models.py` with result dataclasses
    - QualityGateResult, LossRecord, ConfidenceTier enum
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Implement ConfidenceFilter component
  - [x] 2.1 Create `src/kinetic_empire/signal_quality/confidence_filter.py`
    - Implement filter() method with three-tier logic (reject/medium/high)
    - Return tuple of (passed, tier, size_multiplier)
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 2.2 Write property test for confidence filtering
    - **Property 1: Confidence-Based Signal Filtering**
    - **Validates: Requirements 1.1, 1.2, 1.3**

- [x] 3. Implement DirectionAligner component
  - [x] 3.1 Create `src/kinetic_empire/signal_quality/direction_aligner.py`
    - Implement align() method that always returns Enhanced TA direction
    - Log warning when Cash Cow direction conflicts
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 3.2 Write property test for direction enforcement
    - **Property 2: Direction Enforcement**
    - **Validates: Requirements 2.1, 2.2, 2.3**

- [x] 4. Implement MomentumValidator component
  - [x] 4.1 Create `src/kinetic_empire/signal_quality/momentum_validator.py`
    - Implement validate() method checking 3-candle price change
    - Add RSI overbought/oversold rejection logic
    - _Requirements: 5.1, 5.2, 5.3_
  - [x] 4.2 Write property test for momentum validation
    - **Property 5: Momentum Validation**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 5. Implement BlacklistManager component
  - [x] 5.1 Create `src/kinetic_empire/signal_quality/blacklist_manager.py`
    - Implement record_loss() to track stop-losses per symbol
    - Implement is_blacklisted() with time-based expiration
    - Implement cleanup_expired() for maintenance
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 5.2 Write property test for blacklist lifecycle
    - **Property 3: Blacklist Lifecycle**
    - **Validates: Requirements 3.1, 3.2, 3.3**

- [x] 6. Implement RiskAdjuster component
  - [x] 6.1 Create `src/kinetic_empire/signal_quality/risk_adjuster.py`
    - Implement calculate_stop_loss() with regime-based percentages
    - Implement calculate_max_leverage() with confidence and regime logic
    - _Requirements: 4.1, 4.2, 4.3, 6.1, 6.2, 6.3_
  - [x] 6.2 Write property test for regime-based stop loss
    - **Property 4: Regime-Based Stop Loss**
    - **Validates: Requirements 4.1, 4.2, 4.3**
  - [x] 6.3 Write property test for leverage capping
    - **Property 6: Leverage Capping**
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [x] 7. Implement MicroTimeframeAnalyzer component
  - [x] 7.1 Create `src/kinetic_empire/signal_quality/micro_analyzer.py`
    - Implement analyze() method for 1M and 5M trend detection
    - Calculate EMA9/EMA21 crossover on both timeframes
    - Return alignment bonus or rejection flag
    - _Requirements: 7.1, 7.2, 7.3_
  - [x] 7.2 Write property test for micro-timeframe alignment
    - **Property 7: Micro-Timeframe Alignment**
    - **Validates: Requirements 7.2, 7.3**

- [x] 8. Implement BreakoutDetector component
  - [x] 8.1 Create `src/kinetic_empire/signal_quality/breakout_detector.py`
    - Implement detect() method for volume surge detection (>200% avg)
    - Detect price breakouts above resistance with volume confirmation
    - Return breakout bonus and tight trailing flag
    - _Requirements: 8.1, 8.2, 8.3_
  - [x] 8.2 Write property test for volume surge and breakout detection
    - **Property 8: Volume Surge and Breakout Detection**
    - **Validates: Requirements 8.1, 8.2, 8.3**

- [x] 9. Checkpoint - Ensure all component tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Create SignalQualityGate orchestrator
  - [x] 10.1 Create `src/kinetic_empire/signal_quality/gate.py`
    - Initialize all sub-components including MicroTimeframeAnalyzer and BreakoutDetector
    - Implement evaluate() method that chains all validations
    - Return comprehensive QualityGateResult with all bonuses
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1_
  - [x] 10.2 Create `src/kinetic_empire/signal_quality/__init__.py` with exports
    - Export SignalQualityGate, QualityGateConfig, QualityGateResult
    - _Requirements: All_

- [x] 11. Integrate SignalQualityGate with Cash Cow Live Engine
  - [x] 11.1 Update `run_cash_cow_live.py` to fetch 1M and 5M data
    - Add 1M and 5M kline fetching to symbol analysis
    - Pass micro-timeframe data to SignalQualityGate
    - _Requirements: 7.1_
  - [x] 11.2 Update `run_cash_cow_live.py` to use SignalQualityGate
    - Add gate evaluation before trade execution
    - Use gate's direction instead of Cash Cow direction
    - Apply position size multiplier from gate
    - Add micro-alignment bonus and breakout bonus to confidence
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 7.2, 7.3, 8.2_
  - [x] 11.3 Update stop loss calculation to use regime-based values
    - Replace hardcoded 3% with RiskAdjuster values
    - Use tighter trailing stops for breakout trades
    - _Requirements: 4.1, 4.2, 4.3, 8.3_
  - [x] 11.4 Update leverage calculation to use capped values
    - Apply max leverage from RiskAdjuster
    - _Requirements: 6.1, 6.2, 6.3_
  - [x] 11.5 Add blacklist recording on stop-loss exits
    - Call blacklist_manager.record_loss() when stopped out
    - Check is_blacklisted() before scanning symbols
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 12. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
