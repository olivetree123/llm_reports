from ninja import Redoc
from ninja import NinjaAPI

from main.utils.router import MyRouter
from main.handlers import stats

main_api = NinjaAPI(title="llm reports api", docs=Redoc(), version="0.1.0")

stats_router = MyRouter(tags=["统计"])
main_api.add_router(prefix="", router=stats_router)

stats_router.get("/stats/daily_accuracy", stats.DailyAccuracyHandler)
stats_router.get("/stats/weekly_accuracy", stats.WeeklyAccuracyHandler)
stats_router.get("/stats/range_accuracy", stats.RangeAccuracyHandler)
stats_router.get("/stats/range_daily_accuracy",
                 stats.RangeDailyAccuracyHandler)
stats_router.get("/stats/list_errors", stats.ListErrorsHandler)
