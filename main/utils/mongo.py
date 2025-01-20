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

    async def find(self, query=None, collection_name="Data"):
        collection = self.db[collection_name]
        cursor = collection.find(query)
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

    async def find_by_week(self, week_start_date: str, env: str = "", collection_name: str = "Data"):
        query = {"custom.week_start_date": week_start_date}
        if env:
            query["custom.env"] = env
        documents = await self.find(query, collection_name)
        return documents

    async def find_by_range(self, start_date: str, end_date: str, env: str = "", collection_name: str = "Data"):
        query = {"custom.date": {"$gte": start_date, "$lte": end_date}}
        if env:
            query["custom.env"] = env
        documents = await self.find(query, collection_name)
        return documents


mongo_client = MongoClient(uri="mongodb://admin:123456@10.240.3.251:27017", db_name="label_llm")


if __name__ == "__main__":
    asyncio.run(mongo_client.find("Data"))
