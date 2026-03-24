"""VI Core Pluggy Plugin

Provides:
- Field registry and specs
- Query engine
- Calculator registry
"""
from __future__ import annotations

import sys
from importlib.metadata import entry_points
from typing import Any, TYPE_CHECKING

import pandas as pd
import pluggy  # type: ignore[import]
from loguru import logger

from .spec import vi_hookimpl, ValueInvestmentSpecs, EvolutionSpec
from vi_fields_extension import StandardFields

if TYPE_CHECKING:
    from acorn_events import EventBus


# Entry point groups for VI sub-plugins
VI_ENTRY_POINT_GROUPS = (
    "value_investment.fields",
    "value_investment.providers",
    "value_investment.calculators",
)


def _get_entry_points(group: str) -> Any:
    """Get entry points by group, compatible with Python 3.9-3.12"""
    try:
        return entry_points(group=group)
    except TypeError:
        eps = entry_points()
        if hasattr(eps, "select"):
            return eps.select(group=group)
        elif isinstance(eps, dict):
            return eps.get(group, [])
        return []


def _df_to_result_dict(df: pd.DataFrame | None) -> dict:
    """将 DataFrame 转换为 RPC 返回格式
    
    Args:
        df: DataFrame with fiscal_year as column or index
        
    Returns:
        {field: {year: value}} 格式的 dict
    """
    if df is None or df.empty:
        return {}
    
    fiscal_year = StandardFields.fiscal_year
    
    # 确保 fiscal_year 是 index
    if fiscal_year in df.columns:
        df = df.set_index(fiscal_year)
    elif df.index.name != fiscal_year:
        logger.warning("_df_to_result_dict: missing fiscal_year, columns={}", list(df.columns))
        return {}
    
    # 删除 NaN 行
    df = df.dropna(how='all')
    
    return df.to_dict()


def _merge_dfs(dfs: list[pd.DataFrame]) -> pd.DataFrame | None:
    """Merge multiple DataFrames on fiscal_year
    
    所有 Provider 必须输出 fiscal_year 列。
    
    Args:
        dfs: List of DataFrames with fiscal_year column
        
    Returns:
        Merged DataFrame with fiscal_year as index, or None
    """
    if not dfs:
        return None
    
    fiscal_year = StandardFields.fiscal_year
    
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
        
        # 确保 fiscal_year 是 index
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
            # 按 index (fiscal_year) 合并
            result = result.merge(
                df_to_merge[cols_to_add],
                left_index=True,
                right_index=True,
                how="left"
            )
    
    return result


