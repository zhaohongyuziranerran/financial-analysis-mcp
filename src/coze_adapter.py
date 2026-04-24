"""FinMCP REST API Adapter for Coze

Coze云侧插件需要标准REST API（不是MCP协议）。
此适配器将Coze的HTTP请求转换为MCP调用，返回纯文本结果。

部署在同一VPS上，端口9002。
"""
import httpx
import json
import asyncio
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

app = FastAPI(title="FinMCP Coze Adapter", version="1.0.0")

# CORS for Coze
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MCP_URL = "http://localhost:9001/finmcp"
MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


class MCPClient:
    """MCP Streamable HTTP Client"""

    def __init__(self):
        self.session_id = None
        self.request_id = 0

    async def _next_id(self) -> int:
        self.request_id += 1
        return self.request_id

    async def initialize(self) -> bool:
        """Initialize MCP session"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(MCP_URL, headers=MCP_HEADERS, json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": await self._next_id(),
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "coze-adapter", "version": "1.0.0"}
                }
            })
            # Extract session ID from response headers
            self.session_id = resp.headers.get("mcp-session-id")
            print(f"MCP initialized, session: {self.session_id}")
            
            # Send initialized notification
            headers = {**MCP_HEADERS}
            if self.session_id:
                headers["mcp-session-id"] = self.session_id
            await client.post(MCP_URL, headers=headers, json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            })
            return True

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call an MCP tool and return text result"""
        async with httpx.AsyncClient(timeout=60) as client:
            headers = {**MCP_HEADERS}
            if self.session_id:
                headers["mcp-session-id"] = self.session_id

            resp = await client.post(MCP_URL, headers=headers, json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": await self._next_id(),
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                }
            })

            # Parse SSE or JSON response
            text = resp.text
            result = None
            
            # Try parsing as JSON first
            try:
                data = json.loads(text)
                if "result" in data:
                    content = data["result"].get("content", [])
                    if content and isinstance(content, list):
                        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                        result = "\n".join(texts)
                    elif isinstance(data["result"], str):
                        result = data["result"]
            except json.JSONDecodeError:
                pass

            # Try parsing as SSE
            if result is None:
                for line in text.split("\n"):
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if "result" in data:
                                content = data["result"].get("content", [])
                                if content and isinstance(content, list):
                                    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                                    result = "\n".join(texts)
                        except json.JSONDecodeError:
                            continue

            return result or "数据获取失败，请稍后重试"


# Global client
_mcp_client: Optional[MCPClient] = None


async def get_client() -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
        await _mcp_client.initialize()
    return _mcp_client


# ========== Coze API Endpoints ==========

class AnalyzeStockInput(BaseModel):
    ts_code: str = Field(description="股票代码(带交易所后缀)或股票名称，如 000001.SZ 或 贵州茅台")

@app.post("/analyze_stock", summary="个股综合分析", description="个股综合分析 - 行情+估值+财务+AI评级")
async def api_analyze_stock(data: AnalyzeStockInput):
    client = await get_client()
    result = await client.call_tool("analyze_stock", {"ts_code": data.ts_code})
    return {"result": result}


class CompareStocksInput(BaseModel):
    ts_codes: str = Field(description="股票代码列表(逗号分隔)，如 000001.SZ,600519.SH")

@app.post("/compare_stocks_tool", summary="多股对比分析", description="同时对比多只股票的关键指标")
async def api_compare_stocks(data: CompareStocksInput):
    client = await get_client()
    result = await client.call_tool("compare_stocks_tool", {"ts_codes": data.ts_codes})
    return {"result": result}


@app.post("/market_overview", summary="A股市场概览", description="主要指数+北向资金+涨跌停+市场情绪")
async def api_market_overview():
    client = await get_client()
    result = await client.call_tool("market_overview", {})
    return {"result": result}


class AnalyzeFinancialsInput(BaseModel):
    ts_code: str = Field(description="股票代码，如 000001.SZ")

