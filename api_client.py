# 引入 Python 自带的日志模块
import logging

# 引入路径工具，用于确定日志保存位置
from pathlib import Path

# 引入计时工具，用于测量请求耗时
from time import perf_counter

# 引入 Requests，用于发送 HTTP 请求
import requests


# __file__ 是当前文件路径；resolve() 转为绝对路径；
# parent 取得所在目录，即项目根目录
project_root = Path(__file__).resolve().parent

# 拼接日志目录：项目根目录/.runtime/logs，保存在 F 盘
log_dir = project_root / ".runtime" / "logs"

# 创建目录；parents=True 同时创建缺少的上级目录；
# exist_ok=True 表示目录已存在时不报错
log_dir.mkdir(parents=True, exist_ok=True)


# 获取名为 mall_api 的日志记录器
logger = logging.getLogger("mall_api")

# 设置最低记录级别为 INFO，ERROR 等更严重级别也会记录
logger.setLevel(logging.INFO)

# 不向上级记录器传递日志，避免额外的重复输出
logger.propagate = False

# 如果当前记录器没有处理器，才添加文件处理器
if not logger.handlers:
    # 创建文件处理器：默认追加写入，并使用 UTF-8 编码
    handler = logging.FileHandler(
        log_dir / "api-tests.log",
        encoding="utf-8",
    )

    # 设置日志格式：时间 | 级别 | 内容
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
    )

    # 将文件处理器绑定到记录器
    logger.addHandler(handler)


# 定义接口请求客户端类
class ApiClient:
    # 创建对象时接收基础地址
    def __init__(self, base_url):
        # 保存基础地址，并去掉末尾的斜杠
        self.base_url = base_url.rstrip("/")

    # 接收请求方法、接口路径，以及其他命名参数
    def request(self, method, path, **kwargs):
        # 没有指定 timeout 时使用 10；指定了就保留原值
        kwargs.setdefault("timeout", 10)

        # 拼接完整地址，去掉接口路径开头多余的斜杠
        url = f"{self.base_url}/{path.lstrip('/')}"

        # 将 get、post 等转换为 GET、POST
        method = method.upper()

        # 去掉路径中的查询字符串，日志只记录接口路径
        log_path = path.split("?", 1)[0]

        # 记录开始计时的值
        start = perf_counter()

        # 记录请求方法和路径，不记录请求体或认证头
        logger.info("请求开始 | %s %s", method, log_path)

        # 尝试发送请求
        try:
            # 根据 method 发送请求，并取得响应对象
            response = requests.request(
                # 传入 GET、POST 等请求方法
                method=method,
                # 传入拼接后的完整 URL
                url=url,
                # 展开 headers、params、json、timeout 等参数
                **kwargs,
            )

        # 捕获 Requests 的连接失败、超时等异常
        except requests.RequestException as exc:
            # 计算请求失败前的耗时，秒转换成毫秒
            elapsed_ms = (perf_counter() - start) * 1000

            # 写入 ERROR 日志，不打印可能包含敏感信息的完整异常内容
            logger.error(
                "请求异常 | %s %s | 类型=%s | 耗时=%.1fms",
                # 填入第一个 %s：请求方法
                method,
                # 填入第二个 %s：接口路径
                log_path,
                # 填入第三个 %s：异常类型，例如 ConnectionError
                type(exc).__name__,
                # 填入 %.1f：耗时，保留一位小数
                elapsed_ms,
            )

            # 重新抛出原异常，让 pytest 看到失败
            raise

        # 请求成功收到响应后，计算耗时
        elapsed_ms = (perf_counter() - start) * 1000

        # 默认业务码为 -，表示没有读取到整数业务码
        business_code = "-"

        # 尝试解析 JSON 响应
        try:
            # 将 JSON 内容转换为 Python 数据
            body = response.json()

        # 响应不是合法 JSON 时，避免日志处理阻断响应返回
        except ValueError:
            # 使用 None 表示没有解析到 JSON 数据
            body = None

        # 只有 JSON 最外层是对象、解析为字典时，才读取 code
        if isinstance(body, dict):
            # 取出 code；字段不存在时返回 None
            code = body.get("code")

            # 只接受整数业务码，不把任意响应内容写入日志
            if type(code) is int:
                # 保存实际业务码，例如 200、401、404、500
                business_code = code

        # 记录请求完成信息，不记录完整响应体
        logger.info(
            "请求完成 | %s %s | HTTP=%s | 业务码=%s | 耗时=%.1fms",
            # 请求方法
            method,
            # 接口路径
            log_path,
            # HTTP 状态码
            response.status_code,
            # 响应体中的业务码
            business_code,
            # 请求耗时，单位毫秒
            elapsed_ms,
        )

        # 将原响应返回给测试函数，由测试继续执行断言
        return response