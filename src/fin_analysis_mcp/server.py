"""金融智能分析MCP Server

基于NeoData 209个金融数据接口 + AI智能分析层
覆盖A股/港股/美股/基金/期货/宏观/外汇/大宗商品

启动方式:
    # stdio模式(Claude Desktop等)
    python -m fin_analysis_mcp

    # SSE模式(Web访问)
    python -m fin_analysis_mcp --transport sse --port 8080
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Optional

from fastmcp import FastMCP

from .neodata_client import NeoDataClient
from .analyzers import (
    analyze_stock_profile,
    analyze_market_overview,
    analyze_financials,
    analyze_fund,
    analyze_sector,
    analyze_macro,
    analyze_money_flow,
    analyze_limit,
    compare_stocks,
)

# ========== 创建MCP Server ==========
mcp = FastMCP(
    "fin-analysis-mcp",
    version="1.0.0",
    instructions="金融智能分析MCP Server - A股/港股/美股/基金/期货/宏观/外汇，209个数据接口+AI分析。提供个股分析、市场概览、财报分析、基金分析、板块分析、宏观经济、资金流向、智能选股、涨跌停分析、外汇商品等12个工具。",
)

# 全局客户端
_client: Optional[NeoDataClient] = None


def _get_client() -> NeoDataClient:
    """获取或创建NeoData客户端
    
    Token获取优先级:
    1. 环境变量 NEODATA_TOKEN
    2. ~/.workbuddy/.neodata_token 文件
    3. 自动获取(通过codebuddy.cn认证)
    """
    global _client
    if _client is None:
        token = os.getenv("NEODATA_TOKEN")
        if not token:
            from pathlib import Path
            tf = Path.home() / ".workbuddy" / ".neodata_token"
            if tf.exists():
                token = tf.read_text().strip()
        _client = NeoDataClient(token=token if token else None)
    return _client


def _parse_api_response(resp: dict) -> dict:
    """解析结构化API响应"""
    if resp.get("code") != 0:
        return {"error": resp.get("msg", "未知错误"), "code": resp.get("code", -1)}
    data = resp.get("data", {})
    fields = data.get("fields", [])
    items = data.get("items", [])
    # 转为字典列表
    result = []
    for item in items:
        row = {}
        for i, field in enumerate(fields):
            row[field] = item[i] if i < len(item) else None
        result.append(row)
    return {"fields": fields, "data": result, "count": len(result)}


def _get_trade_date(days_ago: int = 0) -> str:
    """获取N天前的日期(YYYYMMDD格式)"""
    d = datetime.now() - timedelta(days=days_ago)
    return d.strftime("%Y%m%d")


# ========== MCP工具定义 ==========

def _parse_nl_stock_data(nl_resp: dict) -> str:
    """解析NL API返回的股票数据，生成分析报告"""
    if nl_resp.get("code") != "200" and nl_resp.get("code") != 200:
        return f"数据获取失败: {nl_resp.get('msg', '未知错误')}"

    data = nl_resp.get("data", {})
    api_data = data.get("apiData", {})
    entities = api_data.get("entity", [])
    api_recall = api_data.get("apiRecall", [])
    doc_data = data.get("docData", {})
    doc_recall = doc_data.get("docRecall", [])

    # 提取股票名称
    stock_name = ""
    stock_code = ""
    if entities:
        stock_code = entities[0].get("name", "")
        stock_name = entities[0].get("code", "")

    lines = [f"## {stock_name}({stock_code}) 综合分析"]

    # 解析各类API数据
    for recall in api_recall:
        rtype = recall.get("type", "")
        desc = recall.get("desc", "")
        content = recall.get("content", "")

        if not content:
            continue

        # 根据类型生成不同标题
        type_names = {
            "股票实时行情": "实时行情",
            "basic_info": "行情与基本面",
            "hk_stock_profile": "股票简况",
            "stock_big_event": "大事件",
            "fund_aggregation": "资金聚合",
            "fund_history": "资金历史",
        }
        title = type_names.get(rtype, desc or rtype)
        lines.append(f"\n### {title}")
        lines.append(content)

    # 相关资讯
    if doc_recall:
        lines.append("\n### 相关资讯")
        for dr in doc_recall[:3]:
            docs = dr.get("docList", [])
            for doc in docs[:3]:
                title_text = doc.get("title", "")
                source = doc.get("source", "")
                content = doc.get("content", "")[:200]
                pub_time = doc.get("publishTime", 0)
                time_str = ""
                if pub_time:
                    from datetime import datetime as dt
                    try:
                        time_str = dt.fromtimestamp(pub_time).strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                lines.append(f"- **{title_text}** ({source} {time_str})")
                if content:
                    lines.append(f"  {content}...")

    # 生成AI评级
    lines.append("\n### AI综合评级")
    lines.append(_generate_nl_rating(api_recall))

    lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。")
    return "\n".join(lines)


def _generate_nl_rating(api_recall: list) -> str:
    """从NL API数据生成评级"""
    score = 50  # 基准分
    signals = []

    for recall in api_recall:
        content = recall.get("content", "")
        rtype = recall.get("type", "")

        # 从行情数据提取信号
        if "行情" in rtype or "basic_info" in rtype:
            # 涨跌幅
            import re
            pct_match = re.search(r"涨跌幅[：:]\s*(-?[\d.]+)%", content)
            if pct_match:
                try:
                    pct = float(pct_match.group(1))
                    if pct > 2:
                        score += 10
                        signals.append(f"今日涨幅{pct}%偏强")
                    elif pct < -2:
                        score -= 10
                        signals.append(f"今日跌幅{pct}%偏弱")
                except ValueError:
                    pass

            # 换手率
            turnover_match = re.search(r"换手率[：:]\s*([\d.]+)%", content)
            if turnover_match:
                try:
                    turnover = float(turnover_match.group(1))
                    if turnover > 5:
                        signals.append(f"换手率{turnover}%活跃")
                    elif turnover < 1:
                        signals.append(f"换手率{turnover}%低迷")
                except ValueError:
                    pass

            # 市盈率
            pe_match = re.search(r"市盈[率比率]*[：:]\s*([\d.]+)", content)
            if pe_match:
                try:
                    pe = float(pe_match.group(1))
                    if pe < 15:
                        score += 15
                        signals.append(f"PE={pe}偏低估")
                    elif pe > 50:
                        score -= 10
                        signals.append(f"PE={pe}偏高估")
                    else:
                        score += 5
                        signals.append(f"PE={pe}中等")
                except ValueError:
                    pass

    # 评级映射
    if score >= 80:
        rating = "🟢 强烈关注"
    elif score >= 65:
        rating = "🟡 值得关注"
    elif score >= 50:
        rating = "⚪ 中性观望"
    elif score >= 35:
        rating = "🟠 谨慎观望"
    else:
        rating = "🔴 风险提示"

    signal_str = " | ".join(signals) if signals else "无明显信号"
    return f"综合评分: {score}/100 | {rating}\n信号: {signal_str}"


@mcp.tool()
async def analyze_stock(ts_code: str) -> str:
    """个股综合分析 - 行情+估值+财务+AI评级

    Args:
        ts_code: 股票代码(带交易所后缀)，如 000001.SZ, 600519.SH, 300750.SZ
                 也支持股票名称，如 "贵州茅台"
    """
    client = _get_client()

    # 优先使用NL API（已验证可用）
    try:
        # 如果ts_code像代码(含.号)，构造查询语句
        if "." in ts_code:
            query = f"{ts_code}最新行情和基本面分析"
        else:
            query = f"{ts_code}最新行情和基本面分析"

        nl_resp = await client.query_nl(query)

        if nl_resp.get("code") == "200" or nl_resp.get("code") == 200:
            return _parse_nl_stock_data(nl_resp)
    except Exception as e:
        pass  # NL API失败，尝试结构化API

    # 降级到结构化API
    try:
        basic_resp, daily_resp, daily_basic_resp, fina_resp = await asyncio.gather(
            client.get_stock_basic(ts_code=ts_code),
            client.get_stock_daily(ts_code=ts_code, start_date=_get_trade_date(30)),
            client.get_daily_basic(ts_code=ts_code, trade_date=_get_trade_date()),
            client.get_fina_indicator(ts_code=ts_code),
            return_exceptions=True,
        )

        basic_info = {}
        if isinstance(basic_resp, dict) and basic_resp.get("code") == 0:
            parsed = _parse_api_response(basic_resp)
            if parsed.get("data"):
                basic_info = parsed["data"][0]

        daily_list = []
        if isinstance(daily_resp, dict) and daily_resp.get("code") == 0:
            parsed = _parse_api_response(daily_resp)
            daily_list = parsed.get("data", [])

        daily_basic = {}
        if isinstance(daily_basic_resp, dict) and daily_basic_resp.get("code") == 0:
            parsed = _parse_api_response(daily_basic_resp)
            if parsed.get("data"):
                daily_basic = parsed["data"][0]

        fina_indicator = {}
        if isinstance(fina_resp, dict) and fina_resp.get("code") == 0:
            parsed = _parse_api_response(fina_resp)
            if parsed.get("data"):
                fina_indicator = parsed["data"][0]

        if basic_info or daily_list:
            return analyze_stock_profile(basic_info, daily_list, daily_basic, fina_indicator)
    except Exception:
        pass

    return "数据获取失败，请确认股票代码是否正确，或稍后重试。"


@mcp.tool()
async def compare_stocks_tool(ts_codes: str) -> str:
    """多股对比分析 - 同时对比多只股票的关键指标

    Args:
        ts_codes: 股票代码列表(逗号分隔)，如 "000001.SZ,600519.SH,300750.SZ"
    """
    client = _get_client()
    codes = [c.strip() for c in ts_codes.split(",")]

    async def _fetch_one(code: str):
        query = f"{code}最新行情估值对比"
        nl_resp = await client.query_nl(query)
        return code, nl_resp

    results = await asyncio.gather(*[_fetch_one(c) for c in codes], return_exceptions=True)

    lines = ["## 多股对比分析"]
    lines.append("\n### 对比概览")

    for result in results:
        if isinstance(result, Exception):
            continue
        code, nl_resp = result
        if nl_resp.get("code") not in ("200", 200):
            continue

        data = nl_resp.get("data", {})
        entities = data.get("apiData", {}).get("entity", [])
        api_recall = data.get("apiData", {}).get("apiRecall", [])

        stock_name = entities[0].get("code", code) if entities else code
        lines.append(f"\n#### {stock_name}({code})")
        for recall in api_recall[:3]:
            content = recall.get("content", "")
            if content:
                # 提取关键数据行
                for line in content.split("\n")[:8]:
                    if any(k in line for k in ["价格", "涨跌", "换手", "市盈", "市净", "成交"]):
                        lines.append(f"- {line.strip()}")

    lines.append("\n> ⚠️ 以上对比仅供参考，不构成投资建议。")
    return "\n".join(lines)


@mcp.tool()
async def market_overview() -> str:
    """A股市场概览 - 主要指数+北向资金+涨跌停+市场情绪"""
    client = _get_client()

    # 使用NL API获取市场概览
    try:
        nl_resp = await client.query_nl("A股主要指数行情和北向资金流向")

        if nl_resp.get("code") in ("200", 200):
            data = nl_resp.get("data", {})
            api_recall = data.get("apiData", {}).get("apiRecall", [])
            doc_recall = data.get("docData", {}).get("docRecall", [])

            lines = ["## A股市场概览"]
            for recall in api_recall:
                rtype = recall.get("type", "")
                desc = recall.get("desc", "")
                content = recall.get("content", "")
                if content:
                    lines.append(f"\n### {desc or rtype}")
                    lines.append(content)

            if doc_recall:
                lines.append("\n### 市场资讯")
                for dr in doc_recall[:2]:
                    for doc in dr.get("docList", [])[:3]:
                        lines.append(f"- **{doc.get('title', '')}** ({doc.get('source', '')})")

            lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。")
            return "\n".join(lines)
    except Exception:
        pass

    return "市场数据获取失败，请稍后重试。"


@mcp.tool()
async def analyze_financials_tool(ts_code: str) -> str:
    """财报深度分析 - 利润表+资产负债表+现金流+财务健康评级

    Args:
        ts_code: 股票代码，如 000001.SZ
    """
    client = _get_client()

    try:
        nl_resp = await client.query_nl(f"{ts_code}最新财报分析 利润表 资产负债表 现金流")

        if nl_resp.get("code") in ("200", 200):
            data = nl_resp.get("data", {})
            entities = data.get("apiData", {}).get("entity", [])
            api_recall = data.get("apiData", {}).get("apiRecall", [])
            stock_name = entities[0].get("code", ts_code) if entities else ts_code

            lines = [f"## {stock_name} 财报深度分析"]
            for recall in api_recall:
                content = recall.get("content", "")
                desc = recall.get("desc", "")
                if content:
                    lines.append(f"\n### {desc or recall.get('type', '')}")
                    lines.append(content)

            # 财务健康评级
            lines.append("\n### AI财务健康评级")
            all_content = " ".join(r.get("content", "") for r in api_recall)
            score = 50
            if "增长" in all_content:
                score += 15
            if "下降" in all_content or "下滑" in all_content:
                score -= 10
            if "亏损" in all_content:
                score -= 20
            if "盈利" in all_content or "增长" in all_content:
                score += 10

            if score >= 70:
                rating = "🟢 财务优秀"
            elif score >= 55:
                rating = "🟡 财务良好"
            elif score >= 40:
                rating = "🟠 财务一般"
            else:
                rating = "🔴 财务风险"

            lines.append(f"综合评分: {score}/100 | {rating}")
            lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。")
            return "\n".join(lines)
    except Exception:
        pass

    return "财报数据获取失败，请稍后重试。"


@mcp.tool()
async def analyze_fund_tool(ts_code: str) -> str:
    """基金分析 - 净值表现+基金概况

    Args:
        ts_code: 基金代码，如 110011.OF
    """
    client = _get_client()

    try:
        nl_resp = await client.query_nl(f"{ts_code}基金最新净值和概况")

        if nl_resp.get("code") in ("200", 200):
            data = nl_resp.get("data", {})
            entities = data.get("apiData", {}).get("entity", [])
            api_recall = data.get("apiData", {}).get("apiRecall", [])
            fund_name = entities[0].get("code", ts_code) if entities else ts_code

            lines = [f"## {fund_name} 基金分析"]
            for recall in api_recall:
                content = recall.get("content", "")
                desc = recall.get("desc", "")
                if content:
                    lines.append(f"\n### {desc or recall.get('type', '')}")
                    lines.append(content)

            lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。基金投资有风险，过往业绩不代表未来表现。")
            return "\n".join(lines)
    except Exception:
        pass

    return "基金数据获取失败，请稍后重试。"


@mcp.tool()
async def analyze_sector_tool(ts_code: str) -> str:
    """板块分析 - 行业/概念板块行情+资金+成分股

    Args:
        ts_code: 板块代码(同花顺)，如 885001.TI(白酒概念)；也支持板块名称如 "白酒"
    """
    client = _get_client()

    try:
        nl_resp = await client.query_nl(f"{ts_code}板块行情资金流向和成分股")

        if nl_resp.get("code") in ("200", 200):
            data = nl_resp.get("data", {})
            entities = data.get("apiData", {}).get("entity", [])
            api_recall = data.get("apiData", {}).get("apiRecall", [])
            sector_name = entities[0].get("code", ts_code) if entities else ts_code

            lines = [f"## {sector_name} 板块分析"]
            for recall in api_recall:
                content = recall.get("content", "")
                desc = recall.get("desc", "")
                if content:
                    lines.append(f"\n### {desc or recall.get('type', '')}")
                    lines.append(content)

            lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。")
            return "\n".join(lines)
    except Exception:
        pass

    return "板块数据获取失败，请稍后重试。"


@mcp.tool()
async def macro_overview() -> str:
    """宏观经济概览 - GDP/CPI/PPI/Shibor利率"""
    client = _get_client()

    try:
        nl_resp = await client.query_nl("最新GDP CPI PPI Shibor利率宏观数据")

        if nl_resp.get("code") in ("200", 200):
            data = nl_resp.get("data", {})
            api_recall = data.get("apiData", {}).get("apiRecall", [])

            lines = ["## 宏观经济概览"]
            for recall in api_recall:
                content = recall.get("content", "")
                desc = recall.get("desc", "")
                if content:
                    lines.append(f"\n### {desc or recall.get('type', '')}")
                    lines.append(content)

            lines.append("\n> ⚠️ 以上数据来源于官方统计，分析仅供参考。")
            return "\n".join(lines)
    except Exception:
        pass

    return "宏观数据获取失败，请稍后重试。"


@mcp.tool()
async def money_flow_analysis(ts_code: str) -> str:
    """资金流向分析 - 个股资金流+北向资金+融资融券

    Args:
        ts_code: 股票代码，如 000001.SZ；或输入 "market" 查看大盘资金
    """
    client = _get_client()

    try:
        if ts_code.lower() == "market":
            query = "今日北向资金流向和融资融券数据"
        else:
            query = f"{ts_code}资金流向和北向资金融资融券"

        nl_resp = await client.query_nl(query)

        if nl_resp.get("code") in ("200", 200):
            data = nl_resp.get("data", {})
            entities = data.get("apiData", {}).get("entity", [])
            api_recall = data.get("apiData", {}).get("apiRecall", [])
            stock_name = entities[0].get("code", ts_code) if entities else ts_code

            lines = [f"## {stock_name} 资金流向分析"]
            for recall in api_recall:
                content = recall.get("content", "")
                desc = recall.get("desc", "")
                if content:
                    lines.append(f"\n### {desc or recall.get('type', '')}")
                    lines.append(content)

            lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。")
            return "\n".join(lines)
    except Exception:
        pass

    return "资金流向数据获取失败，请稍后重试。"


@mcp.tool()
async def limit_analysis(trade_date: Optional[str] = None) -> str:
    """涨跌停分析 - 涨停/跌停/炸板/龙虎榜

    Args:
        trade_date: 交易日期YYYYMMDD格式，不填则默认最近交易日
    """
    client = _get_client()

    try:
        date_str = trade_date or "今天"
        nl_resp = await client.query_nl(f"{date_str}涨停跌停龙虎榜数据")

        if nl_resp.get("code") in ("200", 200):
            data = nl_resp.get("data", {})
            api_recall = data.get("apiData", {}).get("apiRecall", [])

            lines = [f"## {date_str} 涨跌停分析"]
            for recall in api_recall:
                content = recall.get("content", "")
                desc = recall.get("desc", "")
                if content:
                    lines.append(f"\n### {desc or recall.get('type', '')}")
                    lines.append(content)

            lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。")
            return "\n".join(lines)
    except Exception:
        pass

    return "涨跌停数据获取失败，请稍后重试。"


@mcp.tool()
async def stock_screener(
    industry: Optional[str] = None,
    min_roe: Optional[float] = None,
    max_pe: Optional[float] = None,
    min_market_cap: Optional[float] = None,
    limit: int = 20,
) -> str:
    """智能选股 - 多条件筛选股票

    Args:
        industry: 行业筛选，如 "银行", "白酒", "半导体"
        min_roe: 最低ROE(%)，如 15
        max_pe: 最高PE，如 30
        min_market_cap: 最低市值(亿元)，如 100
        limit: 返回数量，默认20
    """
    client = _get_client()

    # 构造自然语言查询
    conditions = []
    if industry:
        conditions.append(f"{industry}行业")
    if min_roe:
        conditions.append(f"ROE大于{min_roe}%")
    if max_pe:
        conditions.append(f"市盈率小于{max_pe}")
    if min_market_cap:
        conditions.append(f"市值大于{min_market_cap}亿")

    query = "选股: " + " ".join(conditions) if conditions else "今日A股低估值高ROE股票推荐"

    try:
        nl_resp = await client.query_nl(query)

        if nl_resp.get("code") in ("200", 200):
            data = nl_resp.get("data", {})
            api_recall = data.get("apiData", {}).get("apiRecall", [])

            lines = [f"## 智能选股结果"]
            lines.append(f"\n筛选条件: {' | '.join(conditions) if conditions else '低估值高ROE'}")

            for recall in api_recall:
                content = recall.get("content", "")
                desc = recall.get("desc", "")
                if content:
                    lines.append(f"\n### {desc or recall.get('type', '')}")
                    lines.append(content)

            lines.append("\n> ⚠️ 以上筛选仅供参考，不构成投资建议。投资有风险，入市需谨慎。")
            return "\n".join(lines)
    except Exception:
        pass

    return "选股数据获取失败，请稍后重试。"


@mcp.tool()
async def query_neodata(query: str) -> str:
    """自然语言金融数据查询 - 用自然语言获取任意金融数据

    Args:
        query: 自然语言查询，如 "贵州茅台最新股价", "沪深300成分股", "最新GDP数据"
    """
    client = _get_client()

    try:
        result = await client.query_nl(query)
        # 格式化输出
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2)
        return str(result)
    except Exception as e:
        return f"查询失败: {str(e)}"


@mcp.tool()
async def query_financial_api(
    api_name: str,
    params: Optional[str] = None,
    fields: Optional[str] = None,
) -> str:
    """结构化金融数据查询 - 直接调用209个NeoData API接口

    Args:
        api_name: 接口名称，如 daily(日线), income(利润表), stock_basic(股票列表)
        params: JSON格式参数，如 '{"ts_code": "000001.SZ", "start_date": "20250101"}'
        fields: 返回字段筛选，逗号分隔，如 "ts_code,close,vol"
    """
    client = _get_client()

    # 解析params
    parsed_params = None
    if params:
        try:
            parsed_params = json.loads(params)
        except json.JSONDecodeError:
            return f"参数格式错误，请使用JSON格式，如: '{{\"ts_code\": \"000001.SZ\"}}'"

    try:
        resp = await client.query_structured(api_name, parsed_params, fields)

        if resp.get("code") != 0:
            return f"API调用失败: {resp.get('msg', '未知错误')} (code: {resp.get('code')})"

        parsed = _parse_api_response(resp)

        # 格式化表格输出
        lines = [f"## {api_name} 查询结果 ({parsed['count']}条)"]
        if parsed["data"]:
            headers = parsed["fields"]
            lines.append("| " + " | ".join(headers[:8]) + " |")
            lines.append("| " + " | ".join(["---"] * min(len(headers), 8)) + " |")
            for row in parsed["data"][:20]:  # 最多显示20行
                vals = [str(row.get(h, ""))[:20] for h in headers[:8]]
                lines.append("| " + " | ".join(vals) + " |")

            if parsed["count"] > 20:
                lines.append(f"\n... 共{parsed['count']}条，仅显示前20条")

        return "\n".join(lines)
    except Exception as e:
        return f"查询失败: {str(e)}"


@mcp.tool()
async def forex_and_commodities(
    fx_code: Optional[str] = None,
) -> str:
    """外汇与大宗商品行情

    Args:
        fx_code: 外汇代码(可选)，如 USDCNY, EURCNY；不填则返回主要汇率
    """
    client = _get_client()

    try:
        if fx_code:
            query = f"{fx_code}汇率最新行情"
        else:
            query = "人民币汇率和黄金现货最新行情"

        nl_resp = await client.query_nl(query)

        if nl_resp.get("code") in ("200", 200):
            data = nl_resp.get("data", {})
            api_recall = data.get("apiData", {}).get("apiRecall", [])

            lines = ["## 外汇与大宗商品"]
            for recall in api_recall:
                content = recall.get("content", "")
                desc = recall.get("desc", "")
                if content:
                    lines.append(f"\n### {desc or recall.get('type', '')}")
                    lines.append(content)

            lines.append("\n> ⚠️ 以上数据仅供参考，不构成投资建议。")
            return "\n".join(lines)
    except Exception:
        pass

    return "外汇数据获取失败，请稍后重试。"


# ========== 入口 ==========

def main():
    """启动MCP Server"""
    parser = argparse.ArgumentParser(description="金融智能分析MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="传输协议 (默认: stdio, http=Streamable HTTP远程模式)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9001,
        help="HTTP/SSE模式端口 (默认: 9001)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="HTTP/SSE模式主机 (默认: 0.0.0.0)",
    )
    parser.add_argument(
        "--path",
        default="/finmcp",
        help="HTTP模式路径 (默认: /finmcp)",
    )

    args = parser.parse_args()

    if args.transport == "http":
        # Streamable HTTP远程模式 - 用户只需填URL即可连接
        mcp.run(transport="http", host=args.host, port=args.port, path=args.path)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
