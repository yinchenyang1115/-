import pytest
import allure

from yaml_loader import load_yaml_cases


login_invalid_cases = load_yaml_cases("data/login_invalid.yaml")


@allure.feature("登录管理")
@allure.story("正常登录")
@allure.title("正确账号和密码能够登录成功")
def test_login_success(api_client):
    with allure.step("发送正常登录请求"):
        response = api_client.request(
            "POST",
            "/admin/login",
            json={
                "username": "admin",
                "password": "macro123",
            },
        )

    with allure.step("检查 HTTP 状态码为 200"):
        assert response.status_code == 200, "HTTP 状态码不符合预期"

    with allure.step("检查登录业务码为 200"):
        result = response.json()
        assert result.get("code") == 200, "登录业务码不符合预期"

    with allure.step("检查返回非空 Token"):
        data = result.get("data") or {}
        assert data.get("token"), "登录成功后没有返回非空 Token"


login_cases_by_id = {
    case["id"]: case
    for case in login_invalid_cases
}


@pytest.mark.parametrize("case_id", list(login_cases_by_id))
def test_login_invalid_inputs(api_client, case_id):
    allure.dynamic.title(f"异常登录：{case_id}")
    case = login_cases_by_id[case_id]

    response = api_client.request(
        "POST",
        "/admin/login",
        json=case["request"],
    )

    assert response.status_code == 200, "HTTP 状态码不符合预期"

    result = response.json()
    expected = case["expected"]

    assert result.get("code") == expected["code"], "业务码不符合预期"
    assert result.get("message") == expected["message"], "提示信息不符合预期"
    assert result.get("data") is None, "异常登录不应返回登录数据"
