"""AI智能分析层 - 数据解读与投资分析生成

核心原则：卖分析不卖数据
- 不直接返回原始数据，而是提供AI解读
- 分析趋势、给出评价、提示风险
- 所有建议附带免责声明
"""

from typing import Any, Optional


def _safe_get(data: dict, key: str, default: str = "N/A") -> str:
    """安全获取字典值"""
    val = data.get(key, default)
    if val is None:
        return default
    return str(val)


def _format_percent(val: Any) -> str:
    """格式化百分比"""
    if val is None or val == "N/A":
        return "N/A"
    try:
        return f"{float(val):.2f}%"
    except (ValueError, TypeError):
        return str(val)


def _format_amount(val: Any, unit: str = "亿") -> str:
    """格式化金额(元→亿元)"""
    if val is None or val == "N/A":
        return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1e8:
            return f"{v / 1e8:.2f}{unit}"
        elif abs(v) >= 1e4:
            return f"{v / 1e4:.2f}万"
        return f"{v:.2f}元"
    except (ValueError, TypeError):
        return str(val)


def _calc_change(current: float, previous: float) -> str:
    """计算涨跌幅"""
    if previous == 0:
        return "N/A"
    pct = (current - previous) / abs(previous) * 100
    arrow = "↑" if pct > 0 else "↓" if pct < 0 else "→"
    return f"{arrow}{abs(pct):.2f}%"


