from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

try:
    from neo4j import GraphDatabase, Transaction  # type: ignore
    from neo4j import Driver as Neo4jDriver  # type: ignore
    from neo4j.exceptions import Neo4jError  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    GraphDatabase = None  # type: ignore
    Neo4jDriver = Any  # type: ignore
    Transaction = Any  # type: ignore
    Neo4jError = RuntimeError  # type: ignore

__all__ = [
    "Neo4jConnectionConfig",
    "Neo4jDriverManager",
    "Neo4jSchemaSnapshot",
    "Neo4jSchemaDiff",
    "Neo4jMigrationAction",
    "Neo4jMigrationPlan",
    "Neo4jMigrationResult",
    "Neo4jSchemaPlanner",
    "Neo4jTransactionalBatchExecutor",
    "Neo4jIncrementalJobAdvisor",
    "JobSliceRecommendation",
]


def _require_neo4j_driver() -> None:
    if GraphDatabase is None:  # pragma: no cover - defensive
        raise ImportError(
            "The neo4j package is required for Neo4j helpers. "
            "Install plexity-sdk[enterprise] or add neo4j>=5.16 manually."
        )


@dataclass(frozen=True)
class Neo4jConnectionConfig:
    """Connection details for Neo4j Aura / Bolt routing."""

    uri: str
    username: str
    password: str
    database: Optional[str] = None
    max_connection_lifetime: float = 3600.0
    max_connection_pool_size: int = 50
    encrypted: bool = True


class Neo4jDriverManager:
    """Manages a shared Neo4j driver with connection pooling."""

    def __init__(self, config: Neo4jConnectionConfig) -> None:
        _require_neo4j_driver()
        self._config = config
        self._driver: Optional[Neo4jDriver] = None

    @property
    def config(self) -> Neo4jConnectionConfig:
        return self._config

    def get_driver(self) -> Neo4jDriver:
        if self._driver is None:
            auth = (self._config.username, self._config.password)
            self._driver = GraphDatabase.driver(
                self._config.uri,
                auth=auth,
                max_connection_lifetime=self._config.max_connection_lifetime,
                max_connection_pool_size=self._config.max_connection_pool_size,
                encrypted=self._config.encrypted,
            )
        return self._driver

    def verify_connectivity(self) -> None:
        driver = self.get_driver()
        driver.verify_connectivity()

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None


def _sorted_tuple(value: Iterable[str]) -> Tuple[str, ...]:
    return tuple(sorted(set(value)))


@dataclass(frozen=True)
class IndexDefinition:
    name: str
    index_type: str
    entity_type: str
    labels_or_types: Tuple[str, ...]
    properties: Tuple[str, ...]

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "IndexDefinition":
        return cls(
            name=record.get("name"),
            index_type=record.get("type", ""),
            entity_type=record.get("entityType", ""),
            labels_or_types=_sorted_tuple(record.get("labelsOrTypes", ())),
            properties=_sorted_tuple(record.get("properties", ())),
        )


@dataclass(frozen=True)
class ConstraintDefinition:
    name: str
    constraint_type: str
    entity_type: str
    labels_or_types: Tuple[str, ...]
    properties: Tuple[str, ...]

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "ConstraintDefinition":
        return cls(
            name=record.get("name"),
            constraint_type=record.get("type", ""),
            entity_type=record.get("entityType", ""),
            labels_or_types=_sorted_tuple(record.get("labelsOrTypes", ())),
            properties=_sorted_tuple(record.get("properties", ())),
        )


