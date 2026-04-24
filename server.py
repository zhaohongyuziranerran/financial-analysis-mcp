"""Financial Analysis MCP Server - Entry Point for MCPize

Compatible with FastMCP 2.x+ and MCPize auto-detection.
"""

from fastmcp import FastMCP

# Create MCP server instance at module level for auto-detection
mcp = FastMCP(
    "financial-analysis-mcp",
    version="1.0.0",
    instructions="金融智能分析MCP Server - 覆盖A股/港股/美股/基金/期货/宏观/外汇/大宗商品，209个数据接口+AI分析。",
)


@mcp.tool()
async def analyze_stock(ts_code: str) -> str:
    """个股综合分析 - 行情+估值+财务+AI评级

    Args:
        ts_code: 股票代码，如 000001.SZ, 600519.SH
    """
    # Delegate to actual implementation
    from fin_analysis_mcp.server import analyze_stock as _analyze
    return await _analyze(ts_code)


@mcp.tool()
async def compare_stocks_tool(ts_codes: str) -> str:
    """多股对比分析"""
    from fin_analysis_mcp.server import compare_stocks_tool as _compare
    return await _compare(ts_codes)


@mcp.tool()
async def market_overview() -> str:
    """A股市场概览"""
    from fin_analysis_mcp.server import market_overview as _market
    return await _market()


@mcp.tool()
async def analyze_financials_tool(ts_code: str) -> str:
    """财报深度分析"""
    from fin_analysis_mcp.server import analyze_financials_tool as _fin
    return await _fin(ts_code)


@mcp.tool()
async def analyze_fund_tool(ts_code: str) -> str:
    """基金分析"""
    from fin_analysis_mcp.server import analyze_fund_tool as _fund
    return await _fund(ts_code)


@mcp.tool()
async def analyze_sector_tool(ts_code: str) -> str:
    """板块分析"""
    from fin_analysis_mcp.server import analyze_sector_tool as _sector
    return await _sector(ts_code)


@mcp.tool()
async def macro_overview() -> str:
    """宏观经济概览"""
    from fin_analysis_mcp.server import macro_overview as _macro
    return await _macro()


@mcp.tool()
async def money_flow_analysis(ts_code: str) -> str:
    """资金流向分析"""
    from fin_analysis_mcp.server import money_flow_analysis as _flow
    return await _flow(ts_code)


@mcp.tool()
async def limit_analysis(trade_date: str = None) -> str:
    """涨跌停分析"""
    from fin_analysis_mcp.server import limit_analysis as _limit
    return await _limit(trade_date)


@mcp.tool()
async def stock_screener(
    industry: str = None,
    min_roe: float = None,
    max_pe: float = None,
    min_market_cap: float = None,
    limit: int = 20,
) -> str:
    """智能选股"""
    from fin_analysis_mcp.server import stock_screener as _screener
    return await _screener(industry, min_roe, max_pe, min_market_cap, limit)


@mcp.tool()
async def query_neodata(query: str) -> str:
    """自然语言金融数据查询"""
    from fin_analysis_mcp.server import query_neodata as _query
    return await _query(query)


@mcp.tool()
async def query_financial_api(api_name: str, params: str = None, fields: str = None) -> str:
    """结构化金融数据查询"""
    from fin_analysis_mcp.server import query_financial_api as _api
    return await _api(api_name, params, fields)


@mcp.tool()
async def forex_and_commodities(fx_code: str = None) -> str:
    """外汇与大宗商品"""
    from fin_analysis_mcp.server import forex_and_commodities as _fx
    return await _fx(fx_code)


if __name__ == "__main__":
    mcp.run()