def analyze_stock_profile(
    basic_info: dict,
    daily_data: list[dict],
    daily_basic: Optional[dict] = None,
    fina_indicator: Optional[dict] = None,
) -> str:
    """个股综合分析报告

    Args:
        basic_info: 股票基本信息
        daily_data: 近期日线数据(最新在前)
        daily_basic: 每日指标(PE/PB等)
        fina_indicator: 财务指标(ROE等)
    """
    lines = []

    # === 基本信息 ===
    name = _safe_get(basic_info, "name")
    ts_code = _safe_get(basic_info, "ts_code")
    industry = _safe_get(basic_info, "industry")
    market = _safe_get(basic_info, "market")

    lines.append(f"## {name}({ts_code}) 综合分析")
    lines.append(f"- 行业: {industry} | 市场: {market}")

    # === 行情分析 ===
    if daily_data and len(daily_data) > 0:
        latest = daily_data[0]
        prev = daily_data[1] if len(daily_data) > 1 else None

        close = float(_safe_get(latest, "close", "0"))
        open_p = float(_safe_get(latest, "open", "0"))
        high = float(_safe_get(latest, "high", "0"))
        low = float(_safe_get(latest, "low", "0"))
        vol = float(_safe_get(latest, "vol", "0"))
        amount = float(_safe_get(latest, "amount", "0"))

        lines.append(f"\n### 行情概况 ({_safe_get(latest, 'trade_date')})")
        lines.append(f"- 收盘: {close:.2f} | 开盘: {open_p:.2f}")
        lines.append(f"- 最高: {high:.2f} | 最低: {low:.2f}")
        lines.append(f"- 成交量: {_format_amount(vol, '手')} | 成交额: {_format_amount(amount * 1000, '元')}")

        # 涨跌分析
        if prev:
            prev_close = float(_safe_get(prev, "close", "0"))
            chg = close - prev_close
            pct_chg = (chg / prev_close * 100) if prev_close != 0 else 0
            arrow = "🔴" if pct_chg > 0 else "🟢" if pct_chg < 0 else "⚪"
            lines.append(f"- 涨跌: {arrow} {chg:+.2f} ({pct_chg:+.2f}%)")

        # 趋势判断(近5日)
        if len(daily_data) >= 5:
            closes_5 = [float(_safe_get(d, "close", "0")) for d in daily_data[:5]]
            ma5 = sum(closes_5) / len(closes_5)
            trend = "上升" if close > ma5 else "下降" if close < ma5 else "震荡"
            lines.append(f"- 5日均价: {ma5:.2f} | 短期趋势: {trend}")

        # 振幅分析
        if high > 0 and low > 0:
            amplitude = (high - low) / low * 100
            lines.append(f"- 日内振幅: {amplitude:.2f}%")

    # === 估值分析 ===
    if daily_basic:
        lines.append("\n### 估值指标")
        pe = _safe_get(daily_basic, "pe")
        pb = _safe_get(daily_basic, "pb")
        ps = _safe_get(daily_basic, "ps")
        dv_ratio = _safe_get(daily_basic, "dv_ratio")
        turnover_rate = _safe_get(daily_basic, "turnover_rate")
        total_mv = _safe_get(daily_basic, "total_mv")
        circ_mv = _safe_get(daily_basic, "circ_mv")

        lines.append(f"- PE(市盈率): {pe} | PB(市净率): {pb}")
        lines.append(f"- PS(市销率): {ps} | 股息率: {dv_ratio}%")
        lines.append(f"- 换手率: {turnover_rate}%")
        lines.append(f"- 总市值: {_format_amount(float(total_mv) * 10000 if total_mv != 'N/A' else 0, '亿')}")

        # 估值评价
        try:
            pe_val = float(pe)
            if pe_val < 0:
                lines.append("- ⚠️ PE为负，公司亏损中")
            elif pe_val < 15:
                lines.append("- ✅ PE较低，可能被低估")
            elif pe_val < 30:
                lines.append("- 📊 PE中等，估值合理")
            elif pe_val < 60:
                lines.append("- ⚠️ PE偏高，注意估值风险")
            else:
                lines.append("- 🔴 PE过高，估值泡沫风险")
        except (ValueError, TypeError):
            pass

    # === 财务健康度 ===
    if fina_indicator:
        lines.append("\n### 财务健康度")
        roe = _safe_get(fina_indicator, "roe")
        grossprofit_margin = _safe_get(fina_indicator, "grossprofit_margin")
        netprofit_margin = _safe_get(fina_indicator, "netprofit_margin")
        debt_to_assets = _safe_get(fina_indicator, "debt_to_assets")
        current_ratio = _safe_get(fina_indicator, "current_ratio")

        lines.append(f"- ROE(净资产收益率): {roe}%")
        lines.append(f"- 毛利率: {grossprofit_margin}% | 净利率: {netprofit_margin}%")
        lines.append(f"- 资产负债率: {debt_to_assets}% | 流动比率: {current_ratio}")

        # 财务评价
        try:
            roe_val = float(roe)
            if roe_val > 15:
                lines.append("- ✅ ROE优秀(>15%)，盈利能力强")
            elif roe_val > 8:
                lines.append("- 📊 ROE中等，盈利能力一般")
            elif roe_val > 0:
                lines.append("- ⚠️ ROE偏低，盈利能力较弱")
            else:
                lines.append("- 🔴 ROE为负，公司亏损")
        except (ValueError, TypeError):
            pass

    # === 综合评价 ===
    lines.append("\n### 综合评价")
    lines.append(_generate_stock_rating(daily_data, daily_basic, fina_indicator))

    lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。")

    return "\n".join(lines)


def _generate_stock_rating(
    daily_data: list[dict],
    daily_basic: Optional[dict],
    fina_indicator: Optional[dict],
) -> str:
    """生成股票评级"""
    score = 50  # 基准分50

    # 趋势分(30分)
    if daily_data and len(daily_data) >= 5:
        closes = [float(_safe_get(d, "close", "0")) for d in daily_data[:5]]
        if closes[0] > sum(closes) / len(closes):
            score += 15
        if all(closes[i] >= closes[i + 1] for i in range(len(closes) - 1)):
            score += 15
        elif all(closes[i] <= closes[i + 1] for i in range(len(closes) - 1)):
            score -= 15

    # 估值分(20分)
    if daily_basic:
        try:
            pe = float(_safe_get(daily_basic, "pe", "0"))
            if 0 < pe < 20:
                score += 15
            elif 20 <= pe < 40:
                score += 5
            elif pe >= 60:
                score -= 10
        except (ValueError, TypeError):
            pass

    # 财务分(20分)
    if fina_indicator:
        try:
            roe = float(_safe_get(fina_indicator, "roe", "0"))
            if roe > 15:
                score += 15
            elif roe > 8:
                score += 8
            elif roe < 0:
                score -= 10
        except (ValueError, TypeError):
            pass

    # 评级映射
    if score >= 80:
        rating = "🟢 强烈关注 - 多项指标优秀"
    elif score >= 65:
        rating = "🟡 值得关注 - 部分指标亮眼"
    elif score >= 50:
        rating = "⚪ 中性观望 - 指标表现一般"
    elif score >= 35:
        rating = "🟠 谨慎观望 - 存在风险因素"
    else:
        rating = "🔴 风险提示 - 多项指标不佳"

    return f"综合评分: {score}/100 | {rating}"


