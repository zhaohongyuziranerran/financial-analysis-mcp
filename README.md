# 金融智能分析MCP Server 🔥

> 覆盖A股/港股/美股/基金/期货/宏观/外汇/大宗商品，209个数据接口+AI智能分析

## ✨ 核心特性

- **209个金融数据接口**：基于NeoData，覆盖股票/指数/基金/期货/债券/宏观/外汇等15大类
- **AI智能分析层**：不卖原始数据，卖AI分析解读，合规变现
- **12个MCP工具**：个股分析/多股对比/市场概览/财报/基金/板块/宏观/资金/选股/涨跌停/自然语言查询/结构化查询
- **双模数据源**：自然语言API(快速查询) + 结构化API(精确控制)
- **FastMCP框架**：支持stdio(Claude Desktop)和SSE(Web)两种传输模式

## 🛠️ MCP工具列表

| 工具名 | 功能 | 示例 |
|--------|------|------|
| `analyze_stock` | 个股综合分析 | 000001.SZ |
| `compare_stocks_tool` | 多股对比 | 000001.SZ,600519.SH |
| `market_overview` | A股市场概览 | - |
| `analyze_financials_tool` | 财报深度分析 | 000001.SZ |
| `analyze_fund_tool` | 基金分析 | 110011.OF |
| `analyze_sector_tool` | 板块分析 | 885001.TI |
| `macro_overview` | 宏观经济概览 | - |
| `money_flow_analysis` | 资金流向分析 | 000001.SZ |
| `limit_analysis` | 涨跌停分析 | 20250423 |
| `stock_screener` | 智能选股 | min_roe=15,max_pe=30 |
| `query_neodata` | 自然语言金融查询 | "贵州茅台最新股价" |
| `query_financial_api` | 结构化金融查询 | daily,{"ts_code":"000001.SZ"} |
| `forex_and_commodities` | 外汇与大宗商品 | USDCNY |

## 📦 安装

```bash
# 从源码安装
cd financial-analysis-mcp
pip install -e .

# 或直接安装依赖
pip install fastmcp>=2.0.0 httpx>=0.27.0 pydantic>=2.0.0
```

## 🚀 启动

### 方式1: Claude Desktop (stdio模式)

在Claude Desktop配置文件中添加：

```json
{
  "mcpServers": {
    "fin-analysis": {
      "command": "python",
      "args": ["-m", "fin_analysis_mcp"],
      "env": {
        "NEODATA_TOKEN": "你的JWT Token"
      }
    }
  }
}
```

### 方式2: 命令行stdio

```bash
# 设置Token(一次性)
echo "你的JWT Token" > ~/.workbuddy/.neodata_token

# 启动Server
python -m fin_analysis_mcp
```

### 方式3: SSE模式(Web访问)

```bash
python -m fin_analysis_mcp --transport sse --port 8080
```

## 🔑 认证

需要NeoData JWT Token，获取方式：

1. 登录 WorkBuddy 平台，自动生成Token
2. Token存储路径：`~/.workbuddy/.neodata_token`
3. 或通过环境变量 `NEODATA_TOKEN` 传入

## 📊 数据覆盖

| 类别 | 接口数 | 主要接口 |
|------|--------|----------|
| 股票数据 | 98 | daily, income, balancesheet, cashflow, moneyflow |
| 指数专题 | 19 | index_daily, index_weight, sw_daily |
| 期货数据 | 15 | fut_basic, fut_daily, fut_holding |
| 债券专题 | 15 | cb_basic, cb_daily, repo_daily |
| ETF专题 | 8 | etf_basic, etf_share_size |
| 公募基金 | 8 | fund_nav, fund_portfolio |
| 宏观经济 | 13 | cn_gdp, cn_cpi, shibor |
| 美股数据 | 9 | us_daily, us_income |
| 外汇数据 | 2 | fx_daily |
| 港股数据 | 3 | hk_daily, hk_mins |
| 其他 | 18 | news, limit_list_d, top_list |

## 💰 变现策略

### 定价方案
| 层级 | 价格 | 功能 | 预估月收入 |
|------|------|------|-----------|
| 免费版 | $0 | 5次分析/天，基础数据 | 引流 |
| 基础版 | $9.9/月 | 50次分析/天，完整数据 | $1,000-3,000 |
| 专业版 | $49/月 | 无限分析，AI报告 | $5,000-15,000 |
| 企业版 | $199/月 | 批量查询，API调用 | $10,000-50,000 |

### 发布渠道
1. **MCPize** - MCP市场(85%开发者分成)
2. **Smithery** - 国际MCP市场
3. **mcp.so / mcpmarket.cn** - 国内MCP市场
4. **ClawHub** - 中国技能市场(85%分成)
5. **闲鱼/淘宝** - 国内零售

### 合规要点
- ✅ 卖分析不卖数据 - AI解读+评级+建议
- ✅ 所有输出附带免责声明
- ✅ 不提供直接投资建议，只提供参考分析
- ⚠️ 不直接转售NeoData原始数据

## 🏗️ 项目结构

```
financial-analysis-mcp/
├── pyproject.toml                    # 项目配置
├── README.md                         # 本文件
└── src/fin_analysis_mcp/
    ├── __init__.py                   # 包初始化
    ├── __main__.py                   # 入口点
    ├── server.py                     # MCP Server(12个工具)
    ├── neodata_client.py             # NeoData API客户端
    └── analyzers.py                  # AI分析引擎
```

## 🔧 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 格式化
black src/
```

## 📄 License

MIT

---

> ⚠️ 本工具提供的数据分析仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。


## 在线访问（推荐）

无需本地安装，直接在MCP客户端配置：

```json
{
  "mcpServers": {
    "financial-analysis-mcp": {
      "url": "http://www.mzse.com/finmcp"
    }
  }
}
```

## REST API

```bash
curl http://www.mzse.com/finmcp
```

## 部署状态

| 项目 | 地址 |
|------|------|
| 域名 | http://www.mzse.com/finmcp |
| GitHub | https://github.com/zhaohongyuziranerran/financial-analysis-mcp |