@dataclass(frozen=True)
class Neo4jSchemaSnapshot:
    labels: Mapping[str, Tuple[str, ...]]
    relationships: Mapping[str, Tuple[str, ...]]
    indexes: Tuple[IndexDefinition, ...]
    constraints: Tuple[ConstraintDefinition, ...]

    @classmethod
    def from_database(cls, manager: Neo4jDriverManager) -> "Neo4jSchemaSnapshot":
        driver = manager.get_driver()
        labels: MutableMapping[str, set[str]] = {}
        relationships: MutableMapping[str, set[str]] = {}
        indexes: List[IndexDefinition] = []
        constraints: List[ConstraintDefinition] = []

        with driver.session(database=manager.config.database) as session:
            node_records = session.run("CALL db.schema.nodeTypeProperties()")
            for record in node_records:
                label_list = record.get("nodeLabels") or []
                prop = record.get("propertyName")
                for label in label_list:
                    labels.setdefault(label, set()).add(prop)

            rel_records = session.run("CALL db.schema.relTypeProperties()")
            for record in rel_records:
                rel_type = record.get("relationshipType")
                prop = record.get("propertyName")
                if rel_type:
                    relationships.setdefault(rel_type, set()).add(prop)

            index_records = session.run("SHOW INDEXES")
            indexes = [IndexDefinition.from_record(record.data()) for record in index_records]

            constraint_records = session.run("SHOW CONSTRAINTS")
            constraints = [ConstraintDefinition.from_record(record.data()) for record in constraint_records]

        return cls(
            labels={label: _sorted_tuple(props) for label, props in labels.items()},
            relationships={rel: _sorted_tuple(props) for rel, props in relationships.items()},
            indexes=tuple(indexes),
            constraints=tuple(constraints),
        )

    def diff(self, target: "Neo4jSchemaSnapshot") -> "Neo4jSchemaDiff":
        current_labels = {label: set(props) for label, props in self.labels.items()}
        target_labels = {label: set(props) for label, props in target.labels.items()}
        current_relationships = {rel: set(props) for rel, props in self.relationships.items()}
        target_relationships = {rel: set(props) for rel, props in target.relationships.items()}

        added_labels: Dict[str, set[str]] = {}
        removed_labels: Dict[str, set[str]] = {}
        for label, props in target_labels.items():
            missing = props - current_labels.get(label, set())
            if missing:
                added_labels[label] = missing
        for label, props in current_labels.items():
            missing = props - target_labels.get(label, set())
            if missing:
                removed_labels[label] = missing

        added_relationships: Dict[str, set[str]] = {}
        removed_relationships: Dict[str, set[str]] = {}
        for rel, props in target_relationships.items():
            missing = props - current_relationships.get(rel, set())
            if missing:
                added_relationships[rel] = missing
        for rel, props in current_relationships.items():
            missing = props - target_relationships.get(rel, set())
            if missing:
                removed_relationships[rel] = missing

        current_indexes = set(self.indexes)
        target_indexes = set(target.indexes)
        current_constraints = set(self.constraints)
        target_constraints = set(target.constraints)

        return Neo4jSchemaDiff(
            added_node_properties={label: tuple(sorted(props)) for label, props in added_labels.items()},
            removed_node_properties={label: tuple(sorted(props)) for label, props in removed_labels.items()},
            added_relationship_properties={rel: tuple(sorted(props)) for rel, props in added_relationships.items()},
            removed_relationship_properties={rel: tuple(sorted(props)) for rel, props in removed_relationships.items()},
            added_indexes=tuple(sorted(target_indexes - current_indexes, key=lambda idx: idx.name or "")),
            removed_indexes=tuple(sorted(current_indexes - target_indexes, key=lambda idx: idx.name or "")),
            added_constraints=tuple(sorted(target_constraints - current_constraints, key=lambda c: c.name or "")),
            removed_constraints=tuple(sorted(current_constraints - target_constraints, key=lambda c: c.name or "")),
        )


