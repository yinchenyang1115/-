import pytest
import requests
from api_client import ApiClient
import os
import pymysql

@pytest.fixture
def api_client(base_url):
    return ApiClient(base_url)

@pytest.fixture
def base_url():
    return "http://127.0.0.1:8080"

@pytest.fixture
def admin_token(api_client):
    response = api_client.request(
        "POST",
        "/admin/login",
        json={
            "username": "admin",
            "password": "macro123",
        },
    )

    assert response.status_code == 200, "准备 Token 时 HTTP 状态异常"

    result = response.json()
    assert result.get("code") == 200, "准备 Token 时登录失败"

    data = result.get("data") or {}
    token = data.get("token")
    assert token, "准备 Token 时没有获取到非空 Token"

    print("准备完成：已获取 Token")

    yield token

    print("收尾阶段：依赖这个 fixture 的测试已结束")

@pytest.fixture
def db_connection():
    connection = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="mall",
        password=os.environ["MALL_DB_PASSWORD"],
        database="mall",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
        autocommit=True,
    )

    try:
        yield connection
    finally:
        connection.close()