class ViCorePlugin:
    """VI Core plugin for pluggy

    Provides commands for querying financial data.

    Args:
        event_bus: 事件总线实例（IOC: 通过依赖注入获得）
    """

    # Class-level plugin manager reference
    _pm: Any = None

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus  # IOC: 由外部注入或延迟初始化

    def _get_default_event_bus(self) -> EventBus:
        """获取默认事件总线（延迟导入避免循环依赖）"""
        from acorn_events import EventBus
        return EventBus()

    @classmethod
    def set_plugin_manager(cls, pm: Any) -> None:
        """Set the plugin manager for field collection"""
        cls._pm = pm

    @classmethod
    def _get_plugin_manager(cls) -> Any:
        """Get or create the VI plugin manager"""
        if cls._pm is None:
            cls._pm = cls._create_plugin_manager()
        return cls._pm

    @classmethod
    def _create_plugin_manager(cls) -> Any:
        """Create pluggy plugin manager and discover sub-plugins"""
        pm = pluggy.PluginManager("value_investment")
        pm.add_hookspecs(ValueInvestmentSpecs)
        
        # 添加 Evolution Hook（框架级）
        pm.add_hookspecs(EvolutionSpec)

        # Discover and register sub-plugins via entry_points
        for group in VI_ENTRY_POINT_GROUPS:
            for ep in _get_entry_points(group):
                try:
                    pm.register(ep.load(), name=ep.name)
                except Exception as e:
                    print(f"Warning: Failed to load {group}:{ep.name}: {e}", file=sys.stderr)

        return pm

    # =============================================================================
    # Genes Interface (Acorn Core)
    # =============================================================================

    @property
    def commands(self) -> list[str]:
        """Return supported commands for Acorn Core"""
        return ["vi_query", "vi_list_fields", "vi_list_calculators", "vi_register_calculator"]

    def handle(self, task: Any) -> dict[str, Any]:
        """Handle task for Acorn Core"""
        command = task.command
        args = task.args or {}
        return self._handle(command, args)

    @vi_hookimpl
    def vi_commands(self) -> list[str]:
        """Return supported commands"""
        return ["list_fields", "query"]

    @vi_hookimpl
    def vi_fields(self) -> Any:
        """Return core fields (empty, fields come from plugins)"""
        return {
            "source": "core",
            "fields": {},
            "description": "Core - fields defined by plugins",
        }

    @vi_hookimpl
    def vi_status(self) -> dict[str, Any]:
        """Return plugin status for acorn status command
        
        收集所有子插件的状态信息，拼接成完整的状态报告。
        """
        status = {
            "name": "vi",
            "description": "Value Investment - 财务数据查询",
            "version": "1.0.0",
            "capabilities": {
                "calculators": [],
                "fields": [],
                "providers": [],
            },
            "config": {},
        }
        
        pm = self._get_plugin_manager()
        if not pm:
            return status
        
        # 收集计算器
        calc_list = pm.hook.vi_list_calculators()
        if calc_list:
            if calc_list and isinstance(calc_list[0], list):
                calc_list = calc_list[0]
            status["capabilities"]["calculators"] = [
                {
                    "name": calc.get("name"),
                    "description": calc.get("description", ""),
                    "required_fields": calc.get("required_fields", []),
                }
                for calc in calc_list
            ]
        
        # 收集字段
        seen_fields = set()
        for fields_result in pm.hook.vi_fields():
            if fields_result:
                source = fields_result.get("source", "unknown")
                fields_dict = fields_result.get("fields", {})
                for field_name in fields_dict.keys():
                    if field_name not in seen_fields:
                        seen_fields.add(field_name)
                        status["capabilities"]["fields"].append(field_name)
        
        # 收集数据源
        for market_result in pm.hook.vi_markets():
            if market_result:
                if isinstance(market_result, list):
                    status["capabilities"]["providers"].extend(market_result)
                else:
                    status["capabilities"]["providers"].append(market_result)
        
        return status

    @vi_hookimpl
    def vi_handle(self, command: str, args: dict[str, Any]) -> dict[str, Any]:
        """Handle commands via pluggy"""
        return self._handle(command, args)

    def _handle(self, command: str, args: dict[str, Any]) -> dict[str, Any]:
        """Internal command handler"""
        # Strip "vi_" prefix if present
        internal_cmd = command[3:] if command.startswith("vi_") else command

        if internal_cmd == "list_fields":
            return self._list_fields(args)
        elif internal_cmd == "query":
            return self._query(args)
        elif internal_cmd == "list_calculators":
            return self._list_calculators(args)
        elif internal_cmd == "register_calculator":
            return self._register_calculator(args)
        return {"success": False, "error": f"Unknown command: {command}"}

    def _list_fields(self, args: dict[str, Any]) -> dict[str, Any]:
        """List all available fields from all plugins"""
        all_fields: dict[str, dict] = {}

        # Collect fields from all plugins via vi_fields hook
        if self._get_plugin_manager():
            for result in self._get_plugin_manager().hook.vi_fields():
                if result:
                    source = result.get("source", "unknown")
                    fields = result.get("fields", {})
                    # fields 现在是 dict: {field_name: {description: ...}}
                    for field_name, field_info in fields.items():
                        if field_name not in all_fields:
                            all_fields[field_name] = {
                                "source": source,
                                "description": field_info.get("description", ""),
                            }

        source = args.get("source")
        prefix = args.get("prefix")

        fields = list(all_fields.keys())

        if source:
            fields = [f for f in fields if all_fields[f]["source"] == source]

        if prefix:
            fields = [f for f in fields if f.startswith(prefix)]

        # Build by_source as {source: [field_names]} for CLI compatibility
        by_source: dict[str, list[str]] = {}
        for f in sorted(fields):
            src = all_fields[f]["source"]
            if src not in by_source:
                by_source[src] = []
            by_source[src].append(f)

        return {
            "success": True,
            "data": {
                "fields": sorted(fields),
                "by_source": by_source,
                "descriptions": {f: all_fields[f]["description"] for f in sorted(fields)},
            }
        }

    def _query(self, args: dict[str, Any]) -> dict[str, Any]:
        """Query financial data from providers

        Args:
            symbol: Stock code (e.g. "600519", "000001")
            fields: Comma-separated field names or "all"
            end_year: End year (default current year)
            years: Number of years to fetch (default 10)
            calculators: Comma-separated calculator names (e.g. "implied_growth")
            calculator_config: Dict of {calculator_name: config_dict}

        Returns:
            {"success": True, "data": {...}}
        """
        symbol = args.get("symbol")
        if not symbol:
            return {"success": False, "error": "Missing required argument: symbol"}

        fields_str = args.get("fields") or ""
        end_year = args.get("end_year")
        years = args.get("years", 10)
        calculators_str = args.get("calculators") or ""
        calculator_config = args.get("calculator_config") or {}

        # Parse end_year: 智能判断默认值
        # 年报通常在次年 4 月发布
        # 如果当前月份 < 4，使用前年（确保年报已发布）
        # 如果当前月份 >= 4，使用去年
        if end_year is None:
            from datetime import datetime
            now = datetime.now()
            if now.month < 4:
                end_year = now.year - 2  # 去年年报还未发布，用前年
            else:
                end_year = now.year - 1  # 去年年报已发布
        else:
            end_year = int(end_year)
        years = int(years)

        # Parse calculators
        requested_calculators = set(
            c.strip() for c in calculators_str.split(",") if c.strip()
        )

        # Parse fields
        if not self._get_plugin_manager():
            return {"success": False, "error": "Plugin manager not initialized"}

        # 获取系统标准字段（vi_fields hook 返回所有插件定义的字段）
        standard_fields: set[str] = set()
        for result in self._get_plugin_manager().hook.vi_fields():
            if result:
                # vi_fields 返回格式: {field_name: {description: ...}}
                fields_dict = result.get("fields", {})
                standard_fields.update(fields_dict.keys())

        # 获取 Provider 支持的字段（vi_supported_fields hook 返回 Provider 实际能提供的字段）
        provider_fields: set[str] = set()
        for result in self._get_plugin_manager().hook.vi_supported_fields():
            if result:
                provider_fields.update(result)

        if fields_str.lower() == "all":
            requested = standard_fields
            fields = provider_fields
        else:
            requested = set(f.strip() for f in fields_str.split(",") if f.strip())
            # 检查缺失的字段（系统能力不足）
            # unsupported: 请求的字段不在系统标准字段定义中
            # unfilled: 请求的字段在标准中，但 Provider 不支持
            unsupported = requested - standard_fields  # 系统不知道这个字段
            unfilled = requested & (standard_fields - provider_fields)  # 系统有但 Provider 不支持

            # 发布能力缺失事件（统一使用 evo.capability.missing）
            if unsupported or unfilled:
                from acorn_events import AcornEvents
                event_bus = self._event_bus or self._get_default_event_bus()
                
                # 字段缺失 → 能力缺失
                missing_fields = list(unsupported | unfilled)
                if missing_fields:
                    event_bus.publish(
                        AcornEvents.EVO_CAPABILITY_MISSING,
                        sender=self,
                        capability_type="field",
                        name=",".join(missing_fields),
                        context={"symbol": symbol, "unsupported": list(unsupported), "unfilled": list(unfilled)},
                    )

            # 最终使用的字段是请求的字段和 Provider 支持字段的交集
            fields = requested & provider_fields

        if not fields and not requested_calculators:
            return {"success": False, "error": "No valid fields specified"}

        # Categorize fields
        indicator_fields = fields & {
            "roe", "roa", "gross_margin", "net_profit_margin",
            "current_ratio", "quick_ratio", "debt_ratio", "asset_turnover",
            "receivable_turnover", "roic", "basic_eps", "diluted_eps",
            "book_value_per_share", "cash_ratio", "ocf_to_debt",
            "interest_bearing_debt", "ebitda", "currentdebt_to_debt",
            "operating_profit_margin", "revenue_yoy", "net_profit_yoy",
        }

        # 市场数据 + 交易数据都通过 vi_fetch_market 获取
        market_fields = fields & {
            "market_cap", "circ_market_cap", "circ_shares", "pe_ratio", "pb_ratio",
            "close", "open", "high", "low", "volume",
        }

        financial_fields = fields - indicator_fields - market_fields

        # 收集所有 DataFrame
        dfs: list[pd.DataFrame] = []

        # Fetch from providers
        if financial_fields:
            for result in self._get_plugin_manager().hook.vi_fetch_financials(
                symbol=symbol,
                fields=financial_fields,
                end_year=end_year,
                years=years,
            ):
                if result is not None and not result.empty:
                    dfs.append(result)

        if indicator_fields:
            for result in self._get_plugin_manager().hook.vi_fetch_indicators(
                symbol=symbol,
                fields=indicator_fields,
                end_year=end_year,
                years=years,
            ):
                if result is not None and not result.empty:
                    dfs.append(result)

        if market_fields:
            for result in self._get_plugin_manager().hook.vi_fetch_market(
                symbol=symbol,
                fields=market_fields,
            ):
                if result is not None and not result.empty:
                    dfs.append(result)

        # Merge DataFrames
        merged_df = _merge_dfs(dfs)

        # 转换为可返回的格式
        result_data = _df_to_result_dict(merged_df)

        # Run calculators - 直接传入 DataFrame
        if requested_calculators:
            calc_results = self._run_calculators(merged_df, requested_calculators, calculator_config)
            for calc_name, series in calc_results.items():
                if series is not None and not series.empty:
                    # 尝试将 index 转换为整数年份
                    try:
                        result_data[calc_name] = {int(year): val for year, val in series.items()}
                    except (ValueError, TypeError):
                        # 如果 index 不是整数年份（如 'current'），直接返回整个 series
                        # 使用第一个值的年份作为 key，如果没有则用 "latest"
                        if len(series) > 0:
                            first_val = list(series.values())[0]
                            result_data[calc_name] = {"latest": first_val}

        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "end_year": end_year,
                "years": years,
                "data": result_data,
                "fields_fetched": list(result_data.keys()),
            }
        }

    def _run_calculators(
        self,
        df: pd.DataFrame | None,
        calculator_names: set[str],
        calculator_config: dict[str, Any],
    ) -> dict[str, pd.Series]:
        """Run calculators via hook and return results
        
        Args:
            df: DataFrame with financial data (index=year, columns=field names)
            calculator_names: Calculator names to run
            calculator_config: Calculator-specific config
            
        Returns:
            {calculator_name: pd.Series} dict
        """
        if df is None or df.empty or not self._get_plugin_manager():
            return {}

        # Get available calculators
        calc_list = self._get_plugin_manager().hook.vi_list_calculators()
        if not calc_list:
            return {}

        # Flatten if nested (pluggy returns [[...]])
        if calc_list and isinstance(calc_list[0], list):
            calc_list = calc_list[0]

        # Build calculator registry
        calc_registry: dict[str, dict] = {}
        for calc in calc_list:
            calc_registry[calc["name"]] = calc

        results: dict[str, pd.Series] = {}

        # Run each requested calculator via hook
        for calc_name in calculator_names:
            if calc_name not in calc_registry:
                # 计算器不存在，发布能力缺失事件
                from acorn_events import AcornEvents
                event_bus = self._event_bus or self._get_default_event_bus()
                event_bus.publish(
                    AcornEvents.EVO_CAPABILITY_MISSING,
                    sender=self,
                    capability_type="calculator",
                    name=calc_name,
                    context={"symbol": df.index[0] if len(df) > 0 else None},
                )
                continue

            calc_spec = calc_registry[calc_name]
            required_fields = list(calc_spec.get("required_fields", []))

            # Check if all required fields are available
            missing = set(required_fields) - set(df.columns)
            if missing:
                continue  # Skip this calculator

            # Extract only the required fields from DataFrame
            # Build dict format: {field: pd.Series}
            calc_data: dict[str, pd.Series] = {
                field: df[field] for field in required_fields if field in df.columns
            }

            # Call hook to run calculator
            config = calculator_config.get(calc_name, {})
            calc_result = self._get_plugin_manager().hook.vi_run_calculator(
                name=calc_name,
                data=calc_data,
                config=config,
            )

            if calc_result is None:
                continue  # Calculator not found

            # Check for calculator error
            if isinstance(calc_result, dict) and calc_result.get("__error__"):
                continue  # Skip error results

            # Accept pd.Series or dict
            if calc_result is not None:
                if isinstance(calc_result, pd.Series):
                    results[calc_name] = calc_result
                elif isinstance(calc_result, dict):
                    results[calc_name] = pd.Series(calc_result)

        return results

    def _find_evolution_spec(
        self,
        capability_type: str,
        name: str,
        context: dict | None = None,
    ) -> str | None:
        """
        遍历所有插件，查找进化规范
        
        Args:
            capability_type: 能力类型（如 "calculator"）
            name: 能力名称（如计算器名称）
            context: 上下文信息
            
        Returns:
            None - 没有插件能提供进化规范
            str - 进化规范（给 LLM 的 prompt）
        """
        pm = self._get_plugin_manager()
        if not pm:
            return None
        
        # 遍历所有插件，查找实现 get_evolution_spec 的
        for plugin in pm.get_plugins():
            if hasattr(plugin, "get_evolution_spec"):
                try:
                    spec = plugin.get_evolution_spec(capability_type, name, context)
                    if spec:
                        return spec
                except Exception:
                    pass
        
        return None

    def _list_calculators(self, args: dict[str, Any]) -> dict[str, Any]:
        """List all available calculators"""
        if not self._get_plugin_manager():
            return {"success": False, "error": "Plugin manager not initialized"}

        calc_list = self._get_plugin_manager().hook.vi_list_calculators()
        if not calc_list:
            return {"success": True, "data": {"calculators": []}}

        # Flatten if nested
        if calc_list and isinstance(calc_list[0], list):
            calc_list = calc_list[0]

        return {"success": True, "data": {"calculators": calc_list}}

    def _register_calculator(self, args: dict[str, Any]) -> dict[str, Any]:
        """Register a calculator dynamically with sandbox validation"""
        if not self._get_plugin_manager():
            return {"success": False, "error": "Plugin manager not initialized"}

        name = args.get("name")
        code = args.get("code")
        required_fields = args.get("required_fields", [])

        # 1. 沙箱验证代码
        try:
            from acorn_core.sandbox import validate_calculator_code
            import pandas as pd

            # 构造测试数据
            test_data = {
                "data": {field: pd.Series([1.0, 2.0, 3.0]) for field in required_fields},
                "config": {}
            }

            validation = validate_calculator_code(code, test_data, {"pd": pd})

            if not validation["success"]:
                return {
                    "success": False,
                    "error": f"Sandbox validation failed: {validation['error']}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Validation error: {str(e)}"
            }

        # 2. 调用 hook 注册
        result = self._get_plugin_manager().hook.vi_register_calculator(
            name=name,
            code=code,
            required_fields=required_fields,
            description=args.get("description", ""),
            namespace=args.get("namespace", "dynamic"),
        )

        return result if result else {"success": True, "data": {"message": f"Calculator '{name}' registered"}}

    def _generate_calculator_extension_prompt(self, calculator_name: str) -> str:
        """
        生成 Calculator 扩展 Prompt

        读取 skill 文件内容，告诉 LLM Agent 如何创建新的 Calculator。
        """
        from pathlib import Path

        # 尝试读取 skill 文件
        skill_paths = [
            Path(".acorn/skills/calculator-creation/SKILL.md"),
            Path.home() / ".pi/agent/skills/calculator-creation/SKILL.md",
        ]

        skill_content = None
        for skill_path in skill_paths:
            if skill_path.exists():
                skill_content = skill_path.read_text(encoding="utf-8")
                break

        if skill_content:
            # 返回 skill 内容 + 具体请求
            return f"""## 扩展请求

calculator_name: {calculator_name}

## 创建规范

{skill_content}"""
        else:
            # 简单 fallback
            return f"""要创建计算器 '{calculator_name}'，请提供：

1. field_name: {calculator_name}
2. required_fields: 需要的输入字段列表
3. code: 计算器代码

代码格式：
```python
REQUIRED_FIELDS = ["field_a", "field_b"]

def calculate(data, config):
    return data["field_a"] / data["field_b"]
```"""

    def on_load(self) -> None:
        """Called when plugin is loaded (Genes lifecycle)"""
        # Plugin manager is set by Acorn kernel
        pass

    def on_unload(self) -> None:
        """Called when plugin is unloaded (Genes lifecycle)"""
        pass


# Plugin instance for pluggy registration
plugin = ViCorePlugin()  # type: ignore[assignment]
