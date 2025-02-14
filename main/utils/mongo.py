import asyncio

from motor.motor_asyncio import AsyncIOMotorClient


class MongoClient:

    def __init__(self, uri, db_name):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    async def find_one(self, query=None, collection_name="Data"):
        collection = self.db[collection_name]
        document = await collection.find_one(query)
        print(document)
        return document

    async def find(self, query=None, collection_name="Data", sort=None):
        collection = self.db[collection_name]
        cursor = collection.find(query)
        if sort:
            cursor = cursor.sort(sort)
        documents = []
        async for document in cursor:
            documents.append(document)
        return documents

    async def find_by_date(self, date: str, env: str = "", collection_name: str = "Data"):
        query = {"custom.date": date}
        if env:
            query["custom.env"] = env
        documents = await self.find(query, collection_name)
        return documents

    async def find_by_week(self,
                           week_start_date: str,
                           env: str = "",
                           collection_name: str = "Data"):
        query = {"custom.week_start_date": week_start_date}
        if env:
            query["custom.env"] = env
        documents = await self.find(query, collection_name)
        return documents

    async def find_by_range(self,
                            start_date: str,
                            end_date: str,
                            env: str = "",
                            collection_name: str = "Data"):
        query = {"custom.date": {"$gte": start_date, "$lte": end_date}}
        if env:
            query["custom.env"] = env
        documents = await self.find(query, collection_name)
        return documents

    async def find_errors(self, env: str = "", date: str = "", collection_name: str = "Data"):
        query = {
            "evaluation.message_evaluation.693ce67c-98b9-4182-8a85-b1beb1aeda94": {
                "$exists": False
            }
        }
        if env:
            query["custom.env"] = env
        if date:
            query["custom.date"] = date
        documents = await self.find(query, collection_name, sort=[("custom.start_time", -1)])
        return documents


mongo_client = MongoClient(uri="mongodb://admin:123456@10.240.3.251:27017", db_name="label_llm")

if __name__ == "__main__":
    query = {"evaluation.message_evaluation.intent": "SUCCESS"}
    asyncio.run(mongo_client.find(query, "Data"))
