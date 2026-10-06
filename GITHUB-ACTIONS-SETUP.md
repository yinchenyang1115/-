# GitHub Actions 本机接口测试

当前状态：流水线和执行脚本已准备，尚未注册执行器或完成 GitHub 云端运行。

## 仓库与执行器

创建私有仓库 mall-api-tests，默认分支 main。执行器安装在
F:\softwaretesting\mall-loaal\.runtime\github-runner，工作目录配置为该目录下的 _work。
注册时添加自定义标签 mall-local；Windows 和 X64 是默认标签。
执行器启动前设置 TEMP、TMP、HOME、USERPROFILE 和缓存目录到 F 盘专用目录。
在仓库 Settings → Actions → Runners 中使用 GitHub 提供的当前下载及注册命令。
注册 token 不提交到仓库，也不要粘贴到聊天中。

在 Settings → Secrets and variables → Actions 添加 MALL_DB_PASSWORD，值为本机 mall 数据库账号密码。
mall 服务、MySQL 和 Redis 需提前启动；执行器运行在这台电脑上才能访问 127.0.0.1。
现阶段流水线复用 F 盘现有虚拟环境及 Allure，是本机专用配置。

## 提交范围

仅提交测试框架文件：.github/workflows/api-tests.yml、Run-CI.ps1、api_client.py、
conftest.py、yaml_loader.py、test_login.py、test_product.py、test_category.py、
data/login_invalid.yaml 和本说明文档。
不要整体上传部署项目目录；mall-local.yml、初始化及部署脚本可能包含本地密码。
不上传 .runtime、.venv、日志、报告、数据库文件、API Key 或 runner 注册文件。
GitHub 页面显示工作流后，先手动运行验证，再验证 push 到 main 自动触发。

## 结果

测试失败时仍尝试生成 Allure 报告，并归档 Allure 结果、HTML 报告、JUnit XML 和请求日志。
在 Actions 的运行详情中下载 mall-api-results-*。输出归档保留 14 天。
工作流只运行明确列出的正式测试，不调用 DeepSeek，不执行未审核候选文件。
