"""Base Data Provider - Provider 模板基类

提供公共逻辑：
- 字段映射（FIELD_MAPPINGS → 系统标准字段）
- 数据去重（按 update_flag 保留最新）
- 模板方法（子类实现 _fetch_*）

使用方式：
    class MyProvider(BaseDataProvider):
        MARKET_CODE = "A"
        
        FIELD_MAPPINGS = {
            "balance_sheet": {...},
            "income_statement": {...},
        }
        
        def _normalize_symbol(self, symbol: str) -> str:
            # 实现代码转换
            return symbol
        
        def _fetch_all_financials(self, symbol, start_year, end_year, fields) -> pd.DataFrame:
            # 调用 API，返回合并后的 DataFrame
            return df
        
        def _fetch_indicators_impl(self, symbol, start_year, end_year) -> pd.DataFrame:
            return df
        
        def _fetch_market_impl(self, symbol) -> pd.DataFrame:
            return df
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseDataProvider(ABC):
    """Provider 模板基类
    
    Template Method 模式：公共逻辑自动包裹，子类只需实现 _fetch_* 方法。
    
    Features:
    - 字段映射支持（native fields → standard fields）
    - 数据去重（按 update_flag 保留最新）
    - 模板方法自动调用数据处理
    """

    # ========================================================================
    # 子类必须定义
    # ========================================================================

    # 市场代码：子类必须定义
    MARKET_CODE: str = ""

    # 字段映射: {statement_type: {native_field: standard_field}}
    FIELD_MAPPINGS: dict[str, dict[str, str]] = {
        "balance_sheet": {},
        "income_statement": {},
        "cash_flow": {},
        "indicators": {},
        "market": {},
    }

    # ========================================================================
    # 公共接口 - 模板方法
    # ========================================================================

    def fetch_financials(
        self,
        symbol: str,
        fields: set[str],
        end_year: int,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """获取财务报表数据（模板方法）
        
        自动执行：获取 → 映射 → 去重 → 过滤字段
        
        Args:
            symbol: 股票代码
            fields: 需要的字段集合
            end_year: 结束年份
            years: 年数
            
        Returns:
            DataFrame with mapped fields only, or None
        """
        if not fields:
            return None

        start_year = end_year - years + 1
        normalized_symbol = self._normalize_symbol(symbol)

        # 获取数据
        df = self._fetch_all_financials(normalized_symbol, start_year, end_year, fields)
        if df is None or df.empty:
            return None

        # 字段映射
        df = self._apply_mapping(df)

        # 去重
        df = self._deduplicate(df)

        # 过滤：只保留映射后的字段和日期列，返回拷贝
        return self._filter_to_mapped_fields(df, fields)

    def fetch_indicators(
        self,
        symbol: str,
        fields: set[str],
        end_year: int,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """获取财务指标数据（模板方法）
        
        Args:
            symbol: 股票代码
            fields: 需要的字段集合
            end_year: 结束年份
            years: 年数
            
        Returns:
            DataFrame with mapped fields only, or None
        """
        if not fields:
            return None

        start_year = end_year - years + 1
        normalized_symbol = self._normalize_symbol(symbol)

        df = self._fetch_indicators_impl(normalized_symbol, start_year, end_year)
        if df is None or df.empty:
            return None

        df = self._apply_mapping(df)
        df = self._deduplicate(df)

        # 过滤：只保留映射后的字段和日期列，返回拷贝
        return self._filter_to_mapped_fields(df, fields)

    def fetch_market(
        self,
        symbol: str,
        fields: set[str],
    ) -> pd.DataFrame | None:
        """获取市场数据（模板方法）
        
        Args:
            symbol: 股票代码
            fields: 需要的字段集合
            
        Returns:
            DataFrame with mapped fields only, or None
        """
        if not fields:
            return None

        normalized_symbol = self._normalize_symbol(symbol)

        df = self._fetch_market_impl(normalized_symbol)
        if df is None or df.empty:
            return None

        df = self._apply_mapping(df)

        # 过滤：只保留映射后的字段和日期列，返回拷贝
        return self._filter_to_mapped_fields(df, fields)

    def fetch_historical(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        adjust: str = "hfq",
    ) -> pd.DataFrame | None:
        """获取历史交易数据（模板方法）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)，可选
            end_date: 结束日期 (YYYY-MM-DD)，可选
            adjust: 复权方式（默认 "hfq" 后复权）
                - "": 不复权
                - "qfq": 前复权
                - "hfq": 后复权
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
            or None if not supported
        """
        normalized_symbol = self._normalize_symbol(symbol)

        df = self._fetch_historical_impl(normalized_symbol, start_date, end_date, adjust)
        if df is None or df.empty:
            return None

        # 日期过滤
        if start_date and "date" in df.columns:
            start_dt = pd.to_datetime(start_date)
            df = df[pd.to_datetime(df["date"]) >= start_dt]
        if end_date and "date" in df.columns:
            end_dt = pd.to_datetime(end_date)
            df = df[pd.to_datetime(df["date"]) <= end_dt]

        return df.copy() if not df.empty else None

    # ========================================================================
    # 子类必须实现的方法
    # ========================================================================

    @abstractmethod
    def _normalize_symbol(self, symbol: str) -> str:
        """标准化股票代码
        
        将不同格式的股票代码转换为 API 需要的格式。
        
        Args:
            symbol: 原始股票代码
            
        Returns:
            标准化后的代码
        """
        pass

    @abstractmethod
    def _fetch_all_financials(
        self,
        symbol: str,
        start_year: int,
        end_year: int,
        fields: set[str],
    ) -> pd.DataFrame | None:
        """获取所有财务报表数据
        
        子类实现：调用 API 获取资产负债表、利润表、现金流量表，
        合并为一个 DataFrame。
        
        Args:
            symbol: 标准化后的股票代码
            start_year: 开始年份
            end_year: 结束年份
            fields: 需要的字段集合
            
        Returns:
            原始 DataFrame（未映射字段）
        """
        pass

    @abstractmethod
    def _fetch_indicators_impl(
        self,
        symbol: str,
        start_year: int,
        end_year: int,
    ) -> pd.DataFrame | None:
        """获取财务指标数据
        
        Args:
            symbol: 标准化后的股票代码
            start_year: 开始年份
            end_year: 结束年份
            
        Returns:
            原始 DataFrame
        """
        pass

    @abstractmethod
    def _fetch_market_impl(self, symbol: str) -> pd.DataFrame | None:
        """获取市场数据
        
        Args:
            symbol: 标准化后的股票代码
            
        Returns:
            原始 DataFrame
        """
        pass

    def _fetch_historical_impl(
        self,
        symbol: str,
        start_date: str | None,
        end_date: str | None,
        adjust: str,
    ) -> pd.DataFrame | None:
        """获取历史交易数据
        
        子类可选实现。默认返回 None（不支持）。
        
        Args:
            symbol: 标准化后的股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            adjust: 复权方式 ("", "qfq", "hfq")
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        return None

    # ========================================================================
    # 子类可覆盖的方法
    # ========================================================================

    def _get_date_column(self) -> str:
        """获取日期列名"""
        return "report_date"

    def _apply_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """应用字段映射
        
        自动识别 DataFrame 中存在的映射类型并应用。
        
        Args:
            df: 原始 DataFrame
            
        Returns:
            映射后的 DataFrame
        """
        if df is None or df.empty:
            return df

        # 按映射类型逐个应用
        for statement_type, mapping in self.FIELD_MAPPINGS.items():
            if not mapping:
                continue
            rename_map = {
                native: std
                for native, std in mapping.items()
                if native in df.columns
            }
            if rename_map:
                df = df.rename(columns=rename_map)

        return df

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据去重
        
        子类可覆盖实现特定市场的去重逻辑。
        默认实现：按日期去重，保留最新记录。
        """
        if df is None or df.empty:
            return df

        date_col = self._get_date_column()
        if date_col not in df.columns:
            return df

        df = df.sort_values(date_col, ascending=False)
        df = df.drop_duplicates(subset=[date_col], keep="first")

        return df

    def _filter_to_mapped_fields(
        self,
        df: pd.DataFrame,
        requested_fields: set[str],
    ) -> pd.DataFrame | None:
        """过滤到只保留映射后的字段
        
        只保留：
        1. 日期列
        2. 在 FIELD_MAPPINGS 中定义的标准字段
        3. 已被映射的列（那些值存在于映射表中的列）
        
        返回一个拷贝，与原始数据无关联。
        
        Args:
            df: DataFrame（已应用映射）
            requested_fields: 请求的字段集合
            
        Returns:
            过滤后的 DataFrame 拷贝，或 None
        """
        if df is None or df.empty:
            return df

        # 获取所有映射后的标准字段名
        mapped_standard_fields = self.get_supported_fields()

        # 日期列
        date_col = self._get_date_column()

        # 要保留的列 = 日期列 + 请求的且在映射中的字段
        cols_to_keep = set()

        # 添加日期列（如果存在）
        if date_col in df.columns:
            cols_to_keep.add(date_col)

        # 添加请求的字段（必须在映射表中定义）
        for field in requested_fields:
            if field in mapped_standard_fields:
                cols_to_keep.add(field)

        # 过滤列
        available_cols = set(df.columns) & cols_to_keep
        if not available_cols:
            return None

        # 返回拷贝，只包含需要的列
        return df[list(available_cols)].copy()

    # ========================================================================
    # 辅助方法
    # ========================================================================

    @classmethod
    def get_supported_fields(cls) -> set[str]:
        """获取 Provider 支持的所有字段"""
        fields = set()
        for mapping_dict in cls.FIELD_MAPPINGS.values():
            fields.update(mapping_dict.values())
        return fields

    @classmethod
    def get_fields_by_category(cls, category: str) -> set[str]:
        """获取指定类别的字段"""
        mapping = cls.FIELD_MAPPINGS.get(category, {})
        return set(mapping.values())
