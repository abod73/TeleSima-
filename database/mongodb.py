import pymongo
from pymongo.errors import ConnectionFailure
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MongoManager:
    _client: Optional[pymongo.MongoClient] = None
    _db: Optional[pymongo.database.Database] = None
    _uri: Optional[str] = None

    @classmethod
    def initialize(cls, uri: str, db_name: str = "telicinema") -> None:
        if cls._client is None:
            try:
                cls._uri = uri
                cls._client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
                cls._client.admin.command('ping') # Test connection
                cls._db = cls._client[db_name]
                logger.info("MongoDB connection established successfully.")
            except ConnectionFailure as e:
                logger.error(f"MongoDB connection failed: {e}")
                cls._client = None
                cls._db = None
            except Exception as e:
                logger.error(f"An unexpected error occurred during MongoDB initialization: {e}")
                cls._client = None
                cls._db = None
        else:
            logger.info("MongoDB client already initialized.")

    @classmethod
    def get_client(cls) -> Optional[pymongo.MongoClient]:
        if cls._client is None:
            logger.warning("MongoDB client requested but not initialized. Call initialize() first.")
        return cls._client

    @classmethod
    def get_db(cls) -> Optional[pymongo.database.Database]:
        if cls._db is None:
            logger.warning("MongoDB database requested but not initialized. Call initialize() first.")
        return cls._db

    @classmethod
    def close_connection(cls) -> None:
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            logger.info("MongoDB connection closed.")

    @classmethod
    def is_initialized(cls) -> bool:
        return cls._client is not None and cls._db is not None

    @classmethod
    def get_collection(cls, collection_name: str) -> Optional[pymongo.collection.Collection]:
        if cls._db:
            return cls._db[collection_name]
        logger.error(f"Cannot get collection '{collection_name}', MongoDB is not initialized.")
        return None

# Example of how to use (for testing purposes, not to be run in Colab)
if __name__ == '__main__':
    # In a real app, URI would come from environment variables
    # os.environ["MONGODB_URI"] = "mongodb://localhost:27017/"
    # MongoManager.initialize(os.getenv("MONGODB_URI"))
    print("MongoManager class defined. Not connecting to DB in Colab.")
