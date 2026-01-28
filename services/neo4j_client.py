from typing import Any

from neo4j import GraphDatabase


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def ping(self) -> bool:
        with self._driver.session() as session:
            result = session.run("RETURN 1 AS ok")
            return result.single()["ok"] == 1

    def ensure_indexes(self) -> None:
        with self._driver.session() as session:
            session.run(
                "CREATE INDEX entity_attempt IF NOT EXISTS FOR (e:Entity) ON (e.attempt_id)"
            )
            session.run(
                "CREATE INDEX entity_corpus IF NOT EXISTS FOR (e:Entity) ON (e.corpus_id)"
            )

    def upsert_graph(self, entities: list[dict[str, Any]], relations: list[dict[str, Any]], corpus_id: str, attempt_id: str) -> None:
        with self._driver.session() as session:
            session.run(
                "UNWIND $entities AS ent "
                "MERGE (e:Entity {id: ent.id, attempt_id: $attempt_id}) "
                "SET e.name = ent.name, e.corpus_id = $corpus_id",
                entities=entities,
                attempt_id=attempt_id,
                corpus_id=corpus_id,
            )
            session.run(
                "UNWIND $relations AS rel "
                "MATCH (s:Entity {id: rel.source, attempt_id: $attempt_id}) "
                "MATCH (t:Entity {id: rel.target, attempt_id: $attempt_id}) "
                "MERGE (s)-[r:REL {type: rel.type, attempt_id: $attempt_id}]->(t) "
                "SET r.corpus_id = $corpus_id",
                relations=relations,
                attempt_id=attempt_id,
                corpus_id=corpus_id,
            )

    def get_neighbors(self, node_ids: list[str], attempt_id: str) -> list[str]:
        if not node_ids:
            return []
        with self._driver.session() as session:
            result = session.run(
                "MATCH (e:Entity {attempt_id: $attempt_id}) "
                "WHERE e.id IN $node_ids "
                "MATCH (e)-[:REL]->(n:Entity {attempt_id: $attempt_id}) "
                "RETURN DISTINCT n.id AS id",
                node_ids=node_ids,
                attempt_id=attempt_id,
            )
            return [record["id"] for record in result]

    def delete_attempt(self, attempt_id: str) -> None:
        with self._driver.session() as session:
            session.run(
                "MATCH (n {attempt_id: $attempt_id}) DETACH DELETE n",
                attempt_id=attempt_id,
            )

    def delete_namespace(self, namespace: str) -> None:
        with self._driver.session() as session:
            session.run(
                f"MATCH (n:`{namespace}`) DETACH DELETE n"
            )
