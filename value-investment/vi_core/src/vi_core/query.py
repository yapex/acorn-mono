"""Query Engine - 统一查询接口

核心流程：
1. 预检 - 检查 items 可用性
2. 获取数据 - 从 Provider 或 Calculator
3. 返回结果 - 包含诊断信息
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TYPE_CHECKING

import pandas as pd

from .precheck import Prechecker, PrecheckResult
from .items import ItemRegistry, ItemSource

if TYPE_CHECKING:
    import pluggy


@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    symbol: str
    data: dict[str, Any] = field(default_factory=dict)
    available: list[str] = field(default_factory=list)   # 可用的 items
    unavailable: list[str] = field(default_factory=list)  # 不可用的 items
    issues: list[dict] = field(default_factory=list)      # 问题详情
    precheck: PrecheckResult | None = None


class QueryEngine:
    """查询引擎
    
    统一的查询接口，负责：
    1. 调用 Prechecker 进行预检
    2. 调用 _fetch_data 获取 Field 数据
    3. 调用 _run_calculators 运行 Calculator
    4. 返回包含诊断信息的 QueryResult
    """
    
    def __init__(
        self,
        prechecker: Prechecker | None = None,
        registry: ItemRegistry | None = None,
        plugin_manager: Any | None = None,
        years: int = 10,
        end_year: int | None = None,
    ):
        """
        Args:
            prechecker: 预检器
            registry: Item 注册表
            plugin_manager: pluggy 插件管理器（用于调用 hooks）
            years: 查询的年份数
            end_year: 结束年份（默认自动判断）
        """
        self._prechecker = prechecker or Prechecker()
        self._registry = registry or ItemRegistry()
        self._pm = plugin_manager
        self.years = years
        self.end_year = end_year
    
    @property
    def provider_fields(self) -> set[str]:
        """返回当前配置的 provider fields"""
        return self._prechecker._provider_fields
    
    def query(self, symbol: str, items: list[str]) -> QueryResult:
        """执行查询
        
        Args:
            symbol: 股票代码
            items: 要查询的 items
            
        Returns:
            QueryResult: 查询结果
        """
        # 1. 预检
        precheck_result = self._precheck(symbol, items)
        
        if not precheck_result.available:
            return QueryResult(
                success=False,
                symbol=symbol,
                available=[],
                unavailable=[i.item for i in precheck_result.issues],
                issues=[{
                    "item": i.item,
                    "reason": i.reason,
                    "suggestion": i.suggestion,
                } for i in precheck_result.issues],
                precheck=precheck_result,
            )
        
        # 2. 获取数据
        data = self._fetch_data(symbol, precheck_result.available)
        
        # 3. 运行 Calculator（如果有待计算的 items）
        calc_items = [item for item in precheck_result.available 
                      if self._registry.get(item).source == ItemSource.CALCULATOR]
        if calc_items:
            calc_results = self._run_calculators(calc_items, data)
            data.update(calc_results)
        
        return QueryResult(
            success=True,
            symbol=symbol,
            data=data,
            available=precheck_result.available,
            unavailable=[i.item for i in precheck_result.issues],
            issues=[{
                "item": i.item,
                "reason": i.reason,
                "suggestion": i.suggestion,
            } for i in precheck_result.issues],
            precheck=precheck_result,
        )
    
    def _precheck(self, symbol: str, items: list[str]) -> PrecheckResult:
        """执行预检"""
        return self._prechecker.check(symbol, items)
    
    def _fetch_data(self, symbol: str, items: list[str]) -> dict[str, Any]:
        """获取数据 - 使用 vi_provide_items
        
        通过 pluggy hooks 调用 Provider 获取 Field 数据。
        新的 vi_provide_items hook 让 Provider 主动决定能提供哪些字段。
        
        Args:
            symbol: 股票代码
            items: 可用的 items 列表（排除 Calculator items）
            
        Returns:
            {item: {year: value}} 格式的数据字典
        """
        if not self._pm or not items:
            return {}
        
        # 推断市场
        market = self._infer_market(symbol)
        
        # 计算 end_year
        end_year = self._get_end_year()
        
        # 广播给所有 Provider
        results = self._pm.hook.vi_provide_items(
            items=items,
            symbol=symbol,
            market=market,
            end_year=end_year,
            years=self.years,
        )
        
        # 合并所有 Provider 返回的 DataFrames
        dfs = [r for r in results if r is not None and not r.empty]
        merged_df = self._merge_dfs(dfs)
        
        # 转换为 {field: {year: value}} 格式
        return self._df_to_result_dict(merged_df)
    
    def _run_calculators(
        self, 
        calc_items: list[str], 
        field_data: dict[str, Any]
    ) -> dict[str, Any]:
        """运行 Calculator
        
        通过 pluggy hook 调用 Calculator。支持 Calculator 之间的依赖：
        - 按拓扑排序确定计算顺序
        - 先计算的 Calculator 结果会加入 DataFrame，供后续 Calculator 使用
        
        Args:
            calc_items: 需要运行的 Calculator 名称列表
            field_data: 已有的 Field 数据 {field: {year: value}}
            
        Returns:
            {calculator_name: {year: value}} 格式的计算结果
        """
        if not self._pm or not calc_items or not field_data:
            return {}
        
        # 获取 Calculator 列表
        calc_list = self._pm.hook.vi_list_calculators()
        if not calc_list:
            return {}
        
        # Flatten if nested (pluggy returns [[...]])
        if calc_list and isinstance(calc_list[0], list):
            calc_list = calc_list[0]
        
        # 构建 Calculator 注册表
        calc_registry: dict[str, dict] = {}
        for calc in calc_list:
            calc_registry[calc["name"]] = calc
        
        # 转换 field_data (dict) 为 DataFrame 用于计算器
        # {field: {year: value}} -> DataFrame(index=year, columns=field)
        if not field_data:
            return {}
        
        # 构建 DataFrame: {field: {year: value}}
        # pd.DataFrame(field_data) creates: rows=years, columns=fields
        # After .T: rows=fields, columns=years
        try:
            df = pd.DataFrame(field_data).T  # 转置：field 为行，year 为列
            df.columns = df.columns.astype(int)  # 列名是年份
            # index 现在是 field names
        except Exception:
            return {}
        
        # 拓扑排序：对 calc_items 按依赖关系排序
        sorted_calcs = self._topological_sort(calc_items, calc_registry, df)
        
        results: dict[str, Any] = {}
        
        # 按拓扑顺序运行每个 Calculator
        for calc_name in sorted_calcs:
            if calc_name not in calc_registry:
                continue
            
            calc_spec = calc_registry[calc_name]
            required_fields = list(calc_spec.get("required_fields", []))
            
            # 检查所需字段是否都可用 (df.index 是 field names)
            available_fields = set(df.index)
            missing = set(required_fields) - available_fields
            if missing:
                continue
            
            # 提取所需字段 (每列是一个 field，返回 pd.Series)
            calc_data: dict[str, pd.Series] = {
                field: df.loc[field] for field in required_fields if field in df.index
            }
            
            # 调用 hook 运行 Calculator
            config = {}  # 可扩展：支持 calculator_config
            calc_result = self._pm.hook.vi_run_calculator(
                name=calc_name,
                data=calc_data,
                config=config,
            )
            
            if calc_result is None:
                continue
            
            # 检查 Calculator 错误
            if isinstance(calc_result, dict) and calc_result.get("__error__"):
                continue
            
            # 接受 pd.Series 或 dict
            if isinstance(calc_result, pd.Series):
                result_dict = {int(year): val for year, val in calc_result.items()}
            elif isinstance(calc_result, dict):
                result_dict = {int(year) if str(year).isdigit() else year: val 
                             for year, val in calc_result.items()}
            else:
                continue
            
            results[calc_name] = result_dict
            
            # 将计算结果加入 DataFrame，供后续 Calculator 使用
            for year, value in result_dict.items():
                if year not in df.columns:
                    # 添加新的年份列
                    df[year] = float('nan')
                df.loc[calc_name, year] = value
        
        return results
    
    def _topological_sort(
        self, 
        calc_items: list[str], 
        calc_registry: dict[str, dict],
        df: pd.DataFrame,
    ) -> list[str]:
        """拓扑排序 - 按依赖顺序排序 Calculator
        
        基于 Calculator 的 required_fields 进行拓扑排序。
        如果一个 Calculator 的 required_fields 包含另一个 Calculator 的输出，
        则被依赖的 Calculator 需要先计算。
        
        Args:
            calc_items: 需要排序的 Calculator 列表
            calc_registry: Calculator 注册表
            df: 当前可用的字段 DataFrame
            
        Returns:
            排序后的 Calculator 列表
        """
        # 构建依赖图：{calc_name: set of deps}
        # graph[calc_name] = set of calculators that calc_name depends on
        graph: dict[str, set[str]] = {}
        dependents: dict[str, set[str]] = {}  # 反向索引：谁依赖这个 Calculator
        all_calc_names = set(calc_items)
        
        for calc_name in calc_items:
            if calc_name not in calc_registry:
                continue
            
            calc_spec = calc_registry[calc_name]
            required_fields = set(calc_spec.get("required_fields", []))
            
            # 找出 required_fields 中哪些是其他 Calculator
            deps = required_fields & all_calc_names
            graph[calc_name] = deps
            
            # 构建反向索引
            for dep in deps:
                if dep not in dependents:
                    dependents[dep] = set()
                dependents[dep].add(calc_name)
        
        # Kahn's algorithm
        # in_degree[calc] = 该 Calculator 依赖的 Calculator 数量
        in_degree: dict[str, int] = {
            calc: len(deps) for calc, deps in graph.items()
        }
        
        # 从 in_degree=0 的节点开始（没有依赖的，被其他 Calculator 依赖的）
        # 这些应该先执行
        queue = [calc for calc, degree in in_degree.items() if degree == 0]
        sorted_calcs = []
        
        while queue:
            # 取出没有依赖的 Calculator（可以被计算了）
            current = queue.pop(0)
            sorted_calcs.append(current)
            
            # 减少依赖该 Calculator 的节点的 in_degree
            if current in dependents:
                for dependent in dependents[current]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # 处理循环依赖：剩余的节点按原始顺序返回
        remaining = [c for c in calc_items if c not in sorted_calcs and c in calc_registry]
        
        return sorted_calcs + remaining
    
    def _get_end_year(self) -> int:
        """获取查询结束年份
        
        年报通常在次年 4 月发布。
        如果当前月份 < 4，使用前年（确保年报已发布）
        如果当前月份 >= 4，使用去年
        """
        if self.end_year is not None:
            return self.end_year
        
        now = datetime.now()
        if now.month < 4:
            return now.year - 2
        else:
            return now.year - 1
    
    def _infer_market(self, symbol: str) -> str:
        """从股票代码推断市场
        
        Args:
            symbol: 股票代码
            
        Returns:
            市场代码: "A", "HK", 或 "US"
        """
        # A股：纯数字（6位）
        if symbol.isdigit() and len(symbol) == 6:
            return "A"
        # 港股：以0开头的5位数字（如00700）
        if len(symbol) == 5 and symbol.isdigit():
            return "HK"
        # 美股：字母（如AAPL）
        if symbol.isalpha():
            return "US"
        # 默认尝试HK
        return "HK"
    
    def _merge_dfs(self, dfs: list[pd.DataFrame]) -> pd.DataFrame | None:
        """合并多个 DataFrame
        
        Args:
            dfs: DataFrame 列表
            
        Returns:
            合并后的 DataFrame 或 None
        """
        if not dfs:
            return None
        
        fiscal_year = "fiscal_year"
        
        # Start with first DataFrame
        result = dfs[0].copy()
        
        # 确保 fiscal_year 是 index
        if fiscal_year in result.columns:
            result = result.set_index(fiscal_year)
        
        # Merge remaining DataFrames
        for df in dfs[1:]:
            if df is None or df.empty:
                continue
            
            df_to_merge = df.copy()
            
            if fiscal_year in df_to_merge.columns:
                df_to_merge = df_to_merge.set_index(fiscal_year)
            
            # 找出需要添加的新列
            cols_to_add = [c for c in df_to_merge.columns if c not in result.columns]
            
            if not cols_to_add:
                continue
            
            # 特殊情况：单行数据（如 market_cap），广播到所有行
            if len(df_to_merge) == 1:
                for col in cols_to_add:
                    result[col] = df_to_merge[col].iloc[0]
            else:
                result = result.merge(
                    df_to_merge[cols_to_add],
                    left_index=True,
                    right_index=True,
                    how="left"
                )
        
        return result
    
    def _df_to_result_dict(self, df: pd.DataFrame | None) -> dict[str, Any]:
        """将 DataFrame 转换为 {field: {year: value}} 格式
        
        Args:
            df: DataFrame with fiscal_year as index
            
        Returns:
            {field: {year: value}} 格式的 dict
        """
        if df is None or df.empty:
            return {}
        
        # 删除 NaN 行
        df = df.dropna(how='all')
        
        return df.to_dict()