"""Test Precheck Result Formatting"""
from vi_core.precheck import PrecheckResult, Issue, IssueSeverity


def test_format_success():
    """成功时格式化"""
    result = PrecheckResult(
        available=["revenue", "net_profit"],
        issues=[],
        symbol="600519"
    )

    lines = result.format()

    assert len(lines) > 0
    text = "\n".join(lines)
    assert "600519" in text
    assert "revenue" in text
    assert "net_profit" in text


def test_format_with_issues():
    """有问题时格式化"""
    result = PrecheckResult(
        available=["revenue"],
        issues=[
            Issue(
                item="implied_growth",
                severity=IssueSeverity.ERROR,
                reason="缺少依赖字段: operating_cash_flow",
                missing_fields=["operating_cash_flow"],
                suggestion="切换到 A 股市场"
            )
        ],
        symbol="00700"
    )

    lines = result.format()
    text = "\n".join(lines)

    assert "implied_growth" in text
    assert "operating_cash_flow" in text
    assert "00700" in text


def test_format_table():
    """表格格式输出"""
    result = PrecheckResult(
        available=["revenue", "net_profit"],
        issues=[
            Issue("unknown", IssueSeverity.ERROR, "未知数据项")
        ],
        symbol="600519"
    )

    table = result.format_table()

    assert "revenue" in table
    assert "unknown" in table


def test_precheck_result_str():
    """__str__ 方法应该可用"""
    result = PrecheckResult(
        available=["revenue"],
        issues=[
            Issue("implied_growth", IssueSeverity.ERROR, "缺少字段")
        ],
        symbol="600519"
    )

    text = str(result)
    assert "revenue" in text
    assert "implied_growth" in text


def test_precheck_with_multiple_issues():
    """多个问题时格式化"""
    result = PrecheckResult(
        available=["revenue"],
        issues=[
            Issue("field1", IssueSeverity.ERROR, "原因1"),
            Issue("field2", IssueSeverity.WARNING, "原因2"),
            Issue("field3", IssueSeverity.INFO, "原因3"),
        ],
        symbol="600519"
    )

    lines = result.format()
    assert len(lines) > 5  # 多个问题应该有多行


def test_precheck_result_equality():
    """PrecheckResult 应该可以比较"""
    result1 = PrecheckResult(
        available=["revenue"],
        issues=[],
        symbol="600519"
    )
    result2 = PrecheckResult(
        available=["revenue"],
        issues=[],
        symbol="600519"
    )

    assert result1.available == result2.available
    assert result1.symbol == result2.symbol
