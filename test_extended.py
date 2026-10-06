"""扩展品牌、SKU、分类层级及分页/筛选/鉴权覆盖；不修改业务数据。"""

import math

import allure
import pytest


def get_data(api_client, admin_token, path, params=None):
    response = api_client.request(
        "GET", path, headers={"Authorization": f"Bearer {admin_token}"},
        params=params,
    )
    assert response.status_code == 200
    result = response.json()
    assert result.get("code") == 200, f"查询失败：{path}"
    assert "data" in result
    return result["data"]


PAGE_PATHS = ["/product/list", "/brand/list", "/productAttribute/category/list"]


@allure.feature("分页与边界")
@pytest.mark.parametrize("path", PAGE_PATHS)
@pytest.mark.parametrize("page_size", [1, 5, 20])
def test_page_size_and_metadata(api_client, admin_token, path, page_size):
    data = get_data(api_client, admin_token, path, {"pageNum": 1, "pageSize": page_size})
    assert isinstance(data, dict)
    assert data["pageNum"] == 1
    assert data["pageSize"] == page_size
    assert type(data["total"]) is int and data["total"] >= 0
    assert isinstance(data["list"], list)
    assert len(data["list"]) == min(page_size, data["total"])
    assert data["totalPage"] == math.ceil(data["total"] / page_size)
    ids = [item["id"] for item in data["list"]]
    assert len(ids) == len(set(ids)), "同一页出现重复记录"


@allure.feature("分页与边界")
@pytest.mark.parametrize("path", PAGE_PATHS)
def test_page_after_last_is_empty(api_client, admin_token, path):
    first = get_data(api_client, admin_token, path, {"pageNum": 1, "pageSize": 5})
    page = first["totalPage"] + 1
    data = get_data(api_client, admin_token, path, {"pageNum": page, "pageSize": 5})
    assert data["pageNum"] == page
    assert data["list"] == []
    assert data["total"] == first["total"]


