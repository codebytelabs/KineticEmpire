# Implementation Plan

- [x] 1. Update ExposureTracker defaults and config integration
  - [x] 1.1 Change DEFAULT_MAX_EXPOSURE from 0.45 to 0.90 in exposure_tracker.py
    - Update the class constant to reflect aggressive capital utilization
    - _Requirements: 1.1, 5.1_
  - [ ]* 1.2 Write property test for exposure tracking invariant
    - **Property 1: Exposure tracking invariant**
    - **Validates: Requirements 1.3, 1.4**
    - Test that available exposure equals max minus sum of positions after any add/remove sequence

- [x] 2. Update ConfidencePositionSizer for aggressive sizing
  - [x] 2.1 Update CONFIDENCE_TO_SIZE mapping in position_sizer.py
    - Change mapping: (90-100)→20%, (80-89)→18%, (70-79)→15%, (60-69)→12%
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x] 2.2 Add regime-aware MIN_CONFIDENCE thresholds
    - MIN_CONFIDENCE_TRENDING = 60 (for trending markets)
    - MIN_CONFIDENCE_SIDEWAYS = 65 (for sideways/choppy - more selective)
    - Update calculate() to accept market_regime parameter
    - _Requirements: 4.1, 4.2_
  - [ ]* 2.3 Write property test for confidence-to-size mapping
    - **Property 2: Confidence-to-size mapping consistency**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    - Test that each confidence tier returns the correct position size percentage
  - [ ]* 2.4 Write property test for regime-aware confidence rejection
    - **Property 3: Regime-aware confidence rejection**
    - **Validates: Requirements 4.1, 4.2**
    - Test that TRENDING rejects below 60, SIDEWAYS/CHOPPY rejects below 65

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Update UnifiedConfig defaults
  - [x] 4.1 Update futures_max_positions_min from 5 to 8 in unified/config.py
    - Increase minimum concurrent positions for choppy markets
    - _Requirements: 3.3_
  - [x] 4.2 Update futures_position_size_max_pct from 20 to 25
    - Allow larger maximum position sizes
    - _Requirements: 5.4_
  - [x] 4.3 Add regime-aware confidence thresholds to config
    - Add futures_min_confidence_trending: 60
    - Add futures_min_confidence_sideways: 65
    - _Requirements: 4.1, 4.2_
  - [ ]* 4.4 Write property test for position size bounds clamping
    - **Property 4: Position size bounds clamping**
    - **Validates: Requirements 5.4**
    - Test that calculated sizes are clamped between min (8%) and max (25%)

- [x] 5. Update FuturesEngine dynamic position limits
  - [x] 5.1 Update _get_dynamic_max_positions() in futures_engine.py
    - TRENDING: return 12, SIDEWAYS: return 10, CHOPPY: return 8
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [ ]* 5.2 Write unit tests for regime-based position limits
    - Test each regime returns correct max positions value
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 6. Update root config.py with aggressive defaults
  - [x] 6.1 Update UNIFIED_CONFIG dictionary in config.py
    - Set futures_min_confidence_trending: 60
    - Set futures_min_confidence_sideways: 65
    - Set futures_max_positions_min: 8
    - Set futures_position_size_max_pct: 25
    - _Requirements: 5.3, 4.1, 4.2_
  - [ ]* 6.2 Write property test for config propagation
    - **Property 5: Config propagation**
    - **Validates: Requirements 1.1, 5.3**
    - Test that components instantiated with config use the config values

- [x] 7. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
