import motor.motor_asyncio
import os
from typing import List, Optional
from logger import get_logger

logger = get_logger(__name__)

MONGO_DETAILS = os.getenv("MONGO_URI", "mongodb://localhost:27017")

try:
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)
    database = client.blog_db
    posts_collection = database.get_collection("posts")
    users_collection = database.get_collection("users")
    logger.info("MongoDB client initialised (URI: %s)", MONGO_DETAILS)
except Exception as exc:
    logger.critical("Failed to create MongoDB client: %s", exc)
    raise


async def init_db():
    logger.info("Initialising database indexes…")
    try:
        await posts_collection.create_index("tags")
        await users_collection.create_index("username", unique=True)
        await users_collection.create_index("email", unique=True)
        logger.info("Database indexes created successfully.")
    except Exception as exc:
        logger.error("Index creation failed: %s", exc)
        raise

async def get_posts(tags: Optional[List[str]] = None, match_mode: str = "any") -> List[dict]:
    query: dict = {}
    if tags:
        if match_mode == "all":
            query["tags"] = {"$all": tags}
        elif match_mode == "any":
            query["tags"] = {"$in": tags}

    logger.debug("get_posts | query=%s match_mode=%s", query, match_mode)
    try:
        posts = []
        async for document in posts_collection.find(query):
            document["_id"] = str(document["_id"])
            posts.append(document)
        logger.info("get_posts | returned %d post(s)", len(posts))
        return posts
    except Exception as exc:
        logger.error("get_posts | DB error: %s", exc)
        raise


async def get_popular_tags(limit: int = 20) -> List[dict]:
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    logger.debug("get_popular_tags | limit=%d", limit)
    try:
        tags = []
        async for doc in posts_collection.aggregate(pipeline):
            tags.append({"tag": doc["_id"], "count": doc["count"]})
        logger.info("get_popular_tags | returned %d tag(s)", len(tags))
        return tags
    except Exception as exc:
        logger.error("get_popular_tags | DB error: %s", exc)
        raise


async def create_post(post_data: dict) -> dict:
    logger.debug("create_post | data=%s", {k: v for k, v in post_data.items() if k != "content"})
    try:
        result = await posts_collection.insert_one(post_data)
        new_post = await posts_collection.find_one({"_id": result.inserted_id})
        new_post["_id"] = str(new_post["_id"])
        logger.info("create_post | inserted _id=%s", new_post["_id"])
        return new_post
    except Exception as exc:
        logger.error("create_post | DB error: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def get_post_by_id(post_id: str) -> Optional[dict]:
    logger.debug("get_post_by_id | id=%s", post_id)
    try:
        from bson import ObjectId
        document = await posts_collection.find_one({"_id": ObjectId(post_id)})
        if document:
            document["_id"] = str(document["_id"])
        return document
    except Exception as exc:
        logger.error("get_post_by_id | DB error: %s", exc)
        return None

async def get_user_by_username(username: str) -> Optional[dict]:
    logger.debug("get_user_by_username | username=%s", username)
    try:
        user = await users_collection.find_one({"username": username})
        logger.debug("get_user_by_username | found=%s", user is not None)
        return user
    except Exception as exc:
        logger.error("get_user_by_username | DB error: %s", exc)
        raise


async def get_user_by_email(email: str) -> Optional[dict]:
    logger.debug("get_user_by_email | email=%s", email)
    try:
        user = await users_collection.find_one({"email": email})
        logger.debug("get_user_by_email | found=%s", user is not None)
        return user
    except Exception as exc:
        logger.error("get_user_by_email | DB error: %s", exc)
        raise


async def create_user(user_data: dict) -> dict:
    logger.debug("create_user | username=%s", user_data.get("username"))
    try:
        result = await users_collection.insert_one(user_data)
        new_user = await users_collection.find_one({"_id": result.inserted_id})
        new_user["_id"] = str(new_user["_id"])
        logger.info("create_user | inserted _id=%s", new_user["_id"])
        return new_user
    except Exception as exc:
        logger.error("create_user | DB error: %s", exc)
        raise
