# Implementation Plan

- [x] 1. Disable High-Quality Bypass and Update Config
  - [x] 1.1 Update QualityGateConfig to disable bypass
    - Set `high_quality_bypass_enabled = False`
    - Set `max_consecutive_losses = 1` (faster blacklist)
    - Set `blacklist_duration_minutes = 60`
    - _Requirements: 1.3, 7.1_
  - [ ]* 1.2 Write property test for regime rejection
    - **Property 1: Regime-based trade rejection**
    - **Validates: Requirements 1.1, 1.2**
  - [x] 1.3 Update SignalQualityGate to reject CHOPPY/SIDEWAYS unconditionally
    - Remove high-quality bypass logic
    - Add clear rejection logging with regime type
    - _Requirements: 1.1, 1.2, 1.4_

- [x] 2. Implement Improved Regime Detection
  - [x] 2.1 Create RegimeDetector class with ADX-based detection
    - ADX > 25 → TRENDING
    - 15 ≤ ADX ≤ 25 → SIDEWAYS
    - ADX < 15 → CHOPPY
    - Include trend direction (bullish/bearish) based on price vs 50-MA
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [ ]* 2.2 Write property test for ADX-based regime detection
    - **Property 9: ADX-based regime detection**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**

- [x] 3. Implement Direction Validator
  - [x] 3.1 Create DirectionValidator class
    - Check last 5 candles for price momentum
    - Reject LONG if price fell > 0.3%
    - Reject SHORT if price rose > 0.3%
    - Log contradiction percentage
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - [ ]* 3.2 Write property test for direction validation
    - **Property 6: Direction validation against price momentum**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Confidence-Based Position Sizer
  - [x] 5.1 Create ConfidencePositionSizer class
    - Implement confidence-to-size mapping (5-15%)
    - Return None for confidence < 50
    - Include confidence tier in result
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  - [ ]* 5.2 Write property test for position sizing mapping
    - **Property 2: Confidence-to-position-size mapping**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**
  - [x] 5.3 Create ExposureTracker class
    - Track total portfolio exposure
    - Enforce 45% maximum exposure cap
    - Recalculate on position open/close
    - _Requirements: 2.7, 8.1, 8.2, 8.3_
  - [ ]* 5.4 Write property test for exposure cap invariant
    - **Property 3: Portfolio exposure cap invariant**
    - **Validates: Requirements 2.7, 8.1, 8.2, 8.3**

- [x] 6. Implement Regime-Based Leverage Calculator
  - [x] 6.1 Create RegimeLeverageCalculator class
    - TRENDING + 90-100 → 10x
    - TRENDING + 70-89 → 7x
    - TRENDING + 50-69 → 5x
    - SIDEWAYS → 3x max
    - CHOPPY → 2x max
    - Reduce by 50% after 2+ consecutive losses
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  - [ ]* 6.2 Write property test for leverage calculation
    - **Property 4: Regime-confidence-to-leverage mapping**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement ATR-Based Stop Calculator
  - [x] 8.1 Create ATRStopCalculator class
    - TRENDING → 2.0x ATR
    - SIDEWAYS → 2.5x ATR
    - CHOPPY → 3.0x ATR
    - Enforce 1% minimum, 5% maximum bounds
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - [ ]* 8.2 Write property test for ATR stop calculation
    - **Property 5: ATR stop loss calculation with bounds**
    - **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**

- [x] 9. Implement ATR Trailing Stop Manager
  - [x] 9.1 Create ATRTrailingStopManager class
    - Activate trailing at 2% profit
    - Trail at 1.5x ATR from peak
    - Tighten to 1.0x ATR at 5% profit
    - Log peak vs exit profit on trigger
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  - [ ]* 9.2 Write property test for trailing stop behavior
    - **Property 7: Trailing stop activation and tightening**
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [x] 10. Update Blacklist Manager
  - [x] 10.1 Update BlacklistManager for faster trigger
    - Blacklist after 1 loss (not 2)
    - 60-minute blacklist duration
    - _Requirements: 7.1, 7.2, 7.3_
  - [ ]* 10.2 Write property test for blacklist behavior
    - **Property 8: Blacklist trigger and expiration**
    - **Validates: Requirements 7.1, 7.2, 7.3**

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement Entry Confirmer
  - [x] 12.1 Create EntryConfirmer class
    - Create pending entries with 30-second confirmation
    - Monitor for 0.5% adverse price movement
    - Cancel if price moves against signal
    - Execute at market price after confirmation
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  - [ ]* 12.2 Write property test for entry confirmation
    - **Property 10: Entry confirmation with cancellation**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

- [x] 13. Integrate Components into SignalQualityGate v2
  - [x] 13.1 Create QualityGateResultV2 data model
    - Include all new fields (position_size_pct, leverage, atr_value, etc.)
    - _Requirements: All_
  - [x] 13.2 Update SignalQualityGate.evaluate() method
    - Integrate RegimeDetector
    - Integrate DirectionValidator
    - Integrate ConfidencePositionSizer
    - Integrate RegimeLeverageCalculator
    - Integrate ATRStopCalculator
    - Integrate ExposureTracker
    - _Requirements: All_
  - [x] 13.3 Update run_bot.py to use new components
    - Use ATRTrailingStopManager for position monitoring
    - Use EntryConfirmer for delayed entry
    - Update position sizing to use new calculator
    - Update leverage to use new calculator
    - _Requirements: All_

- [x] 14. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
