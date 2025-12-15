# Cash Cow Upgrade - Implementation Plan

## Phase 1: Core Position Sizing (Highest Impact)

- [x] 1. Implement Confidence-Based Position Sizer
  - [x] 1.1 Create ConfidenceBasedSizer class with multiplier logic
    - Implement get_confidence_multiplier() returning 2.0/1.5/1.0/0.0 based on score brackets
    - Implement calculate_size() combining all multipliers
    - Enforce 10% max position cap
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  - [x] 1.2 Write property test for confidence multiplier bounds
    - **Property 1: Confidence multiplier bounds**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
  - [x] 1.3 Write property test for position size cap
    - **Property 2: Position size cap enforcement**
    - **Validates: Requirements 1.5**

- [x] 2. Implement Consecutive Loss Tracker
  - [x] 2.1 Create ConsecutiveLossTracker class
    - Implement record_loss() incrementing counter
    - Implement record_win() resetting counter
    - Implement get_protection_multiplier() returning 1.0/0.5/0.25
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [x] 2.2 Write property test for loss counter correctness
    - **Property 3: Consecutive loss counter correctness**
    - **Validates: Requirements 2.1, 2.2**
  - [x] 2.3 Write property test for protection multiplier
    - **Property 4: Loss protection multiplier correctness**
    - **Validates: Requirements 2.3, 2.4, 2.5**

- [x] 3. Implement Circuit Breaker
  - [x] 3.1 Create CircuitBreaker class
    - Implement check_and_trigger() with 2% threshold
    - Implement reset_for_new_day()
    - Implement can_enter_new_trade() and can_exit_position()
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 3.2 Write property test for circuit breaker activation
    - **Property 5: Circuit breaker activation**
    - **Validates: Requirements 3.1, 3.4**
  - [x] 3.3 Write property test for circuit breaker reset
    - **Property 6: Circuit breaker reset**
    - **Validates: Requirements 3.3**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: Enhanced Scoring System

- [x] 5. Implement 130-Point Opportunity Scorer
  - [x] 5.1 Create OpportunityScorer class with component scoring
    - Implement score_technical() (0-40 pts): EMA freshness, RSI zones, MACD, VWAP
    - Implement score_momentum() (0-25 pts): ADX, DI spread, price momentum
    - Implement score_volume() (0-20 pts): volume ratio, OBV
    - Implement score_volatility() (0-15 pts): ATR-based
    - Implement score_regime() (0-10 pts): market condition
    - Implement score_sentiment() (0-10 pts): Fear & Greed
    - Implement score_growth_potential() (0-10 pts): momentum + volatility
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_
  - [x] 5.2 Write property test for component score bounds
    - **Property 7: Component score bounds**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7**
  - [x] 5.3 Write property test for total score summation
    - **Property 8: Total score summation**
    - **Validates: Requirements 4.8**

- [x] 6. Implement Upside Analyzer
  - [x] 6.1 Create UpsideAnalyzer class
    - Implement calculate_distance_to_resistance()
    - Implement calculate_risk_reward()
    - Implement get_upside_score() with 25/20/10/0 point tiers
    - Implement get_rr_bonus() with 5/3/0 point tiers
    - Apply -15 penalty for <1% room
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_
  - [x] 6.2 Write property test for upside distance calculation
    - **Property 9: Upside distance calculation**
    - **Validates: Requirements 5.1**
  - [x] 6.3 Write property test for upside score assignment
    - **Property 10: Upside score assignment**
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5**
  - [x] 6.4 Write property test for R/R calculation
    - **Property 11: Risk/reward calculation**
    - **Validates: Requirements 5.6**
  - [x] 6.5 Write property test for R/R bonus assignment
    - **Property 12: R/R bonus assignment**
    - **Validates: Requirements 5.7, 5.8**

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: Regime-Adaptive Risk Management

