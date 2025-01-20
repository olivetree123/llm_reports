import logging
from typing import List, Optional
from datetime import datetime, timedelta

from pydantic import (
    BaseModel,
    computed_field,
    field_validator,
)
from django.http import HttpRequest
from functools import cached_property

from main.utils.response import (
    OkResponse,
    FailedResponse,
)
from main import models, results
from main.utils.mongo import mongo_client

logger = logging.getLogger(__name__)


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
        return {
            "SUCCESS":
            f"{round(self.SUCCESS / self.total*100, 2)}%",
            "ERROR_STT":
            f"{round(self.ERROR_STT / self.total*100, 2)}%",
            "ERROR_INTENT":
            f"{round(self.ERROR_INTENT / self.total*100, 2)}%",
            "ERROR_TASK_RUNNING":
            f"{round(self.ERROR_TASK_RUNNING / self.total*100, 2)}%",
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
        return FailedResponse(message="date is required")
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
    return OkResponse(data=results.DailyStats.model_validate(r))


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
        r = models.WeeklyStats(
            env=env,
            week_start_date=week_start_date.strftime("%Y-%m-%d"),
            week_end_date=(week_start_date +
                           timedelta(days=7)).strftime("%Y-%m-%d"),
            counts=stats["counts"],
            rates=stats["rates"])
        # r.save()
        result.append(results.WeeklyStats.model_validate(r))
    return OkResponse(data=result)


class RangeAccuracyRequest(BaseModel):
    env: Optional[str] = ""
    start_date: Optional[str] = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date: Optional["str"] = datetime.now().strftime("%Y-%m-%d")

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
        return FailedResponse(message="start_date and end_date are required")
    docs = await mongo_client.find_by_range(req.start_date,
                                            req.end_date,
                                            env=req.env)
    r = docs_stats(docs)
    r["start_date"] = req.start_date
    r["end_date"] = req.end_date
    return OkResponse(data=r)


async def RangeDailyAccuracyHandler(request: HttpRequest):
    """范围的每日准确率"""
    req = RangeAccuracyRequest(**request.GET)
    if not req.start_date or not req.end_date:
        return FailedResponse(message="start_date and end_date are required")

    result = []
    date = req.start_date
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
        date = (datetime.strptime(date, "%Y-%m-%d") +
                timedelta(days=1)).strftime("%Y-%m-%d")
        if date > req.end_date:
            break
    return OkResponse(data=result)
