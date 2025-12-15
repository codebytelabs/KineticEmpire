# Requirements Document

## Introduction

This specification defines a unified trading system that runs both Spot and Futures trading strategies concurrently within a single bot instance. The system centralizes all strategy configuration in a root `config.py` file while keeping API credentials and environment-specific settings in `.env`. The bot will run Spot and Futures engines in separate threads/async tasks to ensure isolation and prevent interference between trading modes.

The goal is to provide users with a single entry point (`./start_backend.sh`) that launches both trading modes, with all tunable parameters accessible from two files: `config.py` (strategy variables) and `.env` (API keys and environment settings).

## Glossary

- **Spot Trading**: Buying/selling actual cryptocurrency assets without leverage
- **Futures Trading**: Trading derivative contracts with leverage (2x-125x)
- **Engine**: An isolated trading loop that manages positions for one market type
- **Orchestrator**: Main coordinator that spawns and manages multiple engines
- **Thread Pool**: Collection of worker threads for concurrent execution
- **AsyncIO**: Python's asynchronous I/O framework for concurrent operations
- **Capital Allocation**: Percentage of total portfolio assigned to each engine
- **Circuit Breaker**: Safety mechanism that halts trading after excessive losses

## Requirements

### Requirement 1: Unified Bot Entry Point

**User Story:** As a trader, I want a single command to start both Spot and Futures trading, so that I don't need to manage multiple processes.

#### Acceptance Criteria

1. WHEN the user runs `./start_backend.sh` THEN the Orchestrator SHALL spawn both Spot and Futures engines
2. WHEN the bot starts THEN the Orchestrator SHALL log which engines are enabled based on configuration
3. WHEN an engine is disabled in config THEN the Orchestrator SHALL skip spawning that engine
4. WHEN both engines are running THEN the Orchestrator SHALL display combined portfolio status

### Requirement 2: Centralized Strategy Configuration

**User Story:** As a trader, I want all strategy parameters in a single `config.py` file, so that I can tune the bot without searching through multiple files.

#### Acceptance Criteria

1. WHEN the bot loads configuration THEN the Config_Manager SHALL read all strategy parameters from root `config.py`
2. WHEN a strategy parameter is hardcoded in source files THEN the Config_Manager SHALL override it with the config.py value
3. WHEN config.py is modified THEN the bot SHALL use new values on next restart without code changes
4. WHEN a required config value is missing THEN the Config_Manager SHALL raise a clear error with the missing field name

### Requirement 3: Environment-Based API Configuration

**User Story:** As a trader, I want API keys and environment settings in `.env`, so that I can keep secrets separate from strategy logic.

#### Acceptance Criteria

1. WHEN the bot starts THEN the Config_Manager SHALL load API credentials from `.env` file
2. WHEN `.env` contains SPOT_ENABLED=true THEN the Orchestrator SHALL enable the Spot engine
3. WHEN `.env` contains FUTURES_ENABLED=true THEN the Orchestrator SHALL enable the Futures engine
4. WHEN API keys are missing THEN the Config_Manager SHALL raise an error before starting any engine

### Requirement 4: Isolated Engine Execution

**User Story:** As a trader, I want Spot and Futures engines to run independently, so that a failure in one doesn't affect the other.

#### Acceptance Criteria

1. WHEN both engines are running THEN each engine SHALL execute in its own asyncio task or thread
2. WHEN the Spot engine encounters an error THEN the Futures engine SHALL continue operating
3. WHEN the Futures engine encounters an error THEN the Spot engine SHALL continue operating
4. WHEN an engine crashes THEN the Orchestrator SHALL log the error and optionally restart the engine

### Requirement 5: Spot Trading Strategy Configuration

**User Story:** As a trader, I want to configure Spot-specific strategy parameters, so that I can optimize for spot market conditions.

#### Acceptance Criteria

1. WHEN configuring Spot strategy THEN config.py SHALL contain spot_enabled, spot_capital_pct, spot_max_positions
2. WHEN configuring Spot risk THEN config.py SHALL contain spot_position_size_pct, spot_stop_loss_pct, spot_take_profit_pct
3. WHEN configuring Spot symbols THEN config.py SHALL contain spot_watchlist as a list of trading pairs
4. WHEN Spot engine starts THEN it SHALL use only spot-prefixed configuration values

### Requirement 6: Futures Trading Strategy Configuration

**User Story:** As a trader, I want to configure Futures-specific strategy parameters, so that I can optimize for leveraged trading.

#### Acceptance Criteria

1. WHEN configuring Futures strategy THEN config.py SHALL contain futures_enabled, futures_capital_pct, futures_max_positions
2. WHEN configuring Futures risk THEN config.py SHALL contain futures_leverage_min, futures_leverage_max, futures_position_size_pct
3. WHEN configuring Futures regime THEN config.py SHALL contain futures_regime_adx_trending, futures_regime_adx_sideways
4. WHEN Futures engine starts THEN it SHALL use only futures-prefixed configuration values

### Requirement 7: Capital Allocation Between Engines

**User Story:** As a trader, I want to allocate portfolio percentage to each engine, so that I can balance risk between Spot and Futures.

#### Acceptance Criteria

1. WHEN config specifies spot_capital_pct=40 and futures_capital_pct=60 THEN the Orchestrator SHALL allocate 40% to Spot and 60% to Futures
2. WHEN total allocation exceeds 100% THEN the Config_Manager SHALL raise a validation error
3. WHEN an engine is disabled THEN its capital allocation SHALL be available to the other engine
4. WHEN calculating position sizes THEN each engine SHALL use only its allocated capital

### Requirement 8: Shared Risk Management

**User Story:** As a trader, I want portfolio-wide risk limits, so that combined losses don't exceed my risk tolerance.

#### Acceptance Criteria

1. WHEN configuring global risk THEN config.py SHALL contain global_daily_loss_limit_pct, global_max_drawdown_pct
2. WHEN combined daily loss exceeds global_daily_loss_limit_pct THEN both engines SHALL halt new trades
3. WHEN portfolio drawdown exceeds global_max_drawdown_pct THEN both engines SHALL close all positions
4. WHEN risk limit is triggered THEN the Orchestrator SHALL log the event and notify via Telegram if enabled

### Requirement 9: Engine Health Monitoring

**User Story:** As a trader, I want to monitor engine health, so that I know if something goes wrong.

#### Acceptance Criteria

1. WHEN engines are running THEN the Orchestrator SHALL track last heartbeat timestamp for each engine
2. WHEN an engine hasn't sent heartbeat for 60 seconds THEN the Orchestrator SHALL log a warning
3. WHEN an engine hasn't sent heartbeat for 300 seconds THEN the Orchestrator SHALL attempt restart
4. WHEN displaying status THEN the Orchestrator SHALL show engine state (running/stopped/error)

### Requirement 10: Graceful Shutdown

**User Story:** As a trader, I want the bot to shut down gracefully, so that positions are properly managed on exit.

#### Acceptance Criteria

1. WHEN user sends SIGINT (Ctrl+C) THEN the Orchestrator SHALL signal all engines to stop
2. WHEN stopping THEN each engine SHALL complete current operations before exiting
3. WHEN stopping THEN the Orchestrator SHALL log final portfolio state for each engine
4. WHEN all engines have stopped THEN the Orchestrator SHALL exit cleanly with status code 0