def analyze_market_overview(
    index_data: dict[str, list[dict]],
    moneyflow_hsgt: Optional[dict] = None,
    limit_data: Optional[dict] = None,
) -> str:
    """市场概览分析

    Args:
        index_data: 各指数日线数据 {"000001.SH": [...], "399001.SZ": [...]}
        moneyflow_hsgt: 北向资金数据
        limit_data: 涨跌停数据
    """
    lines = ["## A股市场概览"]

    # === 指数行情 ===
    lines.append("\n### 主要指数")
    index_names = {
        "000001.SH": "上证指数",
        "399001.SZ": "深证成指",
        "399006.SZ": "创业板指",
        "000016.SH": "上证50",
        "000300.SH": "沪深300",
        "000905.SH": "中证500",
        "000852.SH": "中证1000",
    }

    for ts_code, data_list in index_data.items():
        if not data_list:
            continue
        latest = data_list[0]
        name = index_names.get(ts_code, ts_code)
        close = float(_safe_get(latest, "close", "0"))
        pct_chg = _safe_get(latest, "pct_chg")
        vol = _safe_get(latest, "vol")
        arrow = "🔴" if float(pct_chg) > 0 else "🟢" if float(pct_chg) < 0 else "⚪"
        lines.append(
            f"- {name}: {close:.2f} {arrow}{pct_chg}% | 成交量: {_format_amount(float(vol), '手')}"
        )

    # === 北向资金 ===
    if moneyflow_hsgt:
        lines.append("\n### 北向资金")
        items = moneyflow_hsgt.get("data", {}).get("items", [])
        if items:
            fields = moneyflow_hsgt.get("data", {}).get("fields", [])
            latest_item = items[0]
            item_dict = dict(zip(fields, latest_item))
            north_net = _safe_get(item_dict, "north_net")
            north_money = _safe_get(item_dict, "north_money")
            south_net = _safe_get(item_dict, "south_net")
            lines.append(f"- 北向净买入: {_format_amount(float(north_net) * 1e4 if north_net != 'N/A' else 0, '元')}")
            lines.append(f"- 南向净买入: {_format_amount(float(south_net) * 1e4 if south_net != 'N/A' else 0, '元')}")

    # === 涨跌停 ===
    if limit_data:
        items = limit_data.get("data", {}).get("items", [])
        up_count = sum(1 for item in items if len(item) > 2 and str(item[2]) == "Z")
        down_count = sum(1 for item in items if len(item) > 2 and str(item[2]) == "D")
        lines.append(f"\n### 涨跌停统计")
        lines.append(f"- 涨停: {up_count}只 | 跌停: {down_count}只")

    # === 市场情绪判断 ===
    lines.append("\n### 市场情绪")
    total_pct = 0
    count = 0
    for ts_code, data_list in index_data.items():
        if data_list:
            try:
                total_pct += float(_safe_get(data_list[0], "pct_chg", "0"))
                count += 1
            except (ValueError, TypeError):
                pass

    if count > 0:
        avg_pct = total_pct / count
        if avg_pct > 1:
            lines.append("- 🔥 市场情绪火热，普涨行情")
        elif avg_pct > 0.3:
            lines.append("- 🟢 市场偏暖，多头占优")
        elif avg_pct > -0.3:
            lines.append("- ⚪ 市场震荡，多空均衡")
        elif avg_pct > -1:
            lines.append("- 🟠 市场偏弱，空头占优")
        else:
            lines.append("- 🔴 市场低迷，普跌行情")

    lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。")
    return "\n".join(lines)


