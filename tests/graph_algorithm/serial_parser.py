"""
序号编码解析器

解析形如 "1", "1-1", "1-1-1" 的序号编码，支持层级比较和优先级排序。
"""


def parse_serial(serial: str) -> dict:
    """
    解析序号字符串为结构化数据。

    Args:
        serial: 序号字符串，如 "1", "1-1", "1-1-1"

    Returns:
        dict: 包含以下键的字典:
            - path: 路径列表 [1, 1, 1]
            - level: 层级深度 (3)
            - segments: 段数 (3)

    Examples:
        >>> parse_serial("1")
        {'path': [1], 'level': 1, 'segments': 1}
        >>> parse_serial("1-1")
        {'path': [1, 1], 'level': 2, 'segments': 2}
        >>> parse_serial("1-1-1")
        {'path': [1, 1, 1], 'level': 3, 'segments': 3}
    """
    if not serial:
        raise ValueError("Serial cannot be empty")

    # 分割序号并转换为整数
    segments = serial.split('-')
    path = [int(seg) for seg in segments]

    return {
        'path': path,
        'level': len(path),
        'segments': len(path)
    }


def compare_serial(s1: str, s2: str) -> int:
    """
    比较两个序号的优先级。

    规则：
    1. 位数少的序号优先（层级更高）
    2. 同位数按路径数值顺序比较（字典序）

    Args:
        s1: 第一个序号
        s2: 第二个序号

    Returns:
        int: -1 (s1 < s2), 0 (s1 == s2), 1 (s1 > s2)

    Examples:
        >>> compare_serial("1", "1-1")  # 位数少优先
        -1
        >>> compare_serial("1-1", "2-1")  # 同位数，路径比较
        -1
        >>> compare_serial("1-2", "1-1")  # 同位数，路径比较
        1
        >>> compare_serial("1-1", "1-1")  # 相同
        0
    """
    p1 = parse_serial(s1)
    p2 = parse_serial(s2)

    # 规则1: 位数少的优先
    if p1['segments'] < p2['segments']:
        return -1
    if p1['segments'] > p2['segments']:
        return 1

    # 规则2: 同位数按路径数值顺序比较
    for v1, v2 in zip(p1['path'], p2['path']):
        if v1 < v2:
            return -1
        if v1 > v2:
            return 1

    return 0


def get_generation_priority(serial: str, degree: int) -> tuple:
    """
    获取拓扑排序的优先级键。

    用于 Kahn's 算法中的同层节点排序：
    - degree: 入度（度数低的优先，Kahn's 中天然处理）
    - serial_path: 路径元组（序号小的优先，用户描述顺序）

    Args:
        serial: 序号字符串
        degree: 入度数值

    Returns:
        tuple: (degree, serial_path) 排序键

    Examples:
        >>> # 同度数时序号小优先
        >>> get_generation_priority("1-1", 0) < get_generation_priority("2-1", 0)
        True
        >>> # 度数低的优先
        >>> get_generation_priority("1-1", 0) < get_generation_priority("1-1", 1)
        True
    """
    parsed = parse_serial(serial)
    return (degree, tuple(parsed['path']))
