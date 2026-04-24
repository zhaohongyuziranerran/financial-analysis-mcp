"""NeoData 金融数据API客户端

封装两种NeoData API:
1. 自然语言查询API (NL): 通过自然语言获取金融数据
2. 结构化数据API (Structured): 通过api_name精确查询209个接口
"""

import os
import stat
from pathlib import Path
from typing import Any, Optional

import httpx

# ========== 配置常量 ==========
NL_ENDPOINT = "https://copilot.tencent.com/agenttool/v1/neodata"
STRUCTURED_ENDPOINT = "https://www.codebuddy.cn/v2/tool/financedata"
TOKEN_FILE = Path.home() / ".workbuddy" / ".neodata_token"

# HTTP超时
TIMEOUT = 30.0


class NeoDataClient:
    """NeoData金融数据双模客户端"""

    def __init__(
        self,
        token: Optional[str] = None,
        nl_endpoint: Optional[str] = None,
        structured_endpoint: Optional[str] = None,
    ):
        self.token = token or self._read_token_file()
        self.nl_endpoint = nl_endpoint or os.getenv("NEODATA_NL_ENDPOINT", NL_ENDPOINT)
        self.structured_endpoint = structured_endpoint or os.getenv(
            "NEODATA_STRUCTURED_ENDPOINT", STRUCTURED_ENDPOINT
        )
        self._client: Optional[httpx.AsyncClient] = None

    # ========== Token管理 ==========

    @staticmethod
    def _read_token_file() -> Optional[str]:
        """从 ~/.workbuddy/.neodata_token 读取JWT token"""
        try:
            token = TOKEN_FILE.read_text().strip()
            return token if token else None
        except (FileNotFoundError, PermissionError):
            return None

    @staticmethod
    def save_token(token: str) -> None:
        """将JWT token写入文件(权限600)"""
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(token.strip())
        TOKEN_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def _get_auth_headers(self) -> dict[str, str]:
        """获取认证头"""
        if not self.token:
            raise ValueError(
                "未找到NeoData token。请通过环境变量NEODATA_TOKEN或~/.workbuddy/.neodata_token提供"
            )
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    # ========== HTTP客户端 ==========

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建异步HTTP客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=TIMEOUT)
        return self._client

    async def close(self) -> None:
        """关闭HTTP客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ========== 自然语言查询API ==========

    async def query_nl(
        self,
        query: str,
        data_type: str = "all",
    ) -> dict[str, Any]:
        """自然语言查询NeoData

        Args:
            query: 自然语言查询，如"贵州茅台最新股价"
            data_type: 数据类型 "all"(默认)/"api"/"doc"

        Returns:
            查询结果字典
        """
        headers = self._get_auth_headers()
        payload: dict[str, Any] = {
            "query": query,
            "channel": "neodata",
            "sub_channel": "workbuddy",
        }
        if data_type != "all":
            payload["data_type"] = data_type

        client = await self._get_client()
        resp = await client.post(self.nl_endpoint, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()

    # ========== 结构化数据API ==========

    async def query_structured(
        self,
        api_name: str,
        params: Optional[dict[str, Any]] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """结构化API查询

        Args:
            api_name: 接口名称，如"daily", "income", "stock_basic"
            params: 接口参数，如{"ts_code": "000001.SZ", "start_date": "20250101"}
            fields: 返回字段筛选，逗号分隔，如"ts_code,close,vol"

        Returns:
            {
                "code": 0,
                "msg": "",
                "data": {"fields": [...], "items": [[...], ...]}
            }
        """
        payload: dict[str, Any] = {"api_name": api_name}
        if params:
            payload["params"] = params
        if fields:
            payload["fields"] = fields

        client = await self._get_client()
        resp = await client.post(
            self.structured_endpoint,
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    # ========== 便捷方法：常用API封装 ==========

    async def get_stock_daily(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取股票日线行情

        Args:
            ts_code: 股票代码，如"000001.SZ"
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        """
        params = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_structured("daily", params, fields)

    async def get_stock_basic(
        self,
        ts_code: Optional[str] = None,
        list_status: str = "L",
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取股票基本信息

        Args:
            ts_code: 股票代码(可选)
            list_status: 上市状态 L上市 D退市 P暂停
        """
        params = {"list_status": list_status}
        if ts_code:
            params["ts_code"] = ts_code
        return await self.query_structured("stock_basic", params, fields)

    async def get_daily_basic(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取每日指标(PE/PB/换手率等)

        Args:
            ts_code: 股票代码
            trade_date: 交易日期 YYYYMMDD
        """
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        return await self.query_structured("daily_basic", params, fields)

    async def get_income(
        self,
        ts_code: str,
        period: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取利润表"""
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
        return await self.query_structured("income", params, fields)

    async def get_balancesheet(
        self,
        ts_code: str,
        period: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取资产负债表"""
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
        return await self.query_structured("balancesheet", params, fields)

    async def get_cashflow(
        self,
        ts_code: str,
        period: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取现金流量表"""
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
        return await self.query_structured("cashflow", params, fields)

    async def get_fina_indicator(
        self,
        ts_code: str,
        period: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取财务指标(ROE/毛利率等)"""
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
        return await self.query_structured("fina_indicator", params, fields)

    async def get_moneyflow(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取个股资金流向"""
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        return await self.query_structured("moneyflow", params, fields)

    async def get_moneyflow_hsgt(
        self,
        trade_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取沪深港通资金流向(北向资金)"""
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        return await self.query_structured("moneyflow_hsgt", params, fields)

    async def get_limit_list_d(
        self,
        trade_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取涨跌停和炸板数据"""
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        return await self.query_structured("limit_list_d", params, fields)

    async def get_top_list(
        self,
        trade_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取龙虎榜数据"""
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        return await self.query_structured("top_list", params, fields)

    async def get_index_daily(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取指数日线行情"""
        params = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_structured("index_daily", params, fields)

    async def get_fund_nav(
        self,
        ts_code: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取基金净值"""
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if end_date:
            params["end_date"] = end_date
        return await self.query_structured("fund_nav", params, fields)

    async def get_shibor(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取Shibor利率"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_structured("shibor", params, fields)

    async def get_cn_gdp(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取GDP数据"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_structured("cn_gdp", params, fields)

    async def get_cn_cpi(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取CPI数据"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_structured("cn_cpi", params, fields)

    async def get_cn_ppi(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取PPI数据"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_structured("cn_ppi", params, fields)

    async def get_index_weight(
        self,
        index_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取指数成分和权重"""
        params = {"index_code": index_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_structured("index_weight", params, fields)

    async def get_news(
        self,
        src: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取新闻快讯"""
        params = {}
        if src:
            params["src"] = src
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_structured("news", params, fields)

    async def get_ths_daily(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取同花顺概念和行业指数行情"""
        params = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_structured("ths_daily", params, fields)

    async def get_hm_detail(
        self,
        trade_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取游资交易每日明细"""
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        return await self.query_structured("hm_detail", params, fields)

    async def get_fx_daily(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取外汇日线行情"""
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_structured("fx_daily", params, fields)

    async def get_margin(
        self,
        trade_date: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取融资融券交易汇总"""
        params = {}
        if trade_date:
            params["trade_date"] = trade_date
        return await self.query_structured("margin", params, fields)

    async def get_report_rc(
        self,
        ts_code: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取券商盈利预测"""
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        return await self.query_structured("report_rc", params, fields)
