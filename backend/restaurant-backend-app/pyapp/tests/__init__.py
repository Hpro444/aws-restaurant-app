"""Test infrastructure for importing Lambda source packages during test runs."""

import sys
from pathlib import Path
from types import TracebackType

SOURCE_FOLDER = "src"


class ImportFromSourceContext:
    """Context manager that temporarily adds the source folder to sys.path.

    Necessary because the test root is not the syndicate project root but the
    folder where Lambdas are accumulated (SOURCE_FOLDER).
    """

    def __init__(self, source_folder: str = SOURCE_FOLDER) -> None:
        """Store the source folder name and verify the path exists."""
        self.source_folder = source_folder
        self.assert_source_path_exists()

    @property
    def project_path(self) -> Path:
        """Absolute path to the pyapp root directory."""
        return Path(__file__).parent.parent

    @property
    def source_path(self) -> Path:
        """Absolute path to the source folder containing Lambda packages."""
        return Path(self.project_path, self.source_folder)

    def assert_source_path_exists(self) -> None:
        """Exit with an error message if the source path does not exist."""
        source_path = self.source_path
        if not source_path.exists():
            print(f'Source path "{source_path}" does not exist.', file=sys.stderr)
            sys.exit(1)

    def _add_source_to_path(self) -> None:
        """Prepend the source path to sys.path if not already present."""
        source_path = str(self.source_path)
        if source_path not in sys.path:
            sys.path.append(source_path)

    def _remove_source_from_path(self) -> None:
        """Remove the source path from sys.path if present."""
        source_path = str(self.source_path)
        if source_path in sys.path:
            sys.path.remove(source_path)

    def __enter__(self) -> None:
        """Add the source path to sys.path on context entry."""
        self._add_source_to_path()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Remove the source path from sys.path on context exit."""
        self._remove_source_from_path()
