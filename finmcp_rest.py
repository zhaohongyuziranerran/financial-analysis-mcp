"""FinMCP 极简 REST API - 专为 Coze 云侧插件设计

单文件Flask服务，直接暴露REST接口给Coze调用。
每个接口直接调用NeoData API，返回纯文本结果。

部署: python finmcp_rest.py
端口: 9003
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))
from fin_analysis_mcp.neodata_client import NeoDataClient

app = Flask(__name__)
CORS(app)

# 全局NeoData客户端
_client = None

def get_client():
    global _client
    if _client is None:
        _client = NeoDataClient()
    return _client


# ========== 工具函数 ==========

def _run_async(coro):
    """运行异步代码"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def _format_stock_result(nl_resp: dict, stock_code: str) -> str:
    """格式化股票分析结果"""
    if nl_resp.get("code") not in ("200", 200):
        return f"数据获取失败: {nl_resp.get('msg', '未知错误')}"

    data = nl_resp.get("data", {})
    api_data = data.get("apiData", {})
    entities = api_data.get("entity", [])
    api_recall = api_data.get("apiRecall", [])

    stock_name = entities[0].get("code", stock_code) if entities else stock_code

    lines = [f"## {stock_name}({stock_code}) 综合分析"]

    for recall in api_recall:
        rtype = recall.get("type", "")
        desc = recall.get("desc", "")
        content = recall.get("content", "")
        if content:
            title = desc or rtype
            lines.append(f"\n### {title}")
            lines.append(content)

    lines.append("\n> 以上分析仅供参考，不构成投资建议。")
    return "\n".join(lines)


# ========== REST API Endpoints ==========

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "FinMCP REST", "version": "1.0.0"})


@app.route("/analyze_stock", methods=["POST"])
def analyze_stock():
    """个股综合分析"""
    data = request.get_json() or {}
    stock_code = data.get("stock_code", data.get("ts_code", ""))
    if not stock_code:
        return jsonify({"error": "缺少stock_code参数"}), 400

    client = get_client()
    nl_resp = _run_async(client.query_nl(f"{stock_code}最新行情和基本面分析"))
    result = _format_stock_result(nl_resp, stock_code)
    return jsonify({"result": result})


@app.route("/compare_stocks", methods=["POST"])
def compare_stocks():
    """多股对比"""
    data = request.get_json() or {}
    codes = data.get("stock_codes", data.get("ts_codes", ""))
    if not codes:
        return jsonify({"error": "缺少stock_codes参数"}), 400

    client = get_client()
    code_list = [c.strip() for c in codes.split(",")]

    lines = ["## 多股对比分析"]
    for code in code_list:
        nl_resp = _run_async(client.query_nl(f"{code}最新行情估值"))
        if nl_resp.get("code") in ("200", 200):
            api_data = nl_resp.get("data", {}).get("apiData", {})
            entities = api_data.get("entity", [])
            api_recall = api_data.get("apiRecall", [])
            name = entities[0].get("code", code) if entities else code
            lines.append(f"\n### {name}({code})")
            for recall in api_recall[:2]:
                content = recall.get("content", "")
                if content:
                    for line in content.split("\n")[:6]:
                        if any(k in line for k in ["价格", "涨跌", "换手", "市盈", "市净"]):
                            lines.append(f"- {line.strip()}")

    lines.append("\n> 以上对比仅供参考，不构成投资建议。")
    return jsonify({"result": "\n".join(lines)})


@app.route("/market_overview", methods=["POST"])
def market_overview():
    """A股市场概览"""
    client = get_client()
    nl_resp = _run_async(client.query_nl("A股主要指数行情和北向资金流向"))

    if nl_resp.get("code") in ("200", 200):
        api_recall = nl_resp.get("data", {}).get("apiData", {}).get("apiRecall", [])
        lines = ["## A股市场概览"]
        for recall in api_recall:
            content = recall.get("content", "")
            desc = recall.get("desc", "")
            if content:
                lines.append(f"\n### {desc or recall.get('type', '')}")
                lines.append(content)
        return jsonify({"result": "\n".join(lines)})

    return jsonify({"result": "市场数据获取失败，请稍后重试。"})


@app.route("/analyze_financials", methods=["POST"])
def analyze_financials():
    """财报深度分析"""
    data = request.get_json() or {}
    stock_code = data.get("stock_code", data.get("ts_code", ""))
    if not stock_code:
        return jsonify({"error": "缺少stock_code参数"}), 400

    client = get_client()
    nl_resp = _run_async(client.query_nl(f"{stock_code}最新财报分析 利润表 资产负债表 现金流"))
    result = _format_stock_result(nl_resp, stock_code)
    return jsonify({"result": result})