- [x] 8. Implement Regime-Adaptive Sizing
  - [x] 8.1 Enhance Position Sizer with regime multipliers
    - Implement get_regime_multiplier() returning 1.0/0.5/0.75/0.85
    - Implement conservative multiplier selection for multiple conditions
    - Integrate with existing ConfidenceBasedSizer
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  - [x] 8.2 Write property test for regime multiplier correctness
    - **Property 13: Regime multiplier correctness**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
  - [x] 8.3 Write property test for conservative multiplier selection
    - **Property 14: Conservative multiplier selection**
    - **Validates: Requirements 6.5**

- [x] 9. Implement Minimum Stop Distance Enforcement
  - [x] 9.1 Create StopDistanceEnforcer
    - Implement enforce_minimum_stop() with 1.5% floor
    - Implement validate_stop_distance()
    - Integrate with trade validation
    - _Requirements: 7.1, 7.2, 7.3_
  - [x] 9.2 Write property test for minimum stop enforcement
    - **Property 15: Minimum stop distance enforcement**
    - **Validates: Requirements 7.1, 7.2, 7.3**

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: Dynamic Scanning and Alignment

- [x] 11. Implement Dynamic Universe Scanner
  - [x] 11.1 Enhance MarketScanner with 130-point scoring
    - Integrate OpportunityScorer into scanning pipeline
    - Implement ranking by total score
    - Return top N opportunities
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [x] 11.2 Write property test for opportunity ranking
    - **Property 16: Opportunity ranking correctness**
    - **Validates: Requirements 8.2**

- [x] 12. Implement Multi-Timeframe Aligner
  - [x] 12.1 Create MultiTimeframeAligner class
    - Implement get_trend_direction() for each timeframe
    - Implement check_alignment() counting aligned timeframes
    - Calculate alignment bonus (+10/+5/-10) and daily conflict penalty (-5)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  - [x] 12.2 Write property test for alignment bonus correctness
    - **Property 17: Alignment bonus correctness**
    - **Validates: Requirements 9.2, 9.3, 9.4, 9.5**

- [x] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: Crypto-Specific Enhancements

- [x] 14. Implement Funding Rate Integration
  - [x] 14.1 Create FundingRateAnalyzer
    - Implement get_funding_bonus() for extreme funding rates
    - +5 for long when funding < -0.1%
    - +5 for short when funding > 0.1%
    - _Requirements: 10.1, 10.2_
  - [x] 14.2 Write property test for funding rate bonus
    - **Property 18: Funding rate bonus correctness**
    - **Validates: Requirements 10.1, 10.2**

- [x] 15. Implement BTC Correlation Adjustment
  - [x] 15.1 Create BTCCorrelationAdjuster
    - Implement calculate_correlation() with BTC
    - Implement get_correlation_adjustment() reducing size by 20% when high correlation + volatile BTC
    - _Requirements: 10.3, 10.4_
  - [x] 15.2 Write property test for BTC correlation adjustment
    - **Property 19: BTC correlation adjustment**
    - **Validates: Requirements 10.3, 10.4**

- [x] 16. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 6: Integration and Engine Update

- [x] 17. Integrate All Components into Trading Engine
  - [x] 17.1 Update engine.py to use new components
    - Wire OpportunityScorer into analysis pipeline
    - Wire ConfidenceBasedSizer into position management
    - Wire ConsecutiveLossTracker into trade result handling
    - Wire CircuitBreaker into trade entry validation
    - Wire UpsideAnalyzer into opportunity evaluation
    - Wire MultiTimeframeAligner into signal generation
    - _Requirements: All_

- [x] 18. Create Cash Cow Configuration
  - [x] 18.1 Add configuration options for all new features
    - Confidence thresholds (85/75/65)
    - Loss protection thresholds (3/5 losses)
    - Circuit breaker threshold (2%)
    - Minimum stop distance (1.5%)
    - Regime multipliers
    - _Requirements: All_

- [x] 19. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
