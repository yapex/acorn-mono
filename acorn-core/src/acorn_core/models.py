"""
任务上下文 (Task Context)
"""


class TaskContext:
    """
    任务执行上下文

    Attributes:
        task: 原始任务描述
        capabilities: 发现的可用能力列表
        results: 任务执行结果
        state: 自由状态字典
    """

    def __init__(self, task: str):
        self.task = task
        self.capabilities: list[dict] = []
        self.results: list = []
        self.state: dict = {}

    def add_capability(self, capability: dict):
        """添加一个能力"""
        if capability:
            self.capabilities.append(capability)

    def add_result(self, result):
        """添加一个执行结果"""
        self.results.append(result)

    def __repr__(self):
        cap = len(self.capabilities)
        res = len(self.results)
        return f"TaskContext(task={self.task!r}, caps={cap}, res={res})"
