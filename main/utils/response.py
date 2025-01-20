from typing import Generic, TypeVar, Optional

from ninja import Schema, Field

T = TypeVar("T")


class StatusCode(object):

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

    def __str__(self):
        return self.code


class BaseResponse(Schema, Generic[T]):
    code: int = Field(..., description="状态码：0 表示成功；非 0 表示失败，具体错误信息参考message字段")
    data: Optional[T] = Field(None, description="数据")
    message: str = Field(..., description="错误信息")


class OkResponse(BaseResponse):
    code: int = Field(0, description="状态码：0 表示成功；非 0 表示失败，具体错误信息参考message字段")
    data: Optional[T] = Field(None, description="数据")
    message: str = Field("", description="错误信息")

    def __init__(self, data=None):
        super().__init__(code=0, data=data, message="ok")


class FailedResponse(BaseResponse):
    code: int = Field(1, description="状态码：0 表示成功；非 0 表示失败，具体错误信息参考message字段")
    data: Optional[T] = Field(None, description="数据")
    message: str = Field("", description="错误信息")

    def __init__(self, code: StatusCode, message: str = ""):
        message = message if message else code.message
        super().__init__(code=code.code, data=None, message=message)



BAD_REQUEST = StatusCode(1001, "请求参数错误")
RESOURCE_NOT_FOUND = StatusCode(1002, "资源不存在")
DUPLICATE_DATA = StatusCode(1003, "数据重复")
OBJECT_NOT_FOUND = StatusCode(1004, "对象不存在")
WRITE_DATA_FAILED = StatusCode(1005, "写入数据失败")
INVALID_DATA = StatusCode(1006, "无效数据")
NOT_FOUND = StatusCode(1007, "未找到")
LOGIN_FAILED = StatusCode(1008, "登录失败")
PASSWORD_ERROR = StatusCode(1009, "密码错误")
