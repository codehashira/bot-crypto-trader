# Exchange API Research for Cryptocurrency Trading

## Bybit API (V5)

### Overview
- V5 API unifies APIs of various trading products into one set of specifications
- Provides capability to trade Spot, Derivatives, and Options with a single API
- Supports both Unified Trading Account and Classic Account types

### Key Features
- **Product Lines Alignment**: Same API can be used for different products by specifying category parameter
- **Enhanced Capital Efficiency**: Allows sharing and cross-utilization of funds across different products
- **Unified Account Borrowing**: Supports borrowing across unified account mode
- **Portfolio Margin Mode**: Supports combined margin between different contract types

### API Structure
- Clear path definitions with improved clarity and reduced ambiguity
- Divided into modules:
  - v5/market/: Candlestick, orderbook, ticker, platform transaction data
  - v5/order/: Order management
  - v5/position/: Position management
  - v5/account/: Single account operations
  - v5/asset/: Operations across multiple accounts
  - v5/spot-lever-token/: Leveraged Tokens on Spot
  - v5/spot-margin-trade/: Margin Trading on Spot

### Implementation Considerations
- Can cancel all Derivatives orders settled by the same currency with `settleCoin`
- Provides insurance fund interface for checking insurance fund updates
- Documentation has been improved for clarity and better explanations

## MEXC API

### Overview
- MEXC provides order matching systems, account management, and settlement systems
- Currently transitioning from V2 to V3 API (V2 being discontinued)
- Supports both REST and WebSocket APIs for spot and futures trading

### Key Features
- **API Key Setup**: Requires API Key for most endpoints with recommended IP restrictions
- **SDK Support**: Provides SDKs in multiple languages (Python, DotNET, Java, Javascript, Go)
- **Postman Collections**: Offers Postman collection for quick-start into using the API

### Security Considerations
- Never share API key/secret key with anyone
- Recommended to set IP restrictions on API keys
- If API keys are accidentally shared, delete them immediately and create new ones

### Implementation Notes
- Check required permissions when creating an API Key
- MEXC Broker functionality available for partners
- V3 API offers enhanced functionality, greater stability, and higher efficiency compared to V2

## DEX Platform APIs

### Bitquery DEX Trades API

#### Overview
- Provides trading-related data from different DEXs (Uniswap, Pancakeswap, 0x, etc.)
- Offers historical and real-time trades and pricing information for tokens
- Allows filtering by DEXs, protocols, tokens, trades, pools, etc.

#### Key Features
- **DEX Trades Cube**: Represents every swap of tokens on decentralized exchanges
  - Good for queries based on protocol or smart contracts
  - Provides total count of trades, gas spending, and usage dynamics
  
- **DEX Trades By Tokens**: Exposes trades relative to the token
  - Each trade represented by 2 records (one for each token in the trade)
  - Useful for building queries by tokens or token pairs
  - Can be used for OHLC graph building with time intervals

#### Implementation Considerations
- DEX Trades By Tokens has twice as many records for DEX trades
- Always use at least one filter by token when querying DEX Trades By Tokens
- Use interval argument for date/time to build OHLC graphs

### Other DEX API Options

- **DEX Screener API**: Provides token profiles and market data with rate limits
- **OKX DEX API**: All-in-one trading aggregator for multi-chain and cross-chain transactions
- **GeckoTerminal API**: Offers live, on-chain market data like token prices, OHLC, trading volume, etc.

## Implementation Strategy for Our Trading Bot

### Exchange Selection
- **CEX Integration**: 
  - Implement Bybit V5 API as primary CEX due to unified API structure
  - Add MEXC V3 API as secondary CEX option

- **DEX Integration**:
  - Use Bitquery DEX Trades API for accessing multiple DEXs through a single interface
  - Consider GeckoTerminal API for additional price and market data

### API Usage Approach
- Create abstraction layer to standardize interactions across different exchanges
- Implement websocket connections for real-time data where available
- Handle rate limiting and error responses appropriately
- Store API keys securely with proper permission restrictions
