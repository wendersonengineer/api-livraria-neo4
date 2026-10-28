import os
from neo4j import GraphDatabase


# Carrega o arquivo .env se ele existir localmente
# Configuração direta para o seu computador local (localhost)
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "migracao"


class Neo4jConnection:
    _driver = None

    @classmethod
    def get_driver(cls):
        if cls._driver is None:
            cls._driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        return cls._driver

    @classmethod
    def close(cls):
        if cls._driver is not None:
            cls._driver.close()
            cls._driver = None
