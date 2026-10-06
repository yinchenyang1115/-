from pathlib import Path

import yaml
import json

def load_yaml_cases(relative_path):
    project_root = Path(__file__).resolve().parent
    file_path = project_root / relative_path

    with file_path.open("r", encoding="utf-8") as file:
        cases = yaml.safe_load(file)

    if not isinstance(cases, list) or not cases:
        raise ValueError("用例文件必须是非空列表")

    seen_ids = set()
    seen_requests = {}

    for index, case in enumerate(cases, start=1):
        location = f"{file_path.name} 第 {index} 条用例"

        if not isinstance(case, dict):
            raise ValueError(f"{location}：必须是字典")

        for field in ("id", "request", "expected"):
            if field not in case:
                raise ValueError(f"{location}：缺少字段 {field}")

        case_id = case["id"]

        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"{location}：id 必须是非空字符串")

        if case_id in seen_ids:
            raise ValueError(f"{location}：id 重复：{case_id}")

        seen_ids.add(case_id)

        if not isinstance(case["request"], dict):
            raise ValueError(f"{location}：request 必须是字典")
        
        # 对请求内容排序并转换为字符串，作为比较依据
        request_key = json.dumps(
            case["request"],
            sort_keys=True,
            ensure_ascii=False,
        )

        if request_key in seen_requests:
            previous_id = seen_requests[request_key]
            raise ValueError(
                f"{location}：请求内容重复，"
                f"与用例 {previous_id} 相同"
            )

        seen_requests[request_key] = case_id

        expected = case["expected"]

        if not isinstance(expected, dict):
            raise ValueError(f"{location}：expected 必须是字典")

        for field in ("code", "message"):
            if field not in expected:
                raise ValueError(
                    f"{location}：expected 缺少字段 {field}"
                )

        if type(expected["code"]) is not int:
            raise ValueError(f"{location}：expected.code 必须是整数")

        if not isinstance(expected["message"], str):
            raise ValueError(
                f"{location}：expected.message 必须是字符串"
            )

    return cases