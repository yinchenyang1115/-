import requests
import pytest
from uuid import uuid4
import allure


def test_query_top_categories(admin_token, api_client):
    response = api_client.request(
        "GET",
        "/productCategory/list/0",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
        params={
            "pageNum": 1,
            "pageSize": 20,
        },
    )

    assert response.status_code == 200

    result = response.json()
    assert result.get("code") == 200, "分类查询失败"

    data = result.get("data") or {}
    categories = data.get("list")

    assert isinstance(categories, list), "分类列表类型不正确"
    assert 0 < len(categories) <= 20, "当前测试数据下应返回分类"
    assert data.get("pageNum") == 1
    assert data.get("pageSize") == 20

    for category in categories:
        assert category.get("parentId") == 0, (
            f"分类 {category.get('id')} 不属于顶级分类"
        )

@pytest.mark.parametrize(
    "changed_fields, expected_message",
    [
        pytest.param(
            {"sort": -1},
            "sort最小不能小于0",
            id="negative-sort",
        ),
        pytest.param(
            {"showStatus": 2},
            "showStatus状态只能为0或1",
            id="invalid-show-status",
        ),
        pytest.param(
            {"name": ""},
            "name不能为空",
            id="empty-name",
        ),
    ],
)

def test_create_category_invalid(
    admin_token, api_client, changed_fields, expected_message
):
    payload = {
        "parentId": 0,
        "name": "接口自动化_异常分类",
        "productUnit": "件",
        "navStatus": 0,
        "showStatus": 0,
        "sort": 0,
        "icon": "",
        "keywords": "接口测试",
        "description": "异常参数校验",
        "productAttributeIdList": [],
    }

    payload.update(changed_fields)

    response = api_client.request(
        "POST",
        "/productCategory/create",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
        json=payload,
    )

    assert response.status_code == 200

    result = response.json()
    assert result.get("code") == 404, "非法参数应被拒绝"
    assert result.get("message") == expected_message
    assert result.get("data") is None

@pytest.fixture
def test_category(admin_token, api_client, db_connection):
    name = f"接口自动化分类_{uuid4().hex}"
    headers = {
        "Authorization": f"Bearer {admin_token}",
    }
    category_id = None

    # 按唯一名称查找我们创建的分类，逐页查询
    def find_category():
        page = 1

        while True:
            response = api_client.request(
                "GET",
                "/productCategory/list/0",
                headers=headers,
                params={"pageNum": page, "pageSize": 100},
            )

            assert response.status_code == 200

            result = response.json()
            assert result.get("code") == 200

            data = result["data"]

            for category in data["list"]:
                if category["name"] == name:
                    return category

            if page >= data["totalPage"]:
                return None

            page += 1

    try:
        response = api_client.request(
            "POST",
            "/productCategory/create",
            headers=headers,
            json={
                "parentId": 0,
                "name": name,
                "productUnit": "件",
                "navStatus": 0,
                "showStatus": 0,
                "sort": 0,
                "icon": "",
                "keywords": "接口测试",
                "description": "自动化专用，结束后清理",
                "productAttributeIdList": [],
            },
        )

        assert response.status_code == 200

        result = response.json()
        assert result.get("code") == 200, "创建测试分类失败"
        assert result.get("data") == 1

        category = find_category()
        assert category is not None, "创建后未找到测试分类"

        category_id = category["id"]

        # 将分类 ID 和名称提供给测试函数
        yield {"id": category_id, "name": name}

    finally:
        # 如果准备过程中失败，尝试查找可能已经创建的记录
        if category_id is None:
            category = find_category()
            if category is not None:
                category_id = category["id"]

        if category_id is not None:
            response = api_client.request(
                "POST",
                f"/productCategory/delete/{category_id}",
                headers=headers,
            )

            assert response.status_code == 200

            result = response.json()
            assert result.get("code") == 200, "清理测试分类失败"
            assert result.get("data") == 1

            response = api_client.request(
                "GET",
                f"/productCategory/{category_id}",
                headers=headers,
            )

            assert response.status_code == 200

            result = response.json()
            assert result.get("code") == 200
            assert result.get("data") is None, "清理后仍能查到测试分类"

            with allure.step("核验删除后数据库没有残留分类"):
                with db_connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM pms_product_category WHERE id = %s",
                        (category_id,),
                    )
                    remaining_category = cursor.fetchone()

                assert remaining_category is None, (
                    f"删除后数据库仍存在分类：{category_id}"
                )