def analyze_financials(
    stock_name: str,
    income_data: Optional[dict] = None,
    balance_data: Optional[dict] = None,
    cashflow_data: Optional[dict] = None,
    fina_indicator: Optional[dict] = None,
) -> str:
    """财报深度分析

    Args:
        stock_name: 股票名称
        income_data: 利润表数据
        balance_data: 资产负债表数据
        cashflow_data: 现金流量表数据
        fina_indicator: 财务指标数据
    """
    lines = [f"## {stock_name} 财报深度分析"]

    # === 盈利能力 ===
    if fina_indicator:
        lines.append("\n### 盈利能力")
        lines.append(f"- ROE(净资产收益率): {_safe_get(fina_indicator, 'roe')}%")
        lines.append(f"- ROA(总资产收益率): {_safe_get(fina_indicator, 'roa')}%")
        lines.append(f"- 毛利率: {_safe_get(fina_indicator, 'grossprofit_margin')}%")
        lines.append(f"- 净利率: {_safe_get(fina_indicator, 'netprofit_margin')}%")
        lines.append(f"- 营业利润率: {_safe_get(fina_indicator, 'op_yoy')}%")

    # === 利润表 ===
    if income_data:
        lines.append("\n### 利润表摘要")
        lines.append(f"- 营业收入: {_format_amount(float(_safe_get(income_data, 'total_revenue', '0')))}")
        lines.append(f"- 营业成本: {_format_amount(float(_safe_get(income_data, 'total_cogs', '0')))}")
        lines.append(f"- 净利润: {_format_amount(float(_safe_get(income_data, 'n_income', '0')))}")
        lines.append(f"- 扣非净利润: {_format_amount(float(_safe_get(income_data, 'n_income_attr_p', '0')))}")

        # 增长分析
        yoy_profit = _safe_get(income_data, "n_income_attr_p")
        rev_yoy = _safe_get(income_data, "total_revenue")
        if rev_yoy != "N/A" and yoy_profit != "N/A":
            lines.append(f"- 营收同比: {rev_yoy}% | 净利润同比: {yoy_profit}%")

    # === 资产负债表 ===
    if balance_data:
        lines.append("\n### 资产负债表摘要")
        total_assets = float(_safe_get(balance_data, "total_assets", "0"))
        total_liab = float(_safe_get(balance_data, "total_liab", "0"))
        total_holders_eqy = float(_safe_get(balance_data, "total_holders_eqy_no_min", "0"))

        lines.append(f"- 总资产: {_format_amount(total_assets)}")
        lines.append(f"- 总负债: {_format_amount(total_liab)}")
        lines.append(f"- 净资产: {_format_amount(total_holders_eqy)}")

        if total_assets > 0:
            debt_ratio = total_liab / total_assets * 100
            lines.append(f"- 资产负债率: {debt_ratio:.2f}%")
            if debt_ratio > 70:
                lines.append("  ⚠️ 负债率偏高，偿债压力大")
            elif debt_ratio > 50:
                lines.append("  📊 负债率中等，尚属合理")
            else:
                lines.append("  ✅ 负债率较低，财务稳健")

    # === 现金流 ===
    if cashflow_data:
        lines.append("\n### 现金流分析")
        ocf = float(_safe_get(cashflow_data, "n_cashflow_act", "0"))
        icf = float(_safe_get(cashflow_data, "n_cashflow_inv_act", "0"))
        fcf = float(_safe_get(cashflow_data, "n_cashflow_fnc_act", "0"))

        lines.append(f"- 经营活动现金流: {_format_amount(ocf)}")
        lines.append(f"- 投资活动现金流: {_format_amount(icf)}")
        lines.append(f"- 筹资活动现金流: {_format_amount(fcf)}")

        if ocf > 0:
            lines.append("  ✅ 经营现金流为正，造血能力正常")
        else:
            lines.append("  ⚠️ 经营现金流为负，需关注经营状况")

    # === 综合评价 ===
    lines.append("\n### 财务综合评价")
    lines.append(_generate_financial_rating(fina_indicator, income_data, balance_data, cashflow_data))

    lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。")
    return "\n".join(lines)


