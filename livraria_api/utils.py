import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env local de forma segura
load_dotenv()

# O Python lê as credenciais direto da memória invisível do sistema
NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")


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
