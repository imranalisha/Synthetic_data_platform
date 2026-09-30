from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from .common import Identifier, Locale, Rate, StrictModel
from .relational import Cardinality, RelationalRequest
from .tabular import ColumnType, TabularRequest


class SchemaSourceType(str, Enum):
    DDL = "ddl"
    JSON_SAMPLE = "json_sample"
    CSV_SAMPLE = "csv_sample"
    NATURAL_LANGUAGE = "natural_language"


class SchemaInferenceRequest(StrictModel):
    source_type: SchemaSourceType
    content: str = Field(min_length=1, max_length=200_000)
    max_tables: int = Field(10, ge=1, le=20)
    include_edge_cases: bool = True
    locale: Locale = Locale.EN_US
    model: str | None = Field(None, description="Override the configured LiteLLM model.")


class EdgeCasePattern(StrictModel):
    pattern_type: Literal["unicode", "boundary", "empty_string", "long_string", "duplicate",
                          "future_date", "negative", "special_chars", "null_heavy", "outlier"]
    description: str
    example: str | None = None
    suggested_rate: Rate = 0.02


class ForeignKeyRef(StrictModel):
    table: Identifier
    column: Identifier


class InferredColumn(StrictModel):
    name: Identifier
    type: ColumnType
    nullable: bool = True
    is_primary_key: bool = False
    references: ForeignKeyRef | None = None
    description: str | None = None
    example_values: list[str] = Field(default_factory=list, max_length=10)
    edge_cases: list[EdgeCasePattern] = Field(default_factory=list, max_length=5)


class InferredTable(StrictModel):
    name: Identifier
    columns: list[InferredColumn] = Field(min_length=1)
    suggested_row_count: int = Field(100, ge=1, le=100_000)


class InferredRelationship(StrictModel):
    parent_table: Identifier
    parent_column: Identifier
    child_table: Identifier
    child_column: Identifier
    cardinality: Cardinality = Cardinality.ONE_TO_MANY


class InferredSchema(StrictModel):
    """LLM output is untrusted: every reference is verified before it leaves the AI layer."""
    tables: list[InferredTable] = Field(min_length=1)
    relationships: list[InferredRelationship] = Field(default_factory=list)

    @model_validator(mode="after")
    def _refs(self):
        cols = {t.name: {c.name for c in t.columns} for t in self.tables}
        if len(cols) != len(self.tables):
            raise ValueError("Duplicate table names in inferred schema.")
        for t in self.tables:
            for c in t.columns:
                if c.references and c.references.column not in cols.get(c.references.table, set()):
                    raise ValueError(f"{t.name}.{c.name} references unknown {c.references.table}.{c.references.column}.")
        for r in self.relationships:
            if r.parent_column not in cols.get(r.parent_table, set()) or r.child_column not in cols.get(r.child_table, set()):
                raise ValueError(f"Relationship {r.parent_table}->{r.child_table} references unknown columns.")
        return self


class SchemaInferenceResponse(StrictModel):
    inferred_schema: InferredSchema
    model_used: str
    fallback_used: bool = Field(False, description="True if heuristics replaced the LLM (no key / call failed).")
    warnings: list[str] = []
    # Ready-to-generate payloads so the UI can pipe inference straight into the engines.
    tabular_request: TabularRequest | None = None
    relational_request: RelationalRequest | None = None


class TextKind(str, Enum):
    PERSON_NAME = "person_name"
    ADDRESS = "address"
    COMPANY = "company"
    PRODUCT_DESCRIPTION = "product_description"
    EMAIL = "email"
    FREE_TEXT = "free_text"


class TextSynthesisRequest(StrictModel):
    kind: TextKind
    locale: Locale = Locale.EN_US
    count: int = Field(20, ge=1, le=200)
    context: str | None = Field(None, max_length=500)
    include_edge_cases: bool = True


class SynthesizedValue(StrictModel):
    value: str
    is_edge_case: bool = False
    note: str | None = None


class TextSynthesisResponse(StrictModel):
    values: list[SynthesizedValue]
    model_used: str
    fallback_used: bool = False