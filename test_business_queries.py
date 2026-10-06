"""业务查询扩展：52个参数化实例，预期根据源码及独立SQL核验。"""

import math

import allure
import pytest

from test_extended import get_data


# 表名/条件都是固定测试配置，外部数据只通过SQL参数传入。
MODULES = [
    pytest.param("/order", "oms_order", "delete_status = 0", id="order"),
    pytest.param("/coupon", "sms_coupon", "1 = 1", id="coupon"),
    pytest.param("/returnReason", "oms_order_return_reason", "1 = 1", id="return-reason"),
]


def query_rows(db_connection, sql, params=()):
    with db_connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def check_page(data, total, page_num, page_size):
    assert isinstance(data, dict)
    assert data["total"] == total
    assert data["pageNum"] == page_num
    assert data["pageSize"] == page_size
    assert data["totalPage"] == math.ceil(total / page_size)
    expected_length = min(page_size, max(0, total - (page_num - 1) * page_size))
    assert len(data["list"]) == expected_length
    ids = [item["id"] for item in data["list"]]
    assert len(ids) == len(set(ids)), "分页返回重复记录"


@allure.feature("订单、优惠券与退货原因")
@pytest.mark.parametrize("path,table,condition", MODULES)
@pytest.mark.parametrize("page_size", [1, 5, 20])
def test_business_pagination(api_client, admin_token, db_connection, path, table, condition, page_size):
    rows = query_rows(db_connection, f"SELECT id FROM {table} WHERE {condition}")
    data = get_data(api_client, admin_token, f"{path}/list", {"pageNum": 1, "pageSize": page_size})
    check_page(data, len(rows), 1, page_size)
    valid_ids = {row["id"] for row in rows}
    assert all(item["id"] in valid_ids for item in data["list"])


@allure.feature("分页边界")
@pytest.mark.parametrize("path,table,condition", MODULES)
def test_business_page_after_last(api_client, admin_token, db_connection, path, table, condition):
    total = query_rows(db_connection, f"SELECT COUNT(*) AS total FROM {table} WHERE {condition}")[0]["total"]
    page = math.ceil(total / 5) + 1
    data = get_data(api_client, admin_token, f"{path}/list", {"pageNum": page, "pageSize": 5})
    check_page(data, total, page, 5)


@allure.feature("业务详情与数据一致性")
@pytest.mark.parametrize("path,table,condition", MODULES)
def test_business_detail_matches_database(api_client, admin_token, db_connection, path, table, condition):
    rows = query_rows(db_connection, f"SELECT * FROM {table} WHERE {condition} ORDER BY id LIMIT 1")
    assert rows, f"测试环境需要至少一条{table}数据"
    row = rows[0]
    data = get_data(api_client, admin_token, f"{path}/{row['id']}")
    assert isinstance(data, dict)
    assert data["id"] == row["id"]
    mappings = {
        "/order": {"orderSn": "order_sn", "status": "status", "memberId": "member_id"},
        "/coupon": {"name": "name", "type": "type", "useType": "use_type"},
        "/returnReason": {"name": "name", "status": "status", "sort": "sort"},
    }
    for api_field, db_field in mappings[path].items():
        assert data[api_field] == row[db_field], f"详情字段不一致：{api_field}"
    if path == "/order":
        items = query_rows(db_connection, "SELECT id FROM oms_order_item WHERE order_id = %s", (row["id"],))
        assert {item["id"] for item in data["orderItemList"]} == {item["id"] for item in items}
        assert len(data["orderItemList"]) == len(items)


@allure.feature("业务模块鉴权")
@pytest.mark.parametrize("path,params", [
    pytest.param("/order/list", {}, id="order"),
    pytest.param("/coupon/list", {}, id="coupon"),
    pytest.param("/returnReason/list", {}, id="return-reason"),
    pytest.param("/memberLevel/list", {"defaultStatus": 0}, id="member-level"),
    pytest.param("/productAttribute/list/3", {"type": 0}, id="product-attribute"),
])
@pytest.mark.parametrize("auth", [None, "Bearer invalid-token"], ids=["missing-token", "invalid-token"])
def test_business_queries_require_auth(api_client, path, params, auth):
    headers = {} if auth is None else {"Authorization": auth}
    response = api_client.request("GET", path, headers=headers, params=params)
    assert response.status_code == 200
    result = response.json()
    assert result.get("code") == 401
    assert result.get("message") == "暂未登录或token已经过期"
    assert not isinstance(result.get("data"), (dict, list))


@allure.feature("订单状态筛选")
@pytest.mark.parametrize("status", [0, 1, 2, 3, 4, 5], ids=["unpaid", "pending-delivery", "delivered", "completed", "closed", "invalid"])
def test_order_status_filter(api_client, admin_token, db_connection, status):
    total = query_rows(db_connection,
        "SELECT COUNT(*) AS total FROM oms_order WHERE delete_status = 0 AND status = %s", (status,))[0]["total"]
    data = get_data(api_client, admin_token, "/order/list", {"status": status, "pageSize": 5})
    check_page(data, total, 1, 5)
    assert all(item["status"] == status and item["deleteStatus"] == 0 for item in data["list"])


