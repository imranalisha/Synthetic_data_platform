from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_ROWS = 1_000_000
MAX_PREVIEW_ROWS = 500


class StrictModel(BaseModel):
    """Every contract rejects unknown fields, so typos fail loudly instead of silently."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


Seed = Annotated[int, Field(ge=0, le=2**32 - 1)]
Rate = Annotated[float, Field(ge=0.0, le=1.0)]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")]
# Money is Decimal end-to-end (serialised as a string in JSON) so reconciliation is exact.
Money = Annotated[Decimal, Field(max_digits=14, decimal_places=2)]
NonNegMoney = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class Locale(str, Enum):
    EN_US = "en_US"
    EN_GB = "en_GB"
    EN_IN = "en_IN"
    DE_DE = "de_DE"
    FR_FR = "fr_FR"
    ES_ES = "es_ES"
    IT_IT = "it_IT"
    PT_BR = "pt_BR"
    JA_JP = "ja_JP"


class PrivacyMethod(str, Enum):
    NONE = "none"
    MASK = "mask"
    HASH = "hash"
    NOISE = "noise"


class PrivacyRule(StrictModel):
    """Column-level privacy control. Only the fields for the chosen method are used."""
    method: PrivacyMethod = PrivacyMethod.NONE
    # mask
    mask_char: str = Field("*", min_length=1, max_length=1)
    mask_keep_first: int = Field(0, ge=0, le=32)
    mask_keep_last: int = Field(0, ge=0, le=32)
    # hash (salted, deterministic -> joins across tables still work)
    hash_algorithm: Literal["sha256", "sha512", "blake2b"] = "sha256"
    hash_salt: str | None = Field(None, max_length=128)
    hash_truncate: int | None = Field(None, ge=8, le=128)
    # differential-privacy style noise (numeric columns only)
    noise_mechanism: Literal["laplace", "gaussian"] = "laplace"
    noise_epsilon: float = Field(1.0, gt=0)
    noise_sensitivity: float = Field(1.0, gt=0)
    noise_delta: float | None = Field(None, gt=0, lt=1)

    @model_validator(mode="after")
    def _check(self):
        if (self.method == PrivacyMethod.NOISE and self.noise_mechanism == "gaussian"
                and self.noise_delta is None):
            raise ValueError("noise_delta is required for the gaussian mechanism.")
        return self


class ValidationIssue(StrictModel):
    loc: list[str | int]
    msg: str
    type: str


class ErrorResponse(StrictModel):
    code: str
    message: str
    issues: list[ValidationIssue] = []


class HealthResponse(StrictModel):
    status: Literal["ok"] = "ok"
    version: str
    llm_configured: bool