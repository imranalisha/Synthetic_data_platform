import datetime as dt
from enum import Enum
from typing import Any

from pydantic import Field, model_validator

from .common import (MAX_PREVIEW_ROWS, MAX_ROWS, Identifier, Locale, PrivacyMethod,
                     PrivacyRule, Rate, Seed, StrictModel)


class ColumnType(str, Enum):
    INTEGER = "integer"; FLOAT = "float"; DECIMAL = "decimal"; BOOLEAN = "boolean"
    STRING = "string"; TEXT = "text"; DATE = "date"; DATETIME = "datetime"; UUID = "uuid"
    CATEGORY = "category"
    FIRST_NAME = "first_name"; LAST_NAME = "last_name"; FULL_NAME = "name"
    EMAIL = "email"; PHONE = "phone"; ADDRESS = "address"; CITY = "city"
    COUNTRY = "country"; POSTCODE = "postcode"; COMPANY = "company"; JOB_TITLE = "job_title"
    IBAN = "iban"; CREDIT_CARD = "credit_card"; SSN = "ssn"; IP_ADDRESS = "ip_address"


NUMERIC_TYPES = {ColumnType.INTEGER, ColumnType.FLOAT, ColumnType.DECIMAL}


class ColumnSpec(StrictModel):
    name: Identifier
    type: ColumnType
    nullable: bool = True
    null_rate: Rate | None = Field(None, description="Overrides the table-level null_rate.")
    outlier_rate: Rate | None = Field(None, description="Numeric columns only.")
    min_value: float | None = None
    max_value: float | None = None
    decimal_places: int = Field(2, ge=0, le=8)
    date_start: dt.date | None = None
    date_end: dt.date | None = None
    categories: list[str] | None = Field(None, min_length=1, max_length=100)
    category_weights: list[float] | None = None
    unique: bool = False
    privacy: PrivacyRule = Field(default_factory=PrivacyRule)

    @model_validator(mode="after")
    def _check(self):
        if None not in (self.min_value, self.max_value) and self.min_value > self.max_value:
            raise ValueError("min_value must be <= max_value.")
        if None not in (self.date_start, self.date_end) and self.date_start > self.date_end:
            raise ValueError("date_start must be <= date_end.")
        if self.type == ColumnType.CATEGORY and not self.categories:
            raise ValueError("'categories' is required for type 'category'.")
        if self.category_weights is not None:
            if not self.categories or len(self.category_weights) != len(self.categories):
                raise ValueError("category_weights must match categories in length.")
            if any(w <= 0 for w in self.category_weights):
                raise ValueError("category_weights must be > 0.")
        if not self.nullable and (self.null_rate or 0) > 0:
            raise ValueError("null_rate must be 0/None on a non-nullable column.")
        if (self.outlier_rate or 0) > 0 and self.type not in NUMERIC_TYPES:
            raise ValueError("outlier_rate only applies to numeric columns.")
        if self.privacy.method == PrivacyMethod.NOISE and self.type not in NUMERIC_TYPES:
            raise ValueError("Noise privacy only applies to numeric columns.")
        return self


class TabularRequest(StrictModel):
    columns: list[ColumnSpec] = Field(min_length=1, max_length=200)
    row_count: int = Field(100, ge=1, le=MAX_ROWS)
    seed: Seed | None = Field(42, description="None = random; the resolved seed is echoed in responses.")
    locale: Locale = Locale.EN_US
    null_rate: Rate = 0.0
    outlier_rate: Rate = 0.0
    outlier_magnitude: float = Field(5.0, gt=1, description="Outliers sit this many std-devs from the mean.")

    @model_validator(mode="after")
    def _unique_names(self):
        names = [c.name.lower() for c in self.columns]
        if len(names) != len(set(names)):
            raise ValueError("Column names must be unique (case-insensitive).")
        return self


class TabularPreviewRequest(TabularRequest):
    row_count: int = Field(20, ge=1, le=MAX_PREVIEW_ROWS)


class TabularExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"


class TabularExportRequest(TabularRequest):
    format: TabularExportFormat = TabularExportFormat.CSV


class ColumnMeta(StrictModel):
    name: str
    type: ColumnType
    privacy_applied: PrivacyMethod


class TabularStats(StrictModel):
    null_counts: dict[str, int]
    outlier_counts: dict[str, int]
    generation_ms: float


class TabularResponse(StrictModel):
    columns: list[ColumnMeta]
    rows: list[dict[str, Any]]
    row_count: int
    seed: int
    stats: TabularStats