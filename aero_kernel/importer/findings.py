"""A finding: one thing wrong in the canon document, named by file, field and message."""

from pydantic import BaseModel, ConfigDict

__all__ = ["Finding"]


class Finding(BaseModel):
    """One problem the importer found; it is fixed in the canon document (ADR 0019, 0020).

    Attributes:
        file: The canon file the problem is in, relative to the canon directory.
        field: The field of that file; ``front matter``, ``document`` or ``entry`` where it is no
            single field.
        message: What is wrong, in plain words: no stack trace and no Python internals.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    file: str
    field: str
    message: str

    def __str__(self) -> str:
        """Render the finding as ``file: field: message``."""
        return f"{self.file}: {self.field}: {self.message}"
