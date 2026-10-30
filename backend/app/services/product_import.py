import csv
from io import BytesIO, StringIO
from pathlib import PurePath
from typing import Any
from zipfile import BadZipFile, ZipFile
from xml.etree.ElementTree import ParseError

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


MAX_IMPORT_ROWS = 500
MAX_UNCOMPRESSED_XLSX_BYTES = 25 * 1024 * 1024
MAX_XLSX_ENTRIES = 1000
REQUIRED_COLUMNS = {"name", "price", "stock"}
ALLOWED_COLUMNS = REQUIRED_COLUMNS | {
    "description",
    "image_url",
    "category_id",
}


class ProductImportFormatError(ValueError):
    pass


def _column_indexes(values: tuple[Any, ...] | list[Any]) -> list[str]:
    columns = [
        str(value).strip().casefold() if value is not None else ""
        for value in values
    ]
    if not any(columns):
        raise ProductImportFormatError("The first row must contain column headers.")
    if any(not column for column in columns):
        raise ProductImportFormatError("Column headers cannot be blank.")
    if len(set(columns)) != len(columns):
        raise ProductImportFormatError("Column headers cannot be duplicated.")
    unknown = set(columns) - ALLOWED_COLUMNS
    if unknown:
        raise ProductImportFormatError(
            f"Unsupported column(s): {', '.join(sorted(unknown))}."
        )
    missing = REQUIRED_COLUMNS - set(columns)
    if missing:
        raise ProductImportFormatError(
            f"Missing required column(s): {', '.join(sorted(missing))}."
        )
    return columns


def _record_from_row(
    columns: list[str],
    values: tuple[Any, ...] | list[Any],
    row_number: int,
) -> tuple[int, dict[str, str | None]] | None:
    if len(values) > len(columns) and any(
        value is not None and str(value).strip()
        for value in values[len(columns) :]
    ):
        raise ProductImportFormatError(
            f"Row {row_number} has values beyond the column headers."
        )
    if not any(value is not None and str(value).strip() for value in values):
        return None

    record = {
        column: (
            str(values[index]).strip()
            if index < len(values) and values[index] is not None
            else None
        )
        for index, column in enumerate(columns)
    }
    return row_number, record


def _parse_csv(content: bytes) -> list[tuple[int, dict[str, str | None]]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ProductImportFormatError(
            "CSV files must use UTF-8 encoding."
        ) from exc

    try:
        rows = csv.reader(StringIO(text, newline=""))
        headers = next(rows, None)
        if headers is None:
            raise ProductImportFormatError("The CSV file is empty.")
        columns = _column_indexes(headers)
        records: list[tuple[int, dict[str, str | None]]] = []
        for row_number, values in enumerate(rows, start=2):
            record = _record_from_row(columns, values, row_number)
            if record is not None:
                records.append(record)
                if len(records) > MAX_IMPORT_ROWS:
                    raise ProductImportFormatError(
                        f"Files can contain at most {MAX_IMPORT_ROWS} product rows."
                    )
        return records
    except csv.Error as exc:
        raise ProductImportFormatError("The CSV file could not be parsed.") from exc


def _check_xlsx_archive(content: bytes) -> None:
    try:
        with ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
    except BadZipFile as exc:
        raise ProductImportFormatError("The XLSX file is not a valid workbook.") from exc

    if len(entries) > MAX_XLSX_ENTRIES:
        raise ProductImportFormatError("The XLSX file contains too many internal files.")
    if sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_XLSX_BYTES:
        raise ProductImportFormatError("The XLSX workbook is too large to process.")


def _parse_xlsx(content: bytes) -> list[tuple[int, dict[str, str | None]]]:
    _check_xlsx_archive(content)
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except (InvalidFileException, OSError, ParseError, ValueError, KeyError) as exc:
        raise ProductImportFormatError("The XLSX file could not be parsed.") from exc

    try:
        if not workbook.worksheets:
            raise ProductImportFormatError("The XLSX workbook has no worksheets.")
        rows = workbook.active.iter_rows(values_only=True)
        headers = next(rows, None)
        if headers is None:
            raise ProductImportFormatError("The first worksheet is empty.")
        columns = _column_indexes(headers)
        records: list[tuple[int, dict[str, str | None]]] = []
        for row_number, values in enumerate(rows, start=2):
            record = _record_from_row(columns, values, row_number)
            if record is not None:
                records.append(record)
                if len(records) > MAX_IMPORT_ROWS:
                    raise ProductImportFormatError(
                        f"Files can contain at most {MAX_IMPORT_ROWS} product rows."
                    )
        return records
    finally:
        workbook.close()


def parse_product_file(
    filename: str,
    content: bytes,
) -> list[tuple[int, dict[str, str | None]]]:
    suffix = PurePath(filename).suffix.casefold()
    if suffix == ".csv":
        return _parse_csv(content)
    if suffix == ".xlsx":
        return _parse_xlsx(content)
    raise ProductImportFormatError("Choose a CSV or XLSX file.")
