# Implementation Plan

- [x] 1. Create Unified Configuration System
  - [x] 1.1 Create root config.py with UnifiedConfig dataclass
    - Define all spot_* prefixed parameters
    - Define all futures_* prefixed parameters
    - Define global_* risk parameters
    - Define health monitoring parameters
    - _Requirements: 2.1, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 8.1_
  - [x] 1.2 Write property test for config loading completeness
    - **Property 2: Configuration loading completeness**
    - **Validates: Requirements 2.1, 2.2**
  - [x] 1.3 Create EnvConfig loader for .env file
    - Load BINANCE_API_KEY, BINANCE_API_SECRET
    - Load SPOT_ENABLED, FUTURES_ENABLED toggles
    - Load TELEGRAM_* settings
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 1.4 Write property test for missing config validation
    - **Property 3: Missing config validation**
    - **Validates: Requirements 2.4, 3.4**

- [x] 2. Implement Capital Allocator
  - [x] 2.1 Create CapitalAllocator class
    - Validate total allocation <= 100%
    - Calculate USD allocation per engine
    - Handle disabled engine reallocation
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  - [x] 2.2 Write property test for capital allocation validation
    - **Property 5: Capital allocation validation**
    - **Validates: Requirements 7.2**
  - [x] 2.3 Write property test for capital allocation correctness
    - **Property 6: Capital allocation correctness**
    - **Validates: Requirements 7.1, 7.4**
  - [x] 2.4 Write property test for disabled engine reallocation
    - **Property 7: Disabled engine capital reallocation**
    - **Validates: Requirements 7.3**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement Global Risk Monitor
  - [x] 4.1 Create GlobalRiskMonitor class
    - Track combined daily P&L across engines
    - Track portfolio peak value for drawdown calculation
    - Implement circuit breaker with cooldown
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [x] 4.2 Write property test for daily loss limit enforcement
    - **Property 8: Global daily loss limit enforcement**
    - **Validates: Requirements 8.2**
  - [x] 4.3 Write property test for drawdown protection
    - **Property 9: Global drawdown protection**
    - **Validates: Requirements 8.3**

- [x] 5. Implement Health Monitor
  - [x] 5.1 Create HealthMonitor class
    - Track last heartbeat per engine
    - Detect warning threshold (60s)
    - Detect restart threshold (300s)
    - Track restart attempts
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [x] 5.2 Write property test for heartbeat timeout detection
    - **Property 10: Heartbeat timeout detection**
    - **Validates: Requirements 9.2, 9.3**

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement Base Engine
  - [x] 7.1 Create BaseEngine abstract class
    - Define start(), stop(), get_status() abstract methods
    - Implement heartbeat sending mechanism
    - Implement graceful shutdown handling
    - _Requirements: 4.1, 10.2_
  - [x] 7.2 Write property test for graceful shutdown
    - **Property 11: Graceful shutdown completion**
    - **Validates: Requirements 10.2**

- [x] 8. Implement Spot Engine
  - [x] 8.1 Create BinanceSpotClient
    - Implement spot buy/sell order methods
    - Implement balance and position queries
    - Handle API rate limiting
    - _Requirements: 5.4_
  - [x] 8.2 Create SpotEngine class extending BaseEngine
    - Implement scan loop for spot opportunities
    - Implement position monitoring loop
    - Use spot_* config values only
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - [x] 8.3 Implement SpotStrategy
    - Simple momentum-based spot strategy
    - Use spot_stop_loss_pct and spot_take_profit_pct
    - _Requirements: 5.2_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Refactor Futures Engine
  - [x] 10.1 Create FuturesEngine class extending BaseEngine
    - Refactor existing run_bot.py logic into FuturesEngine
    - Use futures_* config values only
    - Integrate with existing profitable trading components
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  - [x] 10.2 Update FuturesEngine to use UnifiedConfig
    - Replace hardcoded values with config lookups
    - Ensure all parameters come from config.py
    - _Requirements: 2.2, 6.4_

- [x] 11. Implement Orchestrator
  - [x] 11.1 Create Orchestrator class
    - Initialize ConfigManager and EnvConfig
    - Initialize CapitalAllocator, GlobalRiskMonitor, HealthMonitor
    - _Requirements: 1.1, 1.2_
  - [x] 11.2 Write property test for engine spawning
    - **Property 1: Engine spawning based on configuration**
    - **Validates: Requirements 1.1, 1.3**
  - [x] 11.3 Implement engine spawning logic
    - Spawn enabled engines as async tasks
    - Skip disabled engines
    - Log engine status on startup
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 11.4 Write property test for fault isolation
    - **Property 4: Engine fault isolation**
    - **Validates: Requirements 4.2, 4.3**
  - [x] 11.5 Implement monitoring loop
    - Check engine health periodically
    - Check global risk limits
    - Trigger circuit breaker if needed
    - _Requirements: 8.2, 8.3, 9.1, 9.2, 9.3_
  - [x] 11.6 Implement graceful shutdown
    - Handle SIGINT/SIGTERM signals
    - Signal all engines to stop
    - Wait for engines to complete
    - Log final portfolio state
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Create Main Entry Point
  - [x] 13.1 Create main.py
    - Load config and env
    - Create and start Orchestrator
    - Handle top-level exceptions
    - _Requirements: 1.1_
  - [x] 13.2 Update start_backend.sh
    - Activate venv
    - Set PYTHONPATH
    - Run main.py
    - _Requirements: 1.1_

- [x] 14. Update .env Template
  - [x] 14.1 Create .env.example with all required variables
    - BINANCE_API_KEY, BINANCE_API_SECRET
    - SPOT_ENABLED, FUTURES_ENABLED
    - TELEGRAM_* settings
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 15. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