def _generate_financial_rating(
    fina_indicator: Optional[dict],
    income_data: Optional[dict],
    balance_data: Optional[dict],
    cashflow_data: Optional[dict],
) -> str:
    """财务健康评级"""
    score = 50

    if fina_indicator:
        try:
            roe = float(_safe_get(fina_indicator, "roe", "0"))
            if roe > 20:
                score += 20
            elif roe > 12:
                score += 10
            elif roe > 0:
                score += 0
            else:
                score -= 15
        except (ValueError, TypeError):
            pass

        try:
            gross = float(_safe_get(fina_indicator, "grossprofit_margin", "0"))
            if gross > 50:
                score += 10
            elif gross > 30:
                score += 5
            elif gross < 10:
                score -= 10
        except (ValueError, TypeError):
            pass

    if cashflow_data:
        ocf = float(_safe_get(cashflow_data, "n_cashflow_act", "0"))
        if ocf > 0:
            score += 10
        else:
            score -= 10

    if balance_data:
        total_assets = float(_safe_get(balance_data, "total_assets", "0"))
        total_liab = float(_safe_get(balance_data, "total_liab", "0"))
        if total_assets > 0:
            debt_ratio = total_liab / total_assets * 100
            if debt_ratio < 40:
                score += 10
            elif debt_ratio > 70:
                score -= 10

    if score >= 80:
        return f"综合评分: {score}/100 | 🟢 财务优秀 - 盈利能力强，现金流健康"
    elif score >= 60:
        return f"综合评分: {score}/100 | 🟡 财务良好 - 整体稳健，个别指标需关注"
    elif score >= 40:
        return f"综合评分: {score}/100 | 🟠 财务一般 - 存在隐患，需持续观察"
    else:
        return f"综合评分: {score}/100 | 🔴 财务风险 - 多项指标不佳，投资需谨慎"


def analyze_fund(
    fund_name: str,
    fund_nav: Optional[dict] = None,
    fund_basic: Optional[dict] = None,
) -> str:
    """基金分析报告"""
    lines = [f"## {fund_name} 基金分析"]

    if fund_basic:
        lines.append("\n### 基金概况")
        lines.append(f"- 基金类型: {_safe_get(fund_basic, 'fund_type')}")
        lines.append(f"- 成立日期: {_safe_get(fund_basic, 'found_date')}")
        lines.append(f"- 管理人: {_safe_get(fund_basic, 'management')}")
        lines.append(f"- 托管人: {_safe_get(fund_basic, 'custodian')}")
        lines.append(f"- 基金经理: {_safe_get(fund_basic, 'manager')}")

    if fund_nav:
        lines.append("\n### 净值表现")
        lines.append(f"- 单位净值: {_safe_get(fund_nav, 'end_date')} | {_safe_get(fund_nav, 'unit_nav')}")
        lines.append(f"- 累计净值: {_safe_get(fund_nav, 'accum_nav')}")
        lines.append(f"- 累计复权净值: {_safe_get(fund_nav, 'accum_nav_unit')}")
        lines.append(f"- 净值日期: {_safe_get(fund_nav, 'end_date')}")

    lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。基金投资有风险，过往业绩不代表未来表现。")
    return "\n".join(lines)


def analyze_sector(
    sector_name: str,
    ths_daily: Optional[list[dict]] = None,
    members: Optional[list[dict]] = None,
    moneyflow: Optional[dict] = None,
) -> str:
    """板块分析报告"""
    lines = [f"## {sector_name} 板块分析"]

    if ths_daily and len(ths_daily) > 0:
        latest = ths_daily[0]
        lines.append("\n### 板块行情")
        close = float(_safe_get(latest, "close", "0"))
        pct_chg = _safe_get(latest, "pct_chg")
        vol = _safe_get(latest, "vol")
        arrow = "🔴" if float(pct_chg) > 0 else "🟢" if float(pct_chg) < 0 else "⚪"
        lines.append(f"- 板块指数: {close:.2f} {arrow}{pct_chg}%")
        lines.append(f"- 成交量: {_format_amount(float(vol), '手')}")

        # 趋势判断
        if len(ths_daily) >= 5:
            closes = [float(_safe_get(d, "close", "0")) for d in ths_daily[:5]]
            ma5 = sum(closes) / len(closes)
            trend = "上升" if close > ma5 else "下降" if close < ma5 else "震荡"
            lines.append(f"- 5日均价: {ma5:.2f} | 短期趋势: {trend}")

    if moneyflow:
        lines.append("\n### 资金动向")
        items = moneyflow.get("data", {}).get("items", [])
        if items:
            fields = moneyflow.get("data", {}).get("fields", [])
            if items[0]:
                item_dict = dict(zip(fields, items[0]))
                lines.append(f"- 净买入: {_safe_get(item_dict, 'net_buy_amount')}")
                lines.append(f"- 净卖出: {_safe_get(item_dict, 'net_sell_amount')}")

    if members:
        lines.append("\n### 成分股TOP10")
        for i, m in enumerate(members[:10], 1):
            lines.append(f"  {i}. {_safe_get(m, 'name')}({_safe_get(m, 'ts_code')})")

    lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。")
    return "\n".join(lines)


