import time
import logging
import json

from django.http import HttpRequest
from asgiref.sync import iscoroutinefunction, markcoroutinefunction

logger = logging.getLogger(__name__)

class RequestTimerMiddleware:
    async_capable = True
    sync_capable = False

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    async def __call__(self, request: HttpRequest):
        # 记录开始时间
        start_time = time.time()

        # 获取 GET 参数
        query_params = dict(request.GET.items())

        # 处理请求
        response = await self.get_response(request)

        # 计算耗时
        duration = time.time() - start_time

        # 记录请求路径、参数和耗时
        logger.info(
            f"Path: {request.path} | "
            f"Query: {json.dumps(query_params, ensure_ascii=False)} | "
            f"Duration: {duration:.3f}s"
        )

        return response
