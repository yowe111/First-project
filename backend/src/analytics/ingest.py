"""
ingest.py — ЧТЕНИЕ И ПРИВЕДЕНИЕ ФАЙЛА К КАНОНИЧЕСКОМУ ВИДУ.

Самый недооценённый модуль продукта. Выглядит скучно, но именно он решает,
дойдёт ли пользователь до дашборда: файлы приходят в cp1251, с точкой с
запятой вместо запятой, с суммами вида «1 234,50» и датами в пяти форматах.
Пока это не разобрано, никакая модель не нужна.

Порядок работы:

    read_table()  →  guess_mapping()  →  [человек правит]  →  normalize()

На выходе `normalize` даёт DataFrame с колонками из `schema.py`, пригодный
для любого аналитического модуля.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.analytics.schema import (
    ALL_FIELDS,
    AMOUNT,
    COLUMN_SYNONYMS,
    CUSTOMER_ID,
    ORDER_DATE,
    QUANTITY,
    UNIT_PRICE,
    ColumnMapping,
)


class IngestError(Exception):
    """Файл не удалось прочитать или в нём нет нужных колонок."""


# ── Чтение файла ──────────────────────────────────────────────────────

#: Кодировки в порядке убывания вероятности. cp1251 — наследие Excel из
#: русской локали, оно встречается до сих пор.
_ENCODINGS = ("utf-8-sig", "cp1251", "latin-1")


def read_table(path: str | Path) -> pd.DataFrame:
    """Прочитать CSV, Excel или Parquet, не зная заранее формата."""
    path = Path(path)
    if not path.exists():
        raise IngestError(f"Файл не найден: {path}")

    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    return _read_csv(path)


def _read_csv(path: Path) -> pd.DataFrame:
    """CSV с подбором кодировки и автоопределением разделителя.

    `sep=None` вместе с движком python включает «вынюхивание» разделителя:
    pandas сам поймёт, запятая там, точка с запятой или табуляция.
    """
    last_error: Exception | None = None
    for encoding in _ENCODINGS:
        try:
            return pd.read_csv(path, sep=None, engine="python", encoding=encoding)
        except (UnicodeDecodeError, pd.errors.ParserError) as error:
            last_error = error
    raise IngestError(f"Не удалось прочитать CSV: {last_error}")


# ── Распознавание колонок ─────────────────────────────────────────────


def normalize_name(name: str) -> str:
    """Привести имя колонки к виду, пригодному для сравнения.

    «Дата заказа», «дата_заказа» и «ДатаЗаказа» должны считаться одним
    и тем же именем, поэтому убираем регистр и всё, кроме букв и цифр.
    """
    return re.sub(r"[^0-9a-zа-яё]", "", str(name).lower())


def guess_mapping(frame: pd.DataFrame) -> ColumnMapping:
    """Предположить, какая колонка файла чему соответствует.

    Распознавание идёт в два прохода. Сначала ищем точные совпадения со
    словарём синонимов, и только потом — колонки, которые с синонима
    начинаются: «Сумма, руб» и «Дата заказа, МСК» должны находиться, но
    не ценой ошибки там, где есть точное совпадение.

    Это именно предположение: результат показывается человеку, и он может
    его поправить. Автоматика должна экономить время, а не решать за него.
    """
    mapping = ColumnMapping()
    taken: set[str] = set()
    normalized = {column: normalize_name(column) for column in frame.columns}

    def claim(canonical: str, matches) -> None:
        if getattr(mapping, canonical) is not None:
            return
        for column in frame.columns:
            if column not in taken and matches(normalized[column]):
                setattr(mapping, canonical, column)
                taken.add(column)
                return

    for canonical, synonyms in COLUMN_SYNONYMS.items():
        claim(canonical, lambda name, s=synonyms: name in s)

    for canonical, synonyms in COLUMN_SYNONYMS.items():
        claim(canonical, lambda name, s=synonyms: name.startswith(s))

    mapping.unmapped = [c for c in frame.columns if c not in taken]
    return mapping


# ── Приведение к каноническому виду ───────────────────────────────────

#: Денежные значения приходят как «1 234,50», «1 234.50 ₽», «(500)».
#: Оставляем только цифры, точку и минус.
_NUMERIC_GARBAGE = re.compile(r"[^\d,.\-]")


def _to_number(series: pd.Series) -> pd.Series:
    """Превратить колонку в числа, пережив пробелы-разделители и запятые."""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype("float64")

    cleaned = (
        series.astype("string")
        .str.replace(_NUMERIC_GARBAGE, "", regex=True)
        # Запятая как десятичный разделитель — только если точки нет.
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def normalize(
    frame: pd.DataFrame,
    mapping: ColumnMapping,
    *,
    drop_invalid: bool = True,
) -> pd.DataFrame:
    """Собрать канонический DataFrame по сопоставлению колонок.

    Что здесь происходит:

    1. колонки переименовываются в наши имена;
    2. дата и числа приводятся к нужным типам;
    3. если суммы нет, но есть количество и цена — сумма считается;
    4. строки без даты, клиента или суммы отбрасываются (их нельзя
       использовать, а тихо подставлять нули — значит врать в отчёте).

    Удаление строк не прячем: сколько именно выброшено, посчитает
    `quality.assess` и покажет пользователю.
    """
    if not mapping.is_valid:
        raise IngestError(
            "Не хватает обязательных колонок: "
            + ", ".join(mapping.missing_required)
        )

    pairs = mapping.as_dict()
    result = pd.DataFrame(
        {name: frame[source] for name, source in pairs.items()}
    )

    result[ORDER_DATE] = pd.to_datetime(
        result[ORDER_DATE],
        errors="coerce",
        # Для «01.02.2024» в русских выгрузках первым идёт день.
        dayfirst=True,
    )

    # Идентификатор клиента — всегда строка. Иначе 12345 и 12345.0
    # станут разными клиентами после чтения Excel.
    result[CUSTOMER_ID] = (
        result[CUSTOMER_ID]
        .astype("string")
        .str.strip()
        .str.removesuffix(".0")
    )
    result.loc[result[CUSTOMER_ID].isin(["", "nan", "None"]), CUSTOMER_ID] = pd.NA

    for column in (AMOUNT, QUANTITY, UNIT_PRICE):
        if column in result.columns:
            result[column] = _to_number(result[column])

    if AMOUNT not in result.columns:
        # Построчная выгрузка товаров: сумма = количество × цена.
        result[AMOUNT] = result[QUANTITY] * result[UNIT_PRICE]

    if drop_invalid:
        result = result.dropna(subset=[ORDER_DATE, CUSTOMER_ID, AMOUNT])

    # Приводим порядок колонок к объявленному в schema.py — так отчёты
    # и превью везде выглядят одинаково.
    ordered = [c for c in ALL_FIELDS if c in result.columns]
    return result[ordered].reset_index(drop=True)
