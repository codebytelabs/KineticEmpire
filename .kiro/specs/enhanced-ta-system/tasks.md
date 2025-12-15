# Implementation Plan

- [x] 1. Set up project structure and core data models
  - [x] 1.1 Create enhanced TA module directory structure
    - Create `src/kinetic_empire/v3/analyzer/enhanced/` directory
    - Create `__init__.py` with module exports
    - _Requirements: 8.1_
  - [x] 1.2 Implement core enums and data models
    - Create `TrendDirection`, `TrendStrength`, `MarketRegime`, `SignalConfidence` enums
    - Create `TimeframeAnalysis`, `TrendAlignment`, `VolumeConfirmation`, `SupportResistance`, `MomentumAnalysis`, `MarketContext`, `ConfidenceScore`, `EnhancedSignal` dataclasses
    - _Requirements: All_
  - [x] 1.3 Write property tests for data model validation
    - **Property 4: Timeframe Weight Distribution**
    - **Validates: Requirements 1.4**

- [x] 2. Implement TrendStrengthCalculator
  - [x] 2.1 Create TrendStrengthCalculator class
    - Implement `calculate()` method for EMA separation percentage
    - Implement threshold-based classification (STRONG > 1%, MODERATE 0.3-1%, WEAK < 0.3%)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x] 2.2 Write property test for trend strength classification
    - **Property 5: Trend Strength Classification**
    - **Validates: Requirements 2.2, 2.3, 2.4**

- [x] 3. Implement MarketRegimeDetector
  - [x] 3.1 Create MarketRegimeDetector class
    - Implement ATR-based volatility detection (HIGH_VOL > 150%, LOW_VOL < 50%)
    - Implement sideways detection (2% range over 20 candles)
    - Implement trending detection (aligned trends + strong momentum)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 3.2 Write property test for market regime classification
    - **Property 7: Market Regime Classification**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

- [x] 4. Implement TrendAlignmentEngine
  - [x] 4.1 Create TrendAlignmentEngine class
    - Implement weighted alignment calculation (4H=50%, 1H=30%, 15M=20%)
    - Implement conflict detection and penalty calculation
    - Implement alignment bonus (25 points when all aligned)
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - [x] 4.2 Write property tests for trend alignment
    - **Property 1: Trend Conflict Penalty**
    - **Property 2: Trend Alignment Bonus**
    - **Property 3: Conflicting Trend Signal Requirement**
    - **Validates: Requirements 1.1, 1.2, 1.3**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement VolumeConfirmationAnalyzer
  - [x] 6.1 Create VolumeConfirmationAnalyzer class
    - Implement minimum volume check (80% of average)
    - Implement volume spike detection (150% bonus)
    - Implement false move detection (significant price move + low volume)
    - Implement declining volume detection (5 consecutive candles)
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 6.2 Write property tests for volume confirmation
    - **Property 10: Minimum Volume Requirement**
    - **Property 11: Volume Spike Bonus**
    - **Property 12: False Move Detection**
    - **Validates: Requirements 4.1, 4.2, 4.3**

- [x] 7. Implement MomentumAnalyzer
  - [x] 7.1 Create MomentumAnalyzer class
    - Implement RSI range validation (LONG: 40-65, SHORT: 35-60)
    - Implement MACD momentum scoring
    - Implement RSI divergence detection
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  - [x] 7.2 Write property tests for momentum analysis
    - **Property 13: RSI Range Validation**
    - **Property 14: MACD Momentum Bonus**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

- [x] 8. Implement SupportResistanceDetector
  - [x] 8.1 Create SupportResistanceDetector class
    - Implement swing high/low detection
    - Implement proximity detection (0.5% threshold)
    - Implement breakout detection with volume confirmation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  - [x] 8.2 Write property tests for support/resistance
    - **Property 15: Support/Resistance Detection**
    - **Property 16: Support Entry Bonus**
    - **Property 17: Resistance Entry Penalty**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement ChoppyMarketDetector
  - [x] 10.1 Create ChoppyMarketDetector class
    - Implement EMA crossing counter (>4 in 20 candles = CHOPPY)
    - Implement ADX-based trend override (ADX < 20 = WEAK)
    - Implement signal alternation detection
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [x] 10.2 Write property tests for choppy detection
    - **Property 24: Choppy Market Detection**
    - **Property 25: Choppy Market Signal Block**
    - **Property 26: ADX Trend Override**
    - **Validates: Requirements 9.1, 9.2, 9.3**

