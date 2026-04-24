# FinMCP Installation Guide for LLMs

## Prerequisites

- Python 3.10 or higher
- pip package manager
- NeoData JWT Token (from WorkBuddy platform)

## Step 1: Clone the Repository

```bash
git clone https://github.com/zhaohongyuziranerran/financial-analysis-mcp.git
cd financial-analysis-mcp
```

## Step 2: Install Dependencies

```bash
pip install fastmcp>=2.0.0 httpx>=0.27.0 pydantic>=2.0.0
```

## Step 3: Configure Authentication

Set your NeoData JWT Token:

```bash
export NEODATA_TOKEN="your-jwt-token"
```

Or create a token file:

```bash
mkdir -p ~/.workbuddy
echo "your-jwt-token" > ~/.workbuddy/.neodata_token
```

## Step 4: Start the Server

### Local Mode (Claude Desktop)

```bash
python -m fin_analysis_mcp
```

### Remote Mode (SSE/Web)

```bash
python -m fin_analysis_mcp --transport sse --port 8080
```

## Step 5: Configure Client

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fin-analysis": {
      "command": "python",
      "args": ["-m", "fin_analysis_mcp"],
      "env": {
        "NEODATA_TOKEN": "your-jwt-token"
      }
    }
  }
}
```

### Remote Client

```json
{
  "mcpServers": {
    "fin-analysis": {
      "url": "http://101.32.191.236/finmcp"
    }
  }
}
```

## Verification

Test the server:

```bash
curl -X POST http://localhost:8080/finmcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

## Tools Overview

| Tool | Purpose |
|------|---------|
| analyze_stock | Individual stock analysis |
| compare_stocks_tool | Multi-stock comparison |
| market_overview | A-share market overview |
| analyze_financials_tool | Financial report analysis |
| analyze_fund_tool | Fund analysis |
| analyze_sector_tool | Sector analysis |
| macro_overview | Macro economy overview |
| money_flow_analysis | Capital flow analysis |
| limit_analysis | Limit up/down analysis |
| stock_screener | Stock screening |
| query_neodata | Natural language query |
| query_financial_api | Structured API query |
| forex_and_commodities | Forex & commodities |

## Troubleshooting

- **Token expired**: Re-authenticate with WorkBuddy platform
- **Module not found**: Ensure you're in the project root directory
- **Port 8080 in use**: Change port with `--port 8081`