@allure.feature("分类管理")
@allure.story("分类增删改查闭环")
@allure.title("创建分类后可查询和修改，结束后自动清理")
def test_created_category_can_be_queried(
    admin_token, api_client, test_category, db_connection
):
    category_id = test_category["id"]
    headers = {
        "Authorization": f"Bearer {admin_token}",
    }

    # 1. 查询并确认创建的数据
    response = api_client.request(
        "GET",
        f"/productCategory/{category_id}",
        headers=headers,
    )

    assert response.status_code == 200

    result = response.json()
    assert result.get("code") == 200

    category = result.get("data")
    assert isinstance(category, dict)
    assert category["id"] == category_id
    assert category["name"] == test_category["name"]
    assert category["parentId"] == 0

    # 2. 修改名称、排序和描述
    new_name = f"{test_category['name']}_已修改"

    response = api_client.request(
        "POST",
        f"/productCategory/update/{category_id}",
        headers=headers,
        json={
            "parentId": 0,
            "name": new_name,
            "productUnit": "件",
            "navStatus": 0,
            "showStatus": 0,
            "sort": 2,
            "icon": "",
            "keywords": "接口测试",
            "description": "自动化修改验证",
            "productAttributeIdList": [],
        },
    )

    assert response.status_code == 200

    result = response.json()
    assert result.get("code") == 200, "修改分类失败"
    assert result.get("data") == 1

    # 3. 再次查询，确认修改实际生效
    response = api_client.request(
        "GET",
        f"/productCategory/{category_id}",
        headers=headers,
    )

    assert response.status_code == 200

    result = response.json()
    assert result.get("code") == 200

    with allure.step("核验修改后的分类字段"):
        category = result.get("data")
        assert isinstance(category, dict), "没有返回分类对象"

        # 只附加本次测试需要的字段
        allure.attach(
            (
                f"分类 ID：{category.get('id')}\n"
                f"分类名称：{category.get('name')}\n"
                f"排序值：{category.get('sort')}\n"
                f"描述：{category.get('description')}"
            ),
            name="修改后的分类数据",
            attachment_type=allure.attachment_type.TEXT,
        )

        assert category["id"] == category_id
        assert category["name"] == new_name
        assert category["sort"] == 2
        assert category["description"] == "自动化修改验证"

    with allure.step("核验修改结果已写入数据库"):
        with db_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, sort, description
                FROM pms_product_category
                WHERE id = %s
                """,
                (category_id,),
            )
            db_category = cursor.fetchone()

        assert db_category is not None, "数据库未找到测试分类"
        assert db_category["id"] == category_id
        assert db_category["name"] == new_name
        assert db_category["sort"] == 2
        assert db_category["description"] == "自动化修改验证"

def test_category_matches_database(
    admin_token, api_client, db_connection
):
    category_id = 19

    # 查询接口
    response = api_client.request(
        "GET",
        f"/productCategory/{category_id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
    )

    assert response.status_code == 200

    result = response.json()
    assert result.get("code") == 200

    api_category = result.get("data")
    assert isinstance(api_category, dict), "接口未返回分类对象"

    # 查询数据库中的同一条记录
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name, parent_id, level, show_status, sort
            FROM pms_product_category
            WHERE id = %s
            """,
            (category_id,),
        )
        db_category = cursor.fetchone()

    assert db_category is not None, "数据库未找到指定分类"

    # 左边是接口字段，右边是数据库字段
    field_mapping = {
        "id": "id",
        "name": "name",
        "parentId": "parent_id",
        "level": "level",
        "showStatus": "show_status",
        "sort": "sort",
    }

    for api_field, db_field in field_mapping.items():
        assert api_field in api_category, f"接口缺少字段：{api_field}"
        assert api_category[api_field] == db_category[db_field], (
            f"字段不一致：接口 {api_field}={api_category[api_field]!r}，"
            f"数据库 {db_field}={db_category[db_field]!r}"
        )