def analyze_macro(
    gdp_data: Optional[list[dict]] = None,
    cpi_data: Optional[list[dict]] = None,
    ppi_data: Optional[list[dict]] = None,
    shibor_data: Optional[list[dict]] = None,
) -> str:
    """宏观经济分析"""
    lines = ["## 宏观经济概览"]

    if gdp_data and len(gdp_data) > 0:
        latest = gdp_data[0]
        lines.append("\n### GDP")
        lines.append(f"- 季度: {_safe_get(latest, 'quarter')}")
        lines.append(f"- GDP: {_safe_get(latest, 'gdp')}亿元")
        lines.append(f"- 同比增长: {_safe_get(latest, 'gdp_yoy')}%")

    if cpi_data and len(cpi_data) > 0:
        latest = cpi_data[0]
        lines.append("\n### CPI(居民消费价格指数)")
        lines.append(f"- 月份: {_safe_get(latest, 'month')}")
        lines.append(f"- CPI同比: {_safe_get(latest, 'nt_yoy')}%")
        lines.append(f"- CPI环比: {_safe_get(latest, 'nt_mom')}%")

    if ppi_data and len(ppi_data) > 0:
        latest = ppi_data[0]
        lines.append("\n### PPI(工业生产者出厂价格指数)")
        lines.append(f"- 月份: {_safe_get(latest, 'month')}")
        lines.append(f"- PPI同比: {_safe_get(latest, 'ppi_yoy')}%")
        lines.append(f"- PPI环比: {_safe_get(latest, 'ppi_mom')}%")

    if shibor_data and len(shibor_data) > 0:
        latest = shibor_data[0]
        lines.append("\n### Shibor利率")
        lines.append(f"- 日期: {_safe_get(latest, 'date')}")
        lines.append(f"- 隔夜: {_safe_get(latest, 'on')}%")
        lines.append(f"- 1周: {_safe_get(latest, '1w')}%")
        lines.append(f"- 1月: {_safe_get(latest, '1m')}%")
        lines.append(f"- 3月: {_safe_get(latest, '3m')}%")
        lines.append(f"- 1年: {_safe_get(latest, '1y')}%")

    lines.append("\n> ⚠️ 以上数据来源于官方统计，分析仅供参考。")
    return "\n".join(lines)


def analyze_money_flow(
    stock_name: str,
    moneyflow: Optional[dict] = None,
    hsgt: Optional[dict] = None,
    margin: Optional[dict] = None,
) -> str:
    """资金流向分析"""
    lines = [f"## {stock_name} 资金流向分析"]

    if moneyflow:
        items = moneyflow.get("data", {}).get("items", [])
        fields = moneyflow.get("data", {}).get("fields", [])
        if items and fields:
            lines.append("\n### 个股资金流向")
            latest = dict(zip(fields, items[0]))
            lines.append(f"- 日期: {_safe_get(latest, 'trade_date')}")
            lines.append(f"- 主力净流入: {_format_amount(float(_safe_get(latest, 'buy_elg_sm_orade', '0')))}")
            lines.append(f"- 大单净买入: {_safe_get(latest, 'buy_elg_vol')}")
            lines.append(f"- 中单净买入: {_safe_get(latest, 'buy_mdm_vol')}")
            lines.append(f"- 小单净买入: {_safe_get(latest, 'buy_sml_vol')}")

    if hsgt:
        items = hsgt.get("data", {}).get("items", [])
        fields = hsgt.get("data", {}).get("fields", [])
        if items and fields:
            latest = dict(zip(fields, items[0]))
            lines.append("\n### 北向资金")
            lines.append(f"- 北向净买入: {_safe_get(latest, 'north_net')}")
            lines.append(f"- 沪股通净买入: {_safe_get(latest, 'sh_net')}")
            lines.append(f"- 深股通净买入: {_safe_get(latest, 'sz_net')}")

    if margin:
        items = margin.get("data", {}).get("items", [])
        fields = margin.get("data", {}).get("fields", [])
        if items and fields:
            latest = dict(zip(fields, items[0]))
            lines.append("\n### 融资融券")
            lines.append(f"- 融资余额: {_safe_get(latest, 'rzye')}")
            lines.append(f"- 融券余额: {_safe_get(latest, 'rqye')}")

    lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。")
    return "\n".join(lines)