@dataclass(frozen=True)
class Neo4jSchemaDiff:
    added_node_properties: Mapping[str, Tuple[str, ...]]
    removed_node_properties: Mapping[str, Tuple[str, ...]]
    added_relationship_properties: Mapping[str, Tuple[str, ...]]
    removed_relationship_properties: Mapping[str, Tuple[str, ...]]
    added_indexes: Sequence[IndexDefinition]
    removed_indexes: Sequence[IndexDefinition]
    added_constraints: Sequence[ConstraintDefinition]
    removed_constraints: Sequence[ConstraintDefinition]

    def is_empty(self) -> bool:
        return (
            not self.added_node_properties
            and not self.removed_node_properties
            and not self.added_relationship_properties
            and not self.removed_relationship_properties
            and not self.added_indexes
            and not self.removed_indexes
            and not self.added_constraints
            and not self.removed_constraints
        )


@dataclass(frozen=True)
class Neo4jMigrationAction:
    statement: str
    description: str
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Neo4jMigrationPlan:
    actions: Sequence[Neo4jMigrationAction]

    def is_empty(self) -> bool:
        return len(self.actions) == 0


class Neo4jSchemaPlanner:
    """Plans schema diffs and executable migrations."""

    def __init__(self, manager: Neo4jDriverManager) -> None:
        self._manager = manager

    def snapshot(self) -> Neo4jSchemaSnapshot:
        return Neo4jSchemaSnapshot.from_database(self._manager)

    def diff(self, target: Neo4jSchemaSnapshot, *, current: Optional[Neo4jSchemaSnapshot] = None) -> Neo4jSchemaDiff:
        baseline = current or self.snapshot()
        return baseline.diff(target)

    def plan_migration(
        self,
        target: Neo4jSchemaSnapshot,
        *,
        current: Optional[Neo4jSchemaSnapshot] = None,
    ) -> Neo4jMigrationPlan:
        diff = self.diff(target, current=current)
        if diff.is_empty():
            return Neo4jMigrationPlan(actions=())

        actions: List[Neo4jMigrationAction] = []

        for index in diff.removed_indexes:
            if index.name:
                actions.append(
                    Neo4jMigrationAction(
                        statement=f"DROP INDEX {index.name}",
                        description=f"Drop index {index.name}",
                    )
                )

        for constraint in diff.removed_constraints:
            if constraint.name:
                actions.append(
                    Neo4jMigrationAction(
                        statement=f"DROP CONSTRAINT {constraint.name}",
                        description=f"Drop constraint {constraint.name}",
                    )
                )

        for index in diff.added_indexes:
            label_expr = ":".join(f"`{label}`" for label in index.labels_or_types if label)
            props_expr = ", ".join(f"n.`{prop}`" for prop in index.properties if prop)
            if not label_expr or not props_expr:
                statement = "// Informational: index metadata incomplete"
            elif index.entity_type == "NODE":
                statement = f"CREATE INDEX {index.name} IF NOT EXISTS FOR (n:{label_expr}) ON ({props_expr})"
            else:
                statement = f"// TODO: index creation for entity type {index.entity_type}"
            actions.append(
                Neo4jMigrationAction(
                    statement=statement,
                    description=f"Create index {index.name}",
                )
            )

        for constraint in diff.added_constraints:
            label_expr = ":".join(f"`{label}`" for label in constraint.labels_or_types if label)
            props_expr = ", ".join(f"n.`{prop}`" for prop in constraint.properties if prop)
            if not label_expr or not props_expr:
                statement = "// Informational: constraint metadata incomplete"
            elif constraint.constraint_type.endswith("UNIQUENESS"):
                statement = (
                    f"CREATE CONSTRAINT {constraint.name} IF NOT EXISTS "
                    f"FOR (n:{label_expr}) REQUIRE ({props_expr}) IS UNIQUE"
                )
            else:
                statement = f"// TODO: constraint creation for type {constraint.constraint_type}"
            actions.append(
                Neo4jMigrationAction(
                    statement=statement,
                    description=f"Create constraint {constraint.name}",
                )
            )

        # Informational statements for node / relationship property diffs.
        for label, properties in diff.added_node_properties.items():
            actions.append(
                Neo4jMigrationAction(
                    statement="// Informational: add node properties",
                    description=f"Add node properties {properties} on label {label}",
                )
            )
        for label, properties in diff.removed_node_properties.items():
            actions.append(
                Neo4jMigrationAction(
                    statement="// Informational: remove node properties",
                    description=f"Remove node properties {properties} on label {label}",
                )
            )
        for rel, properties in diff.added_relationship_properties.items():
            actions.append(
                Neo4jMigrationAction(
                    statement="// Informational: add relationship properties",
                    description=f"Add relationship properties {properties} on type {rel}",
                )
            )
        for rel, properties in diff.removed_relationship_properties.items():
            actions.append(
                Neo4jMigrationAction(
                    statement="// Informational: remove relationship properties",
                    description=f"Remove relationship properties {properties} on type {rel}",
                )
            )

        return Neo4jMigrationPlan(actions=tuple(actions))


