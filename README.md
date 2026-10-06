# mall 接口自动化测试

基于本地部署的 mall，使用 Python、pytest、Requests、YAML、Allure、logging 和 MySQL。
覆盖登录异常、商品查询与鉴权、分类参数校验及分类增删改查。
分类闭环核验数据库修改结果，并在清理后确认无残留数据。

GitHub Actions 配置使用 Windows 本机执行器，标签为 mall-local。
运行环境及安装步骤见 GITHUB-ACTIONS-SETUP.md。流水线目前待首次云端验证。
数据库密码通过环境变量 MALL_DB_PASSWORD 提供。
测试中的 admin/macro123 是本地教学演示账号，不用于生产环境。