def analyze_limit(
    trade_date: str,
    limit_data: Optional[dict] = None,
    top_list: Optional[dict] = None,
) -> str:
    """涨跌停分析"""
    lines = [f"## {trade_date} 涨跌停分析"]

    if limit_data:
        items = limit_data.get("data", {}).get("items", [])
        fields = limit_data.get("data", {}).get("fields", [])

        up_stocks = []
        down_stocks = []
        for item in items:
            item_dict = dict(zip(fields, item))
            limit = _safe_get(item_dict, "limit")
            if limit == "Z":
                up_stocks.append(item_dict)
            elif limit == "D":
                down_stocks.append(item_dict)

        lines.append(f"\n### 涨停股({len(up_stocks)}只)")
        for i, s in enumerate(up_stocks[:15], 1):
            lines.append(f"  {i}. {_safe_get(s, 'name')}({_safe_get(s, 'ts_code')}) 封板时间: {_safe_get(s, 'first_time')}")

        lines.append(f"\n### 跌停股({len(down_stocks)}只)")
        for i, s in enumerate(down_stocks[:10], 1):
            lines.append(f"  {i}. {_safe_get(s, 'name')}({_safe_get(s, 'ts_code')})")

    if top_list:
        items = top_list.get("data", {}).get("items", [])
        fields = top_list.get("data", {}).get("fields", [])
        if items:
            lines.append(f"\n### 龙虎榜({len(items)}只)")
            for i, item in enumerate(items[:10], 1):
                item_dict = dict(zip(fields, item))
                lines.append(
                    f"  {i}. {_safe_get(item_dict, 'name')}({_safe_get(item_dict, 'ts_code')}) "
                    f"买入: {_safe_get(item_dict, 'buy_amount')} 卖出: {_safe_get(item_dict, 'sell_amount')}"
                )

    lines.append("\n> ⚠️ 以上分析仅供参考，不构成投资建议。")
    return "\n".join(lines)


def compare_stocks(
    stocks_data: dict[str, dict],
) -> str:
    """多股对比分析

    Args:
        stocks_data: {股票代码: {"basic": {...}, "daily": {...}, "daily_basic": {...}, "fina_indicator": {...}}}
    """
    lines = ["## 多股对比分析"]
    lines.append("\n### 基本对比")

    # 表头
    headers = ["指标"] + list(stocks_data.keys())
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    # 基本信息行
    row_name = ["名称"]
    row_price = ["最新价"]
    row_pe = ["PE"]
    row_pb = ["PB"]
    row_roe = ["ROE"]
    row_change = ["涨跌幅"]

    for ts_code, data in stocks_data.items():
        basic = data.get("basic", {})
        daily = data.get("daily", {})
        db = data.get("daily_basic", {})
        fi = data.get("fina_indicator", {})

        row_name.append(_safe_get(basic, "name"))
        row_price.append(_safe_get(daily, "close"))
        row_pe.append(_safe_get(db, "pe"))
        row_pb.append(_safe_get(db, "pb"))
        row_roe.append(_safe_get(fi, "roe") + "%" if _safe_get(fi, "roe") != "N/A" else "N/A")
        row_change.append(_safe_get(daily, "pct_chg") + "%" if _safe_get(daily, "pct_chg") != "N/A" else "N/A")

    for row in [row_name, row_price, row_pe, row_pb, row_roe, row_change]:
        lines.append("| " + " | ".join(row) + " |")

    lines.append("\n> ⚠️ 以上对比仅供参考，不构成投资建议。")
    return "\n".join(lines)