@allure.feature("接口鉴权")
@pytest.mark.parametrize("path", [
    "/brand/list", "/sku/27", "/productCategory/list/0",
    "/productAttribute/category/list",
])
@pytest.mark.parametrize("auth", [None, "Bearer invalid-token"], ids=["missing-token", "invalid-token"])
def test_other_modules_require_auth(api_client, path, auth):
    headers = {} if auth is None else {"Authorization": auth}
    response = api_client.request("GET", path, headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result.get("code") == 401
    assert result.get("message") == "暂未登录或token已经过期"
    assert not isinstance(result.get("data"), (dict, list)), "拒绝请求仍返回业务数据"


@allure.feature("品牌管理")
def test_brand_list_detail_database_agree(api_client, admin_token, db_connection):
    brands = get_data(api_client, admin_token, "/brand/listAll")
    assert isinstance(brands, list) and brands, "测试环境需要至少一个品牌"
    brand = brands[0]
    detail = get_data(api_client, admin_token, f"/brand/{brand['id']}")
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT id, name, show_status FROM pms_brand WHERE id = %s", (brand["id"],))
        row = cursor.fetchone()
    assert row is not None
    assert detail["id"] == brand["id"] == row["id"]
    assert detail["name"] == brand["name"] == row["name"]
    assert detail["showStatus"] == row["show_status"]


@allure.feature("品牌管理")
@pytest.mark.parametrize("show_status", [0, 1])
def test_brand_show_status_filter(api_client, admin_token, db_connection, show_status):
    data = get_data(api_client, admin_token, "/brand/list", {"showStatus": show_status, "pageSize": 5})
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM pms_brand WHERE show_status = %s", (show_status,))
        row = cursor.fetchone()
    assert data["total"] == row["total"]
    assert len(data["list"]) == min(5, row["total"])
    assert all(item["showStatus"] == show_status for item in data["list"])


@allure.feature("品牌管理")
def test_brand_keyword_filter(api_client, admin_token):
    brands = get_data(api_client, admin_token, "/brand/listAll")
    assert brands
    keyword = brands[0]["name"]
    data = get_data(api_client, admin_token, "/brand/list", {"keyword": keyword, "pageSize": 20})
    assert data["list"]
    assert all(keyword in item["name"] for item in data["list"])


@allure.feature("SKU 库存查询")
def test_sku_matches_database(api_client, admin_token, db_connection):
    skus = get_data(api_client, admin_token, "/sku/27")
    assert isinstance(skus, list) and skus, "种子商品27需要有SKU"
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT id, product_id, sku_code, stock FROM pms_sku_stock WHERE product_id = %s", (27,))
        rows = cursor.fetchall()
    by_id = {row["id"]: row for row in rows}
    assert {sku["id"] for sku in skus} == set(by_id)
    assert len(skus) == len(by_id)
    for sku in skus:
        row = by_id[sku["id"]]
        assert sku["productId"] == row["product_id"] == 27
        assert sku["skuCode"] == row["sku_code"]
        assert sku["stock"] == row["stock"]


@allure.feature("SKU 库存查询")
def test_sku_keyword_filter(api_client, admin_token):
    skus = get_data(api_client, admin_token, "/sku/27")
    assert skus
    keyword = skus[0]["skuCode"]
    filtered = get_data(api_client, admin_token, "/sku/27", {"keyword": keyword})
    assert filtered
    assert all(item["productId"] == 27 and keyword in item["skuCode"] for item in filtered)


@allure.feature("分类层级")
def test_child_categories_match_database(api_client, admin_token, db_connection):
    data = get_data(api_client, admin_token, "/productCategory/list/2", {"pageSize": 100})
    assert data["total"] <= 100, "测试环境子分类数量超出单页核验范围"
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT id, parent_id, level FROM pms_product_category WHERE parent_id = %s", (2,))
        rows = cursor.fetchall()
    assert rows, "种子父分类2需要有子分类"
    assert {item["id"] for item in data["list"]} == {row["id"] for row in rows}
    assert data["total"] == len(rows)
    assert all(item["parentId"] == 2 and item["level"] == 1 for item in data["list"])


@allure.feature("分类层级")
def test_category_tree_relationships(api_client, admin_token, db_connection):
    roots = get_data(api_client, admin_token, "/productCategory/list/withChildren")
    assert isinstance(roots, list) and roots
    root_ids = [root["id"] for root in roots]
    assert len(root_ids) == len(set(root_ids))
    assert any(root["children"] for root in roots), "测试数据需包含至少一个子分类"
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT id, name, parent_id, level FROM pms_product_category")
        rows = cursor.fetchall()
    by_id = {row["id"]: row for row in rows}
    assert set(root_ids) == {row["id"] for row in rows if row["parent_id"] == 0}
    for root in roots:
        assert root["name"] == by_id[root["id"]]["name"]
        assert isinstance(root["children"], list)
        child_ids = [child["id"] for child in root["children"]]
        assert len(child_ids) == len(set(child_ids))
        assert set(child_ids) == {row["id"] for row in rows if row["parent_id"] == root["id"]}
        for child in root["children"]:
            assert child["name"] == by_id[child["id"]]["name"]
            assert by_id[child["id"]]["parent_id"] == root["id"]


@allure.feature("商品筛选")
@pytest.mark.parametrize("field,value", [
    ("publishStatus", 0), ("publishStatus", 1),
    ("verifyStatus", 0), ("verifyStatus", 1),
])
def test_product_status_filter(api_client, admin_token, db_connection, field, value):
    db_field = {"publishStatus": "publish_status", "verifyStatus": "verify_status"}[field]
    data = get_data(api_client, admin_token, "/product/list", {field: value, "pageSize": 5})
    with db_connection.cursor() as cursor:
        # 列名来自上面的固定映射；输入值仍使用SQL参数。
        cursor.execute(f"SELECT COUNT(*) AS total FROM pms_product WHERE delete_status = 0 AND {db_field} = %s", (value,))
        row = cursor.fetchone()
    assert data["total"] == row["total"]
    assert len(data["list"]) == min(5, row["total"])
    assert all(item[field] == value for item in data["list"])