@dataclass
class Neo4jMigrationResult:
    executed: int
    skipped: int
    failures: Sequence[str]


class Neo4jTransactionalBatchExecutor:
    """Executes migration actions in transactional batches."""

    def __init__(self, manager: Neo4jDriverManager, *, batch_size: int = 50) -> None:
        self._manager = manager
        self._batch_size = max(1, batch_size)

    def run_plan(self, plan: Neo4jMigrationPlan, *, dry_run: bool = False) -> Neo4jMigrationResult:
        if plan.is_empty():
            return Neo4jMigrationResult(executed=0, skipped=0, failures=())

        if dry_run:
            return Neo4jMigrationResult(executed=0, skipped=len(plan.actions), failures=())

        driver = self._manager.get_driver()
        executed = 0
        failures: List[str] = []

        with driver.session(database=self._manager.config.database) as session:
            tx: Optional[Transaction] = None
            try:
                for idx, action in enumerate(plan.actions):
                    if action.statement.startswith("//"):
                        continue
                    if tx is None:
                        tx = session.begin_transaction()
                    tx.run(action.statement, action.parameters)
                    executed += 1
                    if executed % self._batch_size == 0:
                        tx.commit()
                        tx = None
                if tx is not None:
                    tx.commit()
            except Neo4jError as err:  # pragma: no cover - requires live Neo4j
                if tx is not None:
                    tx.rollback()
                failures.append(str(err))

        return Neo4jMigrationResult(executed=executed, skipped=0, failures=tuple(failures))


@dataclass(frozen=True)
class JobSliceRecommendation:
    label: str
    org_id: Optional[str]
    node_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {"label": self.label, "orgId": self.org_id, "count": self.node_count}


class Neo4jIncrementalJobAdvisor:
    """Generates incremental job slices grouped by label/org."""

    def __init__(
        self,
        manager: Neo4jDriverManager,
        *,
        org_id_property: str = "orgId",
    ) -> None:
        self._manager = manager
        self._org_id_property = org_id_property

    def recommend(
        self,
        *,
        labels: Optional[Sequence[str]] = None,
        limit: int = 25,
    ) -> List[JobSliceRecommendation]:
        driver = self._manager.get_driver()
        params = {
            "labels": list(labels) if labels else None,
            "limit": max(1, int(limit)),
            "orgProp": self._org_id_property,
        }

        cypher = """
        MATCH (n)
        WHERE $labels IS NULL OR any(label IN labels(n) WHERE label IN $labels)
        WITH labels(n) AS nodeLabels, n[$orgProp] AS orgId
        UNWIND nodeLabels AS nodeLabel
        WITH nodeLabel AS label, orgId, count(*) AS nodeCount
        ORDER BY nodeCount DESC
        RETURN label, orgId, nodeCount
        LIMIT $limit
        """

        recommendations: List[JobSliceRecommendation] = []
        with driver.session(database=self._manager.config.database) as session:
            records = session.run(cypher, params)
            for record in records:
                recommendations.append(
                    JobSliceRecommendation(
                        label=record.get("label"),
                        org_id=record.get("orgId"),
                        node_count=record.get("nodeCount", 0),
                    )
                )
        return recommendations
