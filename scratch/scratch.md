Here is your script using **python-arango-async**, integrated with **Loguru** for comprehensive async-aware logging. This ensures your log statements are non-blocking and suitable for asyncio applications by using `enqueue=True` when adding a log sink[5][2].

```python
import asyncio
from arangoasync import ArangoClient
from arangoasync.auth import Auth
from loguru import logger

ARANGO_URL = "http://localhost:8529"
DB_NAME = "your_db"
USERNAME = "root"
PASSWORD = "password"

# Set up Loguru for non-blocking, asynchronous logging
logger.remove()
logger.add("database_structure.log", enqueue=True, level="INFO", format="{time} | {level} | {message}")

async def sample_random_documents(db, col_name, limit=2):
    query = f"FOR doc IN `{col_name}` SORT RAND() LIMIT {limit} RETURN doc"
    logger.debug(f"Sampling up to {limit} random docs from collection '{col_name}'.")
    cursor = await db.aql.execute(query)
    results = []
    async for doc in cursor:
        results.append(doc)
    return results

async def main():
    logger.info(f"Connecting to ArangoDB at {ARANGO_URL} and database '{DB_NAME}'.")
    async with ArangoClient(hosts=ARANGO_URL) as client:
        auth = Auth(username=USERNAME, password=PASSWORD)
        db = await client.db(DB_NAME, auth=auth)

        all_collections = [col async for col in db.collections()]
        user_collections = [col for col in all_collections if not col["name"].startswith("_")]
        logger.info(f"Found {len(user_collections)} user collections (excluding system collections).")

        for col in user_collections:
            name, col_type = col['name'], col['type']
            type_str = 'document' if col_type == 2 else 'edge' if col_type == 3 else 'unknown'
            logger.info(f"Processing collection: {name} (type: {type_str})")
            docs = await sample_random_documents(db, name, limit=2)

            if col_type == 2:   # Document/vertex collection
                if not docs:
                    logger.info(f"  No documents found in '{name}'.")
                else:
                    logger.info(f"  Sample document(s) from '{name}':")
                    for doc in docs:
                        logger.info(f"    {doc}")

            elif col_type == 3:  # Edge collection
                if not docs:
                    logger.info(f"  No edges found in '{name}'.")
                else:
                    logger.info(f"  Sample edge(s) from '{name}':")
                    for edge in docs:
                        logger.info(f"    From: {edge.get('_from', 'N/A')} -> To: {edge.get('_to', 'N/A')}")
                        logger.info(f"    Edge data: {edge}")

        # List all ArangoSearch views and describe indexed collections/fields/analyzers
        logger.info("Inspecting ArangoSearch Views and Analyzers.")
        async for view in db.views():
            logger.info(f"- View: {view['name']}")
            links = view.get('links', {})
            if not links:
                logger.info("    No linked collections.")
            else:
                for col_name, link_info in links.items():
                    logger.info(f"    Indexed Collection: {col_name}")
                    fields = link_info.get('fields', {})
                    if not fields:
                        logger.info("      No field-level analyzers.")
                    else:
                        for field, fparams in fields.items():
                            logger.info(f"      Field: {field}, Analyzers: {fparams.get('analyzers', [])}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Highlights:**
- **Loguru** with `enqueue=True` ensures log records are queued and written in a thread-safe, non-blocking manner suitable for async apps[5][2].
- All major actions and outputs are logged.
- You can customize log file/location and log formatting as needed.

This script will log a detailed schema/relationship/view summary to `database_structure.log` and display messages in real time, giving any agent or user a clear, logged overview of your ArangoDB structure and search configuration.

[1] https://docs.python-arango.com/en/main/async.html
[2] https://signoz.io/guides/loguru/
[3] https://github.com/Delgan/loguru/issues/171
[4] https://github.com/arangodb/python-arango-async
[5] https://last9.io/blog/python-loguru/
[6] https://python-arango-async.readthedocs.io
[7] https://docs.python-arango.com/en/main/logging.html
[8] https://python.plainenglish.io/mastering-logging-in-python-with-loguru-and-pydantic-settings-a-complete-guide-for-cross-module-a6205a987251
[9] https://docs.cloudera.com/data-engineering/cloud/upgrading-cde/cde-upgrading.pdf
[10] https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.8.txt