@app.post("/analyze_financials_tool", summary="财报深度分析", description="利润表+资产负债表+现金流+财务健康评级")
async def api_analyze_financials(data: AnalyzeFinancialsInput):
    client = await get_client()
    result = await client.call_tool("analyze_financials_tool", {"ts_code": data.ts_code})
    return {"result": result}


class AnalyzeFundInput(BaseModel):
    ts_code: str = Field(description="基金代码，如 110011.OF")

@app.post("/analyze_fund_tool", summary="基金分析", description="净值表现+基金概况")
async def api_analyze_fund(data: AnalyzeFundInput):
    client = await get_client()
    result = await client.call_tool("analyze_fund_tool", {"ts_code": data.ts_code})
    return {"result": result}


class AnalyzeSectorInput(BaseModel):
    ts_code: str = Field(description="板块代码或名称，如 885001.TI 或 白酒")

@app.post("/analyze_sector_tool", summary="板块分析", description="行业/概念板块行情+资金+成分股")
async def api_analyze_sector(data: AnalyzeSectorInput):
    client = await get_client()
    result = await client.call_tool("analyze_sector_tool", {"ts_code": data.ts_code})
    return {"result": result}


@app.post("/macro_overview", summary="宏观经济概览", description="GDP/CPI/PPI/Shibor利率")
async def api_macro_overview():
    client = await get_client()
    result = await client.call_tool("macro_overview", {})
    return {"result": result}


class MoneyFlowInput(BaseModel):
    ts_code: str = Field(description="股票代码如000001.SZ，或输入market查看大盘资金")

@app.post("/money_flow_analysis", summary="资金流向分析", description="个股资金流+北向资金+融资融券")
async def api_money_flow(data: MoneyFlowInput):
    client = await get_client()
    result = await client.call_tool("money_flow_analysis", {"ts_code": data.ts_code})
    return {"result": result}


class LimitAnalysisInput(BaseModel):
    trade_date: Optional[str] = Field(default=None, description="交易日期YYYYMMDD，不填默认最近交易日")

@app.post("/limit_analysis", summary="涨跌停分析", description="涨停/跌停/炸板/龙虎榜")
async def api_limit_analysis(data: LimitAnalysisInput):
    client = await get_client()
    args = {}
    if data.trade_date:
        args["trade_date"] = data.trade_date
    result = await client.call_tool("limit_analysis", args)
    return {"result": result}


class StockScreenerInput(BaseModel):
    industry: Optional[str] = Field(default=None, description="行业筛选，如 银行、白酒、半导体")
    min_roe: Optional[float] = Field(default=None, description="最低ROE(%)")
    max_pe: Optional[float] = Field(default=None, description="最高PE")
    min_market_cap: Optional[float] = Field(default=None, description="最低市值(亿元)")

@app.post("/stock_screener", summary="智能选股", description="多条件筛选股票")
async def api_stock_screener(data: StockScreenerInput):
    client = await get_client()
    args = {}
    if data.industry: args["industry"] = data.industry
    if data.min_roe: args["min_roe"] = data.min_roe
    if data.max_pe: args["max_pe"] = data.max_pe
    if data.min_market_cap: args["min_market_cap"] = data.min_market_cap
    result = await client.call_tool("stock_screener", args)
    return {"result": result}


class QueryNeodataInput(BaseModel):
    query: str = Field(description="自然语言查询，如 贵州茅台最新股价")

@app.post("/query_neodata", summary="自然语言金融数据查询", description="用自然语言获取任意金融数据")
async def api_query_neodata(data: QueryNeodataInput):
    client = await get_client()
    result = await client.call_tool("query_neodata", {"query": data.query})
    return {"result": result}


class ForexInput(BaseModel):
    fx_code: Optional[str] = Field(default=None, description="外汇代码如USDCNY，不填返回主要汇率")

@app.post("/forex_and_commodities", summary="外汇与大宗商品", description="外汇汇率+黄金+大宗商品行情")
async def api_forex(data: ForexInput):
    client = await get_client()
    args = {}
    if data.fx_code: args["fx_code"] = data.fx_code
    result = await client.call_tool("forex_and_commodities", args)
    return {"result": result}


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "service": "FinMCP Coze Adapter", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9002)