- [x] 11. Implement BTCCorrelationEngine
  - [x] 11.1 Create BTCCorrelationEngine class
    - Implement BTC trend analysis on 4H timeframe
    - Implement confidence adjustment for altcoins (+/- 20 points)
    - Implement BTC volatility check (ATR > 200% = pause)
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  - [x] 11.2 Write property tests for BTC correlation
    - **Property 27: BTC Correlation Adjustment**
    - **Property 28: BTC Volatility Signal Block**
    - **Validates: Requirements 10.2, 10.3, 10.4**

- [x] 12. Implement AdaptiveStopCalculator
  - [x] 12.1 Create AdaptiveStopCalculator class
    - Implement regime-based multipliers (TRENDING=1.5x, HIGH_VOL=2.5x, LOW_VOL=1.0x)
    - Implement strength-based multipliers (STRONG=1.2x, WEAK=2.0x)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  - [x] 12.2 Write property tests for adaptive stops
    - **Property 18: Regime-Based Stop Loss**
    - **Property 19: Trend-Strength-Based Stop Loss**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

- [x] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Implement ContextWeightedScorer
  - [x] 14.1 Create ContextWeightedScorer class
    - Implement weighted scoring (Alignment=30%, Strength=20%, Volume=15%, Momentum=15%, S/R=10%, Regime=10%)
    - Implement confidence level classification (HIGH > 80, MEDIUM 65-80, LOW < 65)
    - _Requirements: 8.1, 8.2, 8.3_
  - [x] 14.2 Write property tests for scoring
    - **Property 20: Confidence Weight Distribution**
    - **Property 21: Minimum Confidence Threshold**
    - **Property 22: High Confidence Classification**
    - **Validates: Requirements 8.1, 8.2, 8.3**

- [x] 15. Implement CriticalFactorValidator
  - [x] 15.1 Create CriticalFactorValidator class
    - Implement trend alignment validation
    - Implement volume threshold validation
    - Implement weak 4H trend blocking
    - Implement sideways regime blocking
    - Implement choppy market blocking
    - _Requirements: 2.5, 3.5, 8.4, 9.2_
  - [x] 15.2 Write property tests for critical factor validation
    - **Property 6: Weak 4H Trend Signal Block**
    - **Property 8: Sideways Regime Signal Block**
    - **Property 23: Critical Factor Veto**
    - **Validates: Requirements 2.5, 3.5, 8.4**

- [x] 16. Implement EnhancedTAAnalyzer (Main Orchestrator)
  - [x] 16.1 Create EnhancedTAAnalyzer class
    - Integrate all component analyzers
    - Implement `analyze()` method that orchestrates the full analysis pipeline
    - Implement signal generation with all context
    - Implement comprehensive logging of component scores
    - _Requirements: All_
  - [x] 16.2 Write integration tests for EnhancedTAAnalyzer
    - Test full analysis pipeline with various market conditions
    - Test signal generation with aligned trends
    - Test signal blocking with conflicting trends
    - _Requirements: All_

- [x] 17. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 18. Integrate with Live Trading System
  - [x] 18.1 Update run_v3_live.py to use EnhancedTAAnalyzer
    - Replace TAAnalyzer import with EnhancedTAAnalyzer
    - Update analyzer initialization
    - Add BTC data fetching for correlation analysis
    - _Requirements: All_
  - [x] 18.2 Add enhanced logging and monitoring
    - Log all component scores for each analysis
    - Log market regime and trend alignment status
    - Log critical factor validation results
    - _Requirements: 8.5_

- [x] 19. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