@allure.feature("优惠券类型筛选")
@pytest.mark.parametrize("coupon_type", [0, 1, 2, 3])
def test_coupon_type_filter(api_client, admin_token, db_connection, coupon_type):
    total = query_rows(db_connection, "SELECT COUNT(*) AS total FROM sms_coupon WHERE type = %s", (coupon_type,))[0]["total"]
    data = get_data(api_client, admin_token, "/coupon/list", {"type": coupon_type, "pageSize": 5})
    check_page(data, total, 1, 5)
    assert all(item["type"] == coupon_type for item in data["list"])


@allure.feature("会员等级查询")
@pytest.mark.parametrize("default_status", [0, 1])
def test_member_levels_match_database(api_client, admin_token, db_connection, default_status):
    rows = query_rows(db_connection,
        "SELECT id, name, default_status FROM ums_member_level WHERE default_status = %s", (default_status,))
    data = get_data(api_client, admin_token, "/memberLevel/list", {"defaultStatus": default_status})
    assert isinstance(data, list)
    by_id = {row["id"]: row for row in rows}
    assert {item["id"] for item in data} == set(by_id)
    assert len(data) == len(rows)
    for item in data:
        assert item["defaultStatus"] == default_status
        assert item["name"] == by_id[item["id"]]["name"]


@allure.feature("商品属性与参数")
@pytest.mark.parametrize("attribute_type", [0, 1], ids=["attribute", "parameter"])
def test_product_attributes_match_database(api_client, admin_token, db_connection, attribute_type):
    rows = query_rows(db_connection,
        "SELECT id, name, sort FROM pms_product_attribute WHERE product_attribute_category_id = %s AND type = %s",
        (3, attribute_type))
    data = get_data(api_client, admin_token, "/productAttribute/list/3", {"type": attribute_type, "pageSize": 100})
    assert len(rows) <= 100, "数据超出单页核验范围"
    check_page(data, len(rows), 1, 100)
    by_id = {row["id"]: row for row in rows}
    assert {item["id"] for item in data["list"]} == set(by_id)
    for item in data["list"]:
        assert item["productAttributeCategoryId"] == 3
        assert item["type"] == attribute_type
        assert item["name"] == by_id[item["id"]]["name"]
    sorts = [item["sort"] for item in data["list"]]
    assert sorts == sorted(sorts, reverse=True)


@allure.feature("不存在的资源查询")
@pytest.mark.parametrize("path,table,result_type", [
    pytest.param("/brand", "pms_brand", "null", id="brand"),
    pytest.param("/productCategory", "pms_product_category", "null", id="category"),
    pytest.param("/productAttribute/category", "pms_product_attribute_category", "null", id="attribute-category"),
    pytest.param("/productAttribute", "pms_product_attribute", "null", id="attribute"),
    pytest.param("/sku", "pms_product", "list", id="sku-product"),
    pytest.param("/productCategory/list", "pms_product_category", "page", id="child-list"),
])
def test_nonexistent_resource(api_client, admin_token, db_connection, path, table, result_type):
    absent_id = query_rows(db_connection, f"SELECT COALESCE(MAX(id), 0) + 1 AS absent_id FROM {table}")[0]["absent_id"]
    data = get_data(api_client, admin_token, f"{path}/{absent_id}")
    if result_type == "null":
        assert data is None
    elif result_type == "list":
        assert data == []
    else:
        check_page(data, 0, 1, 5)


@allure.feature("跨页查询")
@pytest.mark.parametrize("path,table,condition", MODULES)
def test_business_pages_do_not_overlap(api_client, admin_token, db_connection, path, table, condition):
    total = query_rows(db_connection, f"SELECT COUNT(*) AS total FROM {table} WHERE {condition}")[0]["total"]
    assert total >= 2, "跨页验证需要至少两条数据"
    first = get_data(api_client, admin_token, f"{path}/list", {"pageNum": 1, "pageSize": 1})
    second = get_data(api_client, admin_token, f"{path}/list", {"pageNum": 2, "pageSize": 1})
    check_page(first, total, 1, 1)
    check_page(second, total, 2, 1)
    assert first["list"][0]["id"] != second["list"][0]["id"]


@allure.feature("默认参数")
@pytest.mark.parametrize("path,table,condition", MODULES)
def test_business_default_pagination(api_client, admin_token, db_connection, path, table, condition):
    total = query_rows(db_connection, f"SELECT COUNT(*) AS total FROM {table} WHERE {condition}")[0]["total"]
    data = get_data(api_client, admin_token, f"{path}/list")
    check_page(data, total, 1, 5)


@allure.feature("SKU搜索无结果")
def test_sku_nonmatching_keyword(api_client, admin_token, db_connection):
    keyword = "接口测试_不存在的SKU_7a930f"
    rows = query_rows(db_connection,
        "SELECT COUNT(*) AS total FROM pms_sku_stock WHERE product_id = %s AND sku_code LIKE %s",
        (27, f"%{keyword}%"))
    assert rows[0]["total"] == 0, "搜索关键字已存在，请调整测试数据"
    assert get_data(api_client, admin_token, "/sku/27", {"keyword": keyword}) == []
