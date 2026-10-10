"""
Тесты аналитического ядра.

Данные синтетические и заданы вручную: так заранее известен правильный
ответ, и тест проверяет расчёт, а не повторяет его.

pandas лежит в необязательной группе зависимостей, поэтому в окружении
без неё тесты пропускаются, а не падают.
"""

import pytest

pd = pytest.importorskip("pandas")

from src.analytics import guess_mapping, normalize  # noqa: E402
from src.analytics.ingest import IngestError, normalize_name  # noqa: E402
from src.analytics.quality import (  # noqa: E402
    assess,
    drop_duplicates,
    trim_incomplete_tail,
)
from src.analytics.schema import AMOUNT, CUSTOMER_ID, ORDER_DATE  # noqa: E402


# ── Распознавание колонок ─────────────────────────────────────────────


def test_normalize_name_ignores_case_and_separators():
    assert normalize_name("Дата заказа") == normalize_name("дата_заказа")
    assert normalize_name("Customer ID") == "customerid"


def test_guess_mapping_finds_russian_columns():
    frame = pd.DataFrame(
        {
            "Дата заказа": ["01.02.2024"],
            "Код клиента": ["A-1"],
            "Сумма, руб": ["1 200,50"],
            "Комментарий": ["что-то своё"],
        }
    )

    mapping = guess_mapping(frame)

    assert mapping.order_date == "Дата заказа"
    assert mapping.customer_id == "Код клиента"
    assert mapping.amount == "Сумма, руб"
    assert mapping.is_valid
    # Лишнюю колонку не выдумываем, а показываем человеку.
    assert mapping.unmapped == ["Комментарий"]


def test_mapping_accepts_quantity_and_price_instead_of_amount():
    """Так устроена Online Retail II и большинство выгрузок из 1С."""
    frame = pd.DataFrame(
        {
            "InvoiceDate": ["2024-01-01"],
            "Customer ID": ["17850"],
            "Quantity": [3],
            "Price": [2.5],
        }
    )

    mapping = guess_mapping(frame)

    assert mapping.is_valid
    assert mapping.missing_required == []


def test_mapping_without_customer_is_invalid():
    frame = pd.DataFrame({"Дата": ["2024-01-01"], "Сумма": [100]})

    mapping = guess_mapping(frame)

    assert not mapping.is_valid
    assert CUSTOMER_ID in mapping.missing_required


# ── Приведение к каноническому виду ───────────────────────────────────


def test_normalize_parses_messy_values():
    frame = pd.DataFrame(
        {
            "Дата": ["01.02.2024", "03.02.2024"],
            "Клиент": ["A-1", "A-2"],
            "Сумма": ["1 200,50", "900"],
        }
    )

    result = normalize(frame, guess_mapping(frame))

    # Русская дата читается как день-месяц-год, а не месяц-день-год.
    assert result[ORDER_DATE].iloc[0].month == 2
    assert result[ORDER_DATE].iloc[0].day == 1
    # Пробел-разделитель разрядов и запятая вместо точки не мешают.
    assert result[AMOUNT].iloc[0] == pytest.approx(1200.50)


def test_normalize_computes_amount_from_quantity_and_price():
    frame = pd.DataFrame(
        {
            "InvoiceDate": ["2024-01-01"],
            "Customer ID": ["17850"],
            "Quantity": [3],
            "Price": [2.5],
        }
    )

    result = normalize(frame, guess_mapping(frame))

    assert result[AMOUNT].iloc[0] == pytest.approx(7.5)


def test_normalize_keeps_customer_id_as_string():
    """После Excel номер клиента приходит как 17850.0 — это тот же человек."""
    frame = pd.DataFrame(
        {
            "Дата": ["2024-01-01", "2024-02-01"],
            "Клиент": [17850.0, 17850],
            "Сумма": [100, 200],
        }
    )

    result = normalize(frame, guess_mapping(frame))

    assert result[CUSTOMER_ID].nunique() == 1


def test_normalize_drops_rows_without_required_fields():
    frame = pd.DataFrame(
        {
            "Дата": ["2024-01-01", "не дата", "2024-03-01"],
            "Клиент": ["A-1", "A-2", None],
            "Сумма": [100, 200, 300],
        }
    )

    result = normalize(frame, guess_mapping(frame))

    assert len(result) == 1


def test_normalize_requires_mapping():
    frame = pd.DataFrame({"Дата": ["2024-01-01"], "Сумма": [100]})

    with pytest.raises(IngestError):
        normalize(frame, guess_mapping(frame))


# ── Качество данных ───────────────────────────────────────────────────


def _transactions(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            ORDER_DATE: pd.to_datetime([r[0] for r in rows]),
            CUSTOMER_ID: [r[1] for r in rows],
            AMOUNT: [r[2] for r in rows],
        }
    )


def test_drop_duplicates_counts_removed():
    frame = _transactions(
        [
            ("2024-01-01", "A", 100.0),
            ("2024-01-01", "A", 100.0),
            ("2024-01-02", "B", 200.0),
        ]
    )

    cleaned, removed = drop_duplicates(frame)

    assert removed == 1
    assert len(cleaned) == 2


def test_assess_counts_repeat_customers_and_returns():
    frame = _transactions(
        [
            ("2024-01-10", "A", 100.0),
            ("2024-02-10", "A", 150.0),   # A вернулся
            ("2024-01-15", "B", 200.0),
            ("2024-03-01", "C", -50.0),   # возврат
        ]
    )

    report = assess(frame, rows_raw=5)

    assert report.customers == 3
    assert report.repeat_customers == 1
    assert report.returns_count == 1
    assert report.returns_amount == pytest.approx(-50.0)
    # Возврат вычитается из выручки, а не игнорируется.
    assert report.revenue == pytest.approx(400.0)
    # Одна строка исходного файла не дошла до расчёта.
    assert report.rows_dropped == 1


def test_assess_blocks_forecast_on_short_history():
    frame = _transactions(
        [("2024-01-10", "A", 100.0), ("2024-02-10", "A", 150.0)]
    )

    report = assess(frame)

    assert report.available["rfm"] is True
    assert report.available["churn"] is False
    assert any("прогноз" in w.lower() for w in report.warnings)


def test_assess_on_empty_frame_does_not_crash():
    report = assess(_transactions([]), rows_raw=10)

    assert report.rows_used == 0
    assert report.available["rfm"] is False
    assert report.warnings


def test_trim_incomplete_tail_removes_half_empty_last_month():
    rows = [(f"2024-{month:02d}-10", "A", 1000.0) for month in range(1, 7)]
    rows.append(("2024-07-01", "A", 10.0))  # месяц только начался

    frame = _transactions(rows)
    trimmed, was_trimmed = trim_incomplete_tail(frame)

    assert was_trimmed
    assert trimmed[ORDER_DATE].max().month == 6
