from neo4j import GraphDatabase, Driver
from app.core.config import settings

class Neo4jDriver:
    _driver: Driver | None = None

    @classmethod
    def get_driver(cls) -> Driver:
        if cls._driver is None:
            cls._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
        return cls._driver

    @classmethod
    def close_driver(cls):
        if cls._driver is not None:
            cls._driver.close()
            cls._driver = None

def get_neo4j_session():
    driver = Neo4jDriver.get_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()
