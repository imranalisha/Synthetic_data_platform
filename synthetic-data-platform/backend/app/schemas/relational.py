from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import Field, model_validator

from .common import MAX_ROWS, Identifier, Locale, Seed, StrictModel
from .tabular import NUMERIC_TYPES, ColumnSpec


class Cardinality(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


class RelationalPreset(str, Enum):
    ECOMMERCE = "ecommerce"   # customers, products, orders, order_items
    BANKING = "banking"       # customers, accounts, transactions


class TableSpec(StrictModel):
    name: Identifier
    row_count: int = Field(100, ge=1, le=MAX_ROWS)
    primary_key: Identifier = "id"
    primary_key_type: Literal["serial", "uuid"] = "serial"
    columns: list[ColumnSpec] = Field(default_factory=list, max_length=100,
                                      description="Business columns only; PK/FK columns are added by the engine.")


class RelationshipSpec(StrictModel):
    parent_table: Identifier
    child_table: Identifier
    fk_column: Identifier = Field(description="FK column in the child (1:1, 1:N) or the junction->parent column (N:N).")
    cardinality: Cardinality = Cardinality.ONE_TO_MANY
    min_children: int = Field(0, ge=0, le=1000)
    max_children: int | None = Field(None, ge=1, le=1000, description="Per-parent upper bound; None = unbounded.")
    junction_table: Identifier | None = Field(None, description="Required for N:N. Auto-created if not in 'tables'.")
    junction_child_fk_column: Identifier | None = Field(None, description="Required for N:N.")

    @model_validator(mode="after")
    def _check(self):
        if self.parent_table == self.child_table:
            raise ValueError("Self-referential relationships are not supported in v1.")
        if self.max_children is not None and self.max_children < self.min_children:
            raise ValueError("max_children must be >= min_children.")
        if self.cardinality == Cardinality.MANY_TO_MANY:
            if not self.junction_table or not self.junction_child_fk_column:
                raise ValueError("many_to_many requires junction_table and junction_child_fk_column.")
            if self.junction_table in (self.parent_table, self.child_table):
                raise ValueError("junction_table must differ from parent and child tables.")
            if self.fk_column == self.junction_child_fk_column:
                raise ValueError("Junction FK columns must have different names.")
        else:
            if self.junction_table or self.junction_child_fk_column:
                raise ValueError("junction_* fields are only valid for many_to_many.")
        if self.cardinality == Cardinality.ONE_TO_ONE:
            if self.max_children not in (None, 1) or self.min_children > 1:
                raise ValueError("one_to_one allows at most 1 child per parent.")
            self.max_children = 1
        return self


# ---- Cross-table mathematical consistency rules --------------------------------------------
class SumOfChildrenRule(StrictModel):
    """parent.parent_column == ROUND(SUM(child.child_column)) grouped by FK. Childless parents get 0."""
    kind: Literal["sum_of_children"] = "sum_of_children"
    parent_table: Identifier
    parent_column: Identifier
    child_table: Identifier
    child_column: Identifier
    fk_column: Identifier
    decimal_places: int = Field(2, ge=0, le=6)


class ProductRule(StrictModel):
    """table.target_column == ROUND(PRODUCT(factors)), e.g. line_total = quantity * unit_price."""
    kind: Literal["product"] = "product"
    table: Identifier
    target_column: Identifier
    factors: list[Identifier] = Field(min_length=2, max_length=5)
    decimal_places: int = Field(2, ge=0, le=6)


class CopyFromParentRule(StrictModel):
    """child.child_column := parent.parent_column via FK (e.g. price snapshot on order items)."""
    kind: Literal["copy_from_parent"] = "copy_from_parent"
    child_table: Identifier
    child_column: Identifier
    fk_column: Identifier
    parent_table: Identifier
    parent_column: Identifier


ConsistencyRule = Annotated[Union[SumOfChildrenRule, ProductRule, CopyFromParentRule],
                            Field(discriminator="kind")]


def _col(declared: dict, table: str, column: str, numeric: bool):
    if table not in declared:
        raise ValueError(f"Rule references unknown table '{table}' (junction tables must be declared in 'tables' to carry rules).")
    col = declared[table].get(column)
    if col is None:
        raise ValueError(f"Rule references undeclared column '{table}.{column}'.")
    if numeric and col.type not in NUMERIC_TYPES:
        raise ValueError(f"Rule column '{table}.{column}' must be numeric.")


class RelationalRequest(StrictModel):
    preset: RelationalPreset | None = None
    tables: list[TableSpec] = Field(default_factory=list, max_length=30)
    relationships: list[RelationshipSpec] = Field(default_factory=list, max_length=60)
    consistency_rules: list[ConsistencyRule] = Field(default_factory=list, max_length=60)
    seed: Seed | None = 42
    locale: Locale = Locale.EN_US

    @model_validator(mode="after")
    def _validate_graph(self):
        if (self.preset is None) == (len(self.tables) == 0):
            raise ValueError("Provide exactly one of 'preset' or 'tables'.")
        if self.preset is not None:
            if self.relationships or self.consistency_rules:
                raise ValueError("relationships/consistency_rules must be empty when a preset is used.")
            return self

        tables = {t.name: t for t in self.tables}
        if len(tables) != len(self.tables):
            raise ValueError("Table names must be unique.")
        declared = {}
        for t in self.tables:
            names = [c.name for c in t.columns]
            if len(names) != len(set(names)) or t.primary_key in names:
                raise ValueError(f"Table '{t.name}': duplicate column names or column collides with primary key.")
            declared[t.name] = {c.name: c for c in t.columns}

        edges, seen_fk, fk_parent = [], set(), {}
        for r in self.relationships:
            for tn in (r.parent_table, r.child_table):
                if tn not in tables:
                    raise ValueError(f"Relationship references unknown table '{tn}'.")
            if r.cardinality == Cardinality.MANY_TO_MANY:
                owner = r.junction_table
                fks = [(r.fk_column, r.parent_table), (r.junction_child_fk_column, r.child_table)]
                edges += [(r.parent_table, owner), (r.child_table, owner)]
            else:
                owner, fks = r.child_table, [(r.fk_column, r.parent_table)]
                edges.append((r.parent_table, r.child_table))
            for fk, parent in fks:
                if (owner, fk) in seen_fk:
                    raise ValueError(f"Duplicate FK column '{owner}.{fk}'.")
                seen_fk.add((owner, fk))
                fk_parent[(owner, fk)] = parent
                if owner in tables and (fk == tables[owner].primary_key or fk in declared[owner]):
                    raise ValueError(f"FK column '{owner}.{fk}' collides with a declared column or the primary key.")
            # feasibility: the owner's declared row_count must be reachable under the bounds
            if owner in tables:
                parents, rows = tables[r.parent_table].row_count, tables[owner].row_count
                if r.max_children is not None and rows > parents * r.max_children:
                    raise ValueError(f"'{owner}' has {rows} rows but {parents} parents x max_children={r.max_children} allows fewer.")
                if rows < parents * r.min_children:
                    raise ValueError(f"'{owner}' has {rows} rows but {parents} parents x min_children={r.min_children} requires more.")

        # acyclicity (Kahn) -> guarantees a valid parent-before-child generation order
        nodes = set(tables) | {n for e in edges for n in e}
        indeg, adj = {n: 0 for n in nodes}, {n: [] for n in nodes}
        for a, b in edges:
            adj[a].append(b); indeg[b] += 1
        queue, visited = [n for n, d in indeg.items() if d == 0], 0
        while queue:
            n = queue.pop(); visited += 1
            for m in adj[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    queue.append(m)
        if visited != len(nodes):
            raise ValueError("Relationships form a cycle; FK graph must be acyclic.")

        for rule in self.consistency_rules:
            if rule.kind == "sum_of_children":
                _col(declared, rule.parent_table, rule.parent_column, True)
                _col(declared, rule.child_table, rule.child_column, True)
                if fk_parent.get((rule.child_table, rule.fk_column)) != rule.parent_table:
                    raise ValueError(f"No relationship {rule.parent_table} -> {rule.child_table}.{rule.fk_column}.")
            elif rule.kind == "product":
                _col(declared, rule.table, rule.target_column, True)
                if rule.target_column in rule.factors:
                    raise ValueError("target_column cannot be one of its own factors.")
                for f in rule.factors:
                    _col(declared, rule.table, f, True)
            else:
                _col(declared, rule.child_table, rule.child_column, False)
                _col(declared, rule.parent_table, rule.parent_column, False)
                if fk_parent.get((rule.child_table, rule.fk_column)) != rule.parent_table:
                    raise ValueError(f"No relationship {rule.parent_table} -> {rule.child_table}.{rule.fk_column}.")
        return self


class RelationalPreviewRequest(RelationalRequest):
    preview_row_cap: int = Field(25, ge=1, le=200, description="Max rows returned per table in the preview.")


class RelationalExportFormat(str, Enum):
    SQL = "sql"
    JSON = "json"
    CSV_ZIP = "csv_zip"


class SqlDialect(str, Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MYSQL = "mysql"


class RelationalExportRequest(RelationalRequest):
    format: RelationalExportFormat = RelationalExportFormat.SQL
    sql_dialect: SqlDialect = SqlDialect.POSTGRES
    include_ddl: bool = True
    insert_batch_size: int = Field(500, ge=1, le=5000)


class TableData(StrictModel):
    name: str
    primary_key: str
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int


class IntegrityCheck(StrictModel):
    name: str
    kind: Literal["pk_unique", "fk_valid", "cardinality", "sum_of_children", "product", "copy_from_parent"]
    table: str
    passed: bool
    violations: int = 0
    detail: str | None = None


class IntegrityReport(StrictModel):
    passed: bool
    checks: list[IntegrityCheck]


class RelationalResponse(StrictModel):
    seed: int
    generation_order: list[str]
    tables: list[TableData]
    integrity: IntegrityReport
    generation_ms: float