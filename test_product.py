import requests
import pytest

def test_query_products(admin_token, api_client):
    response = api_client.request(
        "GET",
        "/product/list",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
        params={
            "pageNum": 1,
            "pageSize": 5,
        },
    )

    assert response.status_code == 200

    result = response.json()
    assert result.get("code") == 200, "商品查询失败"

    data = result.get("data") or {}
    products = data.get("list")

    assert isinstance(products, list), "商品列表类型不正确"
    assert 0 < len(products) <= 5, "当前测试数据下应返回 1～5 条商品"
    assert data.get("pageNum") == 1
    assert data.get("pageSize") == 5

@pytest.mark.parametrize(
    "filters, expected_name, expected_category_id",
    [
        pytest.param(
            {"keyword": "小米"},
            "小米",
            None,
            id="keyword",
        ),
        pytest.param(
            {"keyword": "小米", "productCategoryId": 19},
            "小米",
            19,
            id="keyword-and-category",
        ),
    ],
)
def test_filter_products(
    admin_token,
    api_client,
    filters,
    expected_name,
    expected_category_id,
):
    params = {
        "pageNum": 1,
        "pageSize": 5,
        **filters,
    }

    response = api_client.request(
        "GET",
        "/product/list",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
        params=params,
    )

    assert response.status_code == 200

    result = response.json()
    assert result.get("code") == 200

    data = result.get("data") or {}
    products = data.get("list")

    assert isinstance(products, list)
    assert 0 < len(products) <= 5, "当前测试数据下应查到商品"

    for product in products:
        name = product.get("name")
        assert isinstance(name, str), "商品名称应为字符串"
        assert expected_name in name, "商品名称不符合关键词"

        if expected_category_id is not None:
            assert product.get("productCategoryId") == expected_category_id

@pytest.mark.parametrize(
    "headers",
    [
        pytest.param(
            {},
            id="missing-token",
        ),
        pytest.param(
            {"Authorization": "Bearer invalid-token"},
            id="invalid-token",
        ),
    ],
)

def test_query_products_without_valid_token(api_client, headers):
    response = api_client.request(
        "GET",
        "/product/list",
        headers=headers,
        params={
            "pageNum": 1,
            "pageSize": 5,
        },
    )

    assert response.status_code == 200

    result = response.json()
    assert result.get("code") == 401, "无有效 Token 的请求应被拒绝"

    data = result.get("data")
    assert not isinstance(data, dict), "不应返回正常的商品分页数据"