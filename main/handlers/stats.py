import logging
from typing import List, Optional, Union
from datetime import datetime, timedelta

from pydantic import (
    BaseModel,
    Field,
    computed_field,
    field_validator,
)
from ninja.errors import HttpError
from django.http import HttpRequest
from functools import cached_property

from main.utils.response import (
    OkResponse,
    FailedResponse,
)
from main import models, results
from main.utils.mongo import mongo_client

logger = logging.getLogger(__name__)


# {
#     "input1": "how much energy did i use for charging in December 12, 2024",
#     "input2": [
#       {
#         "role": "user",
#         "content": "how much energy did i use for charging in december 12, 2024"
#       }
#     ],
#     "output1": "View_history_charging_energy",
#     "output2": {
#       "text": "how much energy did i use for charging in december 12, 2024",
#       "intent": "用户历史充电电量",
#       "slots": {
#         "起止日期": {
#           "起始日期": "2024-12-12",
#           "结束日期": "2024-12-12"
#         }
#       },
#       "model_version": "llama0.3.1"
#     },
#     "detect_time_cost": 0.930589,
#     "total_time_cost": 1.055931,
#     "client_type": "app",
#     "language": "english",
#     "provider": "LLMAppEnglishProvider",
#     "detector": "EndpointVllmClient",
#     "start_time": "2025-01-18T02:01:43.212783+00:00",
#     "end_time": "2025-01-18T02:01:44.268714+00:00",
#     "timezone_str": "UTC",
#     "env": "dev",
#     "input1_text": "how much energy did i use for charging in December 12, 2024",
#     "session_text": "",
#     "date": "2025-01-18",
#     "week_start_date": "2025-01-13",
#     "week_end_date": "2025-01-19"
#   }
class NluData(BaseModel):
    env: Optional[str] = ""
    user_id: Optional[str] = ""
    input1: Union[str, dict]
    input1_text: str
    input2: List[dict]
    output1: str
    output2: dict
    detect_time_cost: float
    total_time_cost: float
    client_type: str
    language: str
    provider: str
    detector: str
    start_time: str
    end_time: str
    timezone_str: str
    session_text: str
    date: str
    week_start_date: str
    week_end_date: str

    @computed_field
    @property
    def output_intent(self) -> str:
        return self.output2["intent"]


class Counter(BaseModel):
    SUCCESS: int = 0
    ERROR_STT: int = 0
    ERROR_INTENT: int = 0
    ERROR_TASK_RUNNING: int = 0
    ERROR_LANGUAGE: int = 0
    ERROR_TRANSLATE: int = 0
    ERROR_LLM_ANSWER: int = 0
    ERROR_UNKNOWN: int = 0
    _total: int = 0  # 私有字段存储总数
    _labeled: int = 0
    _unlabeled: int = 0

    def increment(self, field: str, amount: int = 1) -> None:
        current = getattr(self, field, 0)
        setattr(self, field, current + amount)
        self._total += amount

    @computed_field
    @property
    def total(self) -> int:
        return self._total

    @computed_field
    @cached_property
    def rates(self) -> dict[str, str]:
        success_rate = round(self.SUCCESS / self.total * 100, 3) if self.total > 0 else 0
        stt_rate = 100 - round(self.ERROR_STT / self.total * 100, 3) if self.total > 0 else 0
        intent_rate = 100 - round(self.ERROR_INTENT / self.total * 100, 3) if self.total > 0 else 0
        task_running_rate = 100 - round(self.ERROR_TASK_RUNNING / self.total *
                                        100, 3) if self.total > 0 else 0
        return {
            "SUCCESS": f"{success_rate}%",
            "SUCCESS_STT_RATE": f"{stt_rate}%",
            "SUCCESS_INTENT_RATE": f"{intent_rate}%",
            "SUCCESS_TASK_RUNNING_RATE": f"{task_running_rate}%",
        }

    @computed_field
    @property
    def labels(self) -> dict[str, int]:
        return {
            "labeled": self._labeled,
            "unlabeled": self._unlabeled,
        }


def docs_stats(docs: List[dict]):
    counter = Counter()
    for doc in docs:
        evaluation = doc["evaluation"]["message_evaluation"]
        if not evaluation:
            counter._unlabeled += 1
            continue
        counter._labeled += 1
        for _, value in evaluation.items():
            if value["__sys_message_type"] == "receive":
                eval_result = value["intent"]
                # `eval_result` is one of the following:
                # - "ERROR_STT", "ERROR_INTENT", "ERROR_TASK_RUNNING", "ERROR_LANGUAGE",
                # - "ERROR_TRANSLATE", "ERROR_LLM_ANSWER", "ERROR_UNKNOWN"
                counter.increment(eval_result)
                break
    result = {
        "counts": counter.model_dump(exclude=["rates", "total"]),
        "rates": counter.rates,
        "labels": counter.labels,
    }
    return result