@app.route("/analyze_fund", methods=["POST"])
def analyze_fund():
    """基金分析"""
    data = request.get_json() or {}
    fund_code = data.get("fund_code", data.get("ts_code", ""))
    if not fund_code:
        return jsonify({"error": "缺少fund_code参数"}), 400

    client = get_client()
    nl_resp = _run_async(client.query_nl(f"{fund_code}基金最新净值和概况"))
    result = _format_stock_result(nl_resp, fund_code)
    return jsonify({"result": result})


@app.route("/money_flow", methods=["POST"])
def money_flow():
    """资金流向分析"""
    data = request.get_json() or {}
    stock_code = data.get("stock_code", data.get("ts_code", "market"))

    client = get_client()
    if stock_code.lower() == "market":
        query = "今日北向资金流向和融资融券数据"
    else:
        query = f"{stock_code}资金流向和北向资金融资融券"

    nl_resp = _run_async(client.query_nl(query))
    result = _format_stock_result(nl_resp, stock_code)
    return jsonify({"result": result})


@app.route("/limit_analysis", methods=["POST"])
def limit_analysis():
    """涨跌停分析"""
    client = get_client()
    nl_resp = _run_async(client.query_nl("今天涨停跌停龙虎榜数据"))

    if nl_resp.get("code") in ("200", 200):
        api_recall = nl_resp.get("data", {}).get("apiData", {}).get("apiRecall", [])
        lines = ["## 涨跌停分析"]
        for recall in api_recall:
            content = recall.get("content", "")
            desc = recall.get("desc", "")
            if content:
                lines.append(f"\n### {desc or recall.get('type', '')}")
                lines.append(content)
        return jsonify({"result": "\n".join(lines)})

    return jsonify({"result": "涨跌停数据获取失败，请稍后重试。"})


@app.route("/macro_overview", methods=["POST"])
def macro_overview():
    """宏观经济概览"""
    client = get_client()
    nl_resp = _run_async(client.query_nl("最新GDP CPI PPI Shibor利率宏观数据"))

    if nl_resp.get("code") in ("200", 200):
        api_recall = nl_resp.get("data", {}).get("apiData", {}).get("apiRecall", [])
        lines = ["## 宏观经济概览"]
        for recall in api_recall:
            content = recall.get("content", "")
            desc = recall.get("desc", "")
            if content:
                lines.append(f"\n### {desc or recall.get('type', '')}")
                lines.append(content)
        return jsonify({"result": "\n".join(lines)})

    return jsonify({"result": "宏观数据获取失败，请稍后重试。"})


@app.route("/query", methods=["POST"])
def query():
    """自然语言金融数据查询"""
    data = request.get_json() or {}
    query_text = data.get("query", "")
    if not query_text:
        return jsonify({"error": "缺少query参数"}), 400

    client = get_client()
    nl_resp = _run_async(client.query_nl(query_text))

    if nl_resp.get("code") in ("200", 200):
        api_recall = nl_resp.get("data", {}).get("apiData", {}).get("apiRecall", [])
        lines = [f"## 查询结果: {query_text}"]
        for recall in api_recall:
            content = recall.get("content", "")
            desc = recall.get("desc", "")
            if content:
                lines.append(f"\n### {desc or recall.get('type', '')}")
                lines.append(content)
        return jsonify({"result": "\n".join(lines)})

    return jsonify({"result": f"查询失败: {nl_resp.get('msg', '未知错误')}"})


# ========== 启动 ==========

if __name__ == "__main__":
    port = int(os.getenv("PORT", 9003))
    print(f"FinMCP REST API starting on port {port}...")
    print("Endpoints:")
    print("  POST /analyze_stock     - 个股分析")
    print("  POST /compare_stocks    - 多股对比")
    print("  POST /market_overview   - 市场概览")
    print("  POST /analyze_financials- 财报分析")
    print("  POST /analyze_fund      - 基金分析")
    print("  POST /money_flow        - 资金流向")
    print("  POST /limit_analysis    - 涨跌停")
    print("  POST /macro_overview    - 宏观经济")
    print("  POST /query             - 自然语言查询")
    app.run(host="0.0.0.0", port=port, threaded=True)