async def DailyAccuracyHandler(request: HttpRequest):
    """每日的准确率"""
    env = request.GET.get("env")
    date = request.GET.get("date")
    if not date:
        raise HttpError(400, "date is required")
    # 暂时不要缓存
    # r = models.DailyStats.objects.filter(env=env, date=date).first()
    # if r:
    #     return OkResponse(data=results.DailyStats.model_validate(r))
    docs = await mongo_client.find_by_date(date=date, env=env)
    stats = docs_stats(docs)
    r = models.DailyStats(env=env,
                          date=date,
                          counts=stats["counts"],
                          rates=stats["rates"],
                          labels=stats["labels"])
    # r.save()
    return results.DailyStats.model_validate(r)


async def WeeklyAccuracyHandler(request: HttpRequest):
    """每周的准确率"""
    env = request.GET.get("env")
    finished, result = 0, []
    week_start_date = datetime.now() - timedelta(days=datetime.now().weekday())
    while True:
        week_start_date = week_start_date - timedelta(days=7)
        # 暂时不要缓存
        # r = models.WeeklyStats.objects.filter(
        #     env=env,
        #     week_start_date=week_start_date.strftime("%Y-%m-%d")).first()
        # if r:
        #     result.append(results.WeeklyStats.model_validate(r))
        #     continue
        docs = await mongo_client.find_by_week(
            env=env, week_start_date=week_start_date.strftime("%Y-%m-%d"))
        if not docs:
            finished += 1
            if finished >= 5:
                break
            continue
        stats = docs_stats(docs)
        r = models.WeeklyStats(env=env,
                               week_start_date=week_start_date.strftime("%Y-%m-%d"),
                               week_end_date=(week_start_date +
                                              timedelta(days=7)).strftime("%Y-%m-%d"),
                               counts=stats["counts"],
                               rates=stats["rates"],
                               labels=stats["labels"])
        # r.save()
        result.append(results.WeeklyStats.model_validate(r))
    return result


class RangeAccuracyRequest(BaseModel):
    env: Optional[str] = ""
    start_date: Optional[str] = Field(
        default_factory=lambda: (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
    end_date: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    @field_validator("start_date")
    def validate_start_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("start_date must be in the format YYYY-MM-DD")
        return v

    @field_validator("end_date")
    def validate_end_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("end_date must be in the format YYYY-MM-DD")
        return v


async def RangeAccuracyHandler(request: HttpRequest):
    """范围的准确率"""
    req = RangeAccuracyRequest(**request.GET)
    if not req.start_date or not req.end_date:
        # return FailedResponse(message="start_date and end_date are required")
        raise HttpError(400, "start_date and end_date are required")
    docs = await mongo_client.find_by_range(req.start_date, req.end_date, env=req.env)
    r = docs_stats(docs)
    r["start_date"] = req.start_date
    r["end_date"] = req.end_date
    return r


async def RangeDailyAccuracyHandler(request: HttpRequest):
    """范围的每日准确率"""
    req = RangeAccuracyRequest(**request.GET)
    if not req.start_date or not req.end_date:
        # return FailedResponse(message="start_date and end_date are required")
        raise HttpError(400, "start_date and end_date are required")

    result = []
    date = req.end_date
    while True:
        docs = await mongo_client.find_by_date(date=date, env=req.env)
        if docs:
            stats = docs_stats(docs)
            r = models.DailyStats(env=req.env,
                                  date=date,
                                  counts=stats["counts"],
                                  rates=stats["rates"],
                                  labels=stats["labels"])
            result.append(results.DailyStats.model_validate(r))
        date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=-1)).strftime("%Y-%m-%d")
        if date < req.start_date:
            break
    return result


async def ListErrorsHandler(request: HttpRequest):
    """列出所有错误"""
    env = request.GET.get("env")
    date = request.GET.get("date")
    docs = await mongo_client.find_errors(env=env, date=date)
    result = []
    for doc in docs:
        r = NluData(**doc["custom"]).model_dump()
        evaluation = doc["evaluation"]["message_evaluation"]
        if not evaluation:
            # 没有标注
            # r["label_type"] = ""
            # result.append(r)
            continue
        for _, value in evaluation.items():
            if value["__sys_message_type"] == "receive":
                eval_result = value["intent"]
                # `eval_result` is one of the following:
                # - "ERROR_STT", "ERROR_INTENT", "ERROR_TASK_RUNNING", "ERROR_LANGUAGE",
                # - "ERROR_TRANSLATE", "ERROR_LLM_ANSWER", "ERROR_UNKNOWN"
                r["label_type"] = eval_result
                break
        result.append(r)
    return result
