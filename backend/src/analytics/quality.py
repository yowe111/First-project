"""
quality.py — ОТЧЁТ О КАЧЕСТВЕ ДАННЫХ.

Это первое, что пользователь увидит после загрузки файла, и первое, чем
сервис доказывает, что действительно посмотрел в его данные, а не выдал
красивые картинки по шаблону.

Второе назначение модуля — честно сказать, что посчитать не получится.
Если истории три месяца, прогноз оттока на год будет выдумкой, и лучше
написать об этом прямо, чем показать график с уверенным видом.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from src.analytics.schema import AMOUNT, CUSTOMER_ID, ORDER_DATE, ORDER_ID

#: Пороги пригодности данных. Подобраны из практики: ниже них модели
#: формально обучатся, но доверять им нельзя.
MIN_MONTHS_FOR_COHORTS = 6
MIN_MONTHS_FOR_FORECAST = 12
MIN_CUSTOMERS = 300
MIN_REPEAT_RATE = 0.10

#: Неразрывный пробел: в русской типографике он разделяет разряды чисел
#: и, в отличие от обычного, не даёт числу разорваться на две строки.
_THIN_SPACE = "\u00a0"


def _num(value: float, digits: int = 0) -> str:
    """Отформатировать число с разделителями разрядов."""
    return f"{value:,.{digits}f}".replace(",", _THIN_SPACE)


@dataclass(slots=True)
class QualityReport:
    """Что мы поняли про загруженный файл."""

    rows_raw: int
    rows_used: int
    customers: int
    orders: int
    revenue: float

    period_from: datetime | None
    period_to: datetime | None
    months_covered: int

    duplicates_removed: int
    rows_dropped: int
    returns_count: int
    returns_amount: float

    repeat_customers: int
    repeat_rate: float

    #: Замечания, которые стоит показать человеку.
    warnings: list[str] = field(default_factory=list)
    #: Что из аналитики доступно на этих данных.
    available: dict[str, bool] = field(default_factory=dict)

    @property
    def average_order(self) -> float:
        return self.revenue / self.orders if self.orders else 0.0

    def summary(self) -> str:
        """Короткий человекочитаемый пересказ — удобно печатать в ноутбуке."""
        period = "неизвестен"
        if self.period_from and self.period_to:
            period = (
                f"{self.period_from:%d.%m.%Y} — {self.period_to:%d.%m.%Y} "
                f"({self.months_covered} мес.)"
            )
        return (
            f"Строк использовано: {_num(self.rows_used)} из {_num(self.rows_raw)}\n"
            f"Период: {period}\n"
            f"Клиентов: {_num(self.customers)}, заказов: {_num(self.orders)}\n"
            f"Выручка: {_num(self.revenue)}, "
            f"средний чек: {_num(self.average_order)}\n"
            f"Повторных клиентов: {_num(self.repeat_customers)} "
            f"({self.repeat_rate:.1%})"
        )


def drop_duplicates(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Убрать полные дубли строк.

    Чаще всего они появляются, когда выгрузку делают несколько раз и
    склеивают файлы. Возвращаем и очищенные данные, и число удалённых —
    это число пойдёт в отчёт.
    """
    before = len(frame)
    cleaned = frame.drop_duplicates()
    return cleaned.reset_index(drop=True), before - len(cleaned)


def trim_incomplete_tail(frame: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """Отрезать последний месяц, если он явно неполный.

    Выгрузку делают в середине месяца, и на графике это выглядит как
    обвал продаж. Считаем месяц неполным, если выручка в нём меньше
    половины медианной месячной.
    """
    if frame.empty:
        return frame, False

    monthly = frame.groupby(frame[ORDER_DATE].dt.to_period("M"))[AMOUNT].sum()
    if len(monthly) < 3:
        return frame, False

    last_period = monthly.index[-1]
    if monthly.iloc[-1] >= monthly.iloc[:-1].median() * 0.5:
        return frame, False

    trimmed = frame[frame[ORDER_DATE].dt.to_period("M") != last_period]
    return trimmed.reset_index(drop=True), True


def assess(frame: pd.DataFrame, *, rows_raw: int | None = None) -> QualityReport:
    """Собрать отчёт по уже приведённым к каноническому виду данным.

    `rows_raw` — сколько строк было в исходном файле до очистки. Если не
    передать, разница «потеряно строк» посчитается нулевой.
    """
    rows_used = len(frame)
    rows_raw = rows_raw if rows_raw is not None else rows_used

    if rows_used == 0:
        return QualityReport(
            rows_raw=rows_raw,
            rows_used=0,
            customers=0,
            orders=0,
            revenue=0.0,
            period_from=None,
            period_to=None,
            months_covered=0,
            duplicates_removed=0,
            rows_dropped=rows_raw,
            returns_count=0,
            returns_amount=0.0,
            repeat_customers=0,
            repeat_rate=0.0,
            warnings=["После очистки не осталось ни одной пригодной строки"],
            available={"rfm": False, "cohorts": False, "clv": False, "churn": False},
        )

    period_from = frame[ORDER_DATE].min()
    period_to = frame[ORDER_DATE].max()
    months = (
        (period_to.year - period_from.year) * 12
        + period_to.month
        - period_from.month
        + 1
    )

    # Возвраты приходят отрицательными суммами. Это не мусор: их нужно
    # вычитать из выручки клиента, иначе LTV окажется завышенным.
    returns = frame[frame[AMOUNT] < 0]

    # Если номера заказа нет, считаем заказом каждую строку.
    if ORDER_ID in frame.columns:
        orders = int(frame[ORDER_ID].nunique())
    else:
        orders = rows_used

    purchases_per_customer = frame.groupby(CUSTOMER_ID)[ORDER_DATE].nunique()
    customers = int(len(purchases_per_customer))
    repeat_customers = int((purchases_per_customer > 1).sum())
    repeat_rate = repeat_customers / customers if customers else 0.0

    report = QualityReport(
        rows_raw=rows_raw,
        rows_used=rows_used,
        customers=customers,
        orders=orders,
        revenue=float(frame[AMOUNT].sum()),
        period_from=period_from.to_pydatetime(),
        period_to=period_to.to_pydatetime(),
        months_covered=months,
        duplicates_removed=0,
        rows_dropped=max(rows_raw - rows_used, 0),
        returns_count=len(returns),
        returns_amount=float(returns[AMOUNT].sum()),
        repeat_customers=repeat_customers,
        repeat_rate=repeat_rate,
    )

    _fill_verdict(report)
    return report


def _fill_verdict(report: QualityReport) -> None:
    """Решить, что на этих данных можно считать, а что нельзя."""
    warnings: list[str] = []

    if report.months_covered < MIN_MONTHS_FOR_COHORTS:
        warnings.append(
            f"История короче {MIN_MONTHS_FOR_COHORTS} месяцев — "
            "когортный анализ будет почти пустым"
        )
    if report.months_covered < MIN_MONTHS_FOR_FORECAST:
        warnings.append(
            f"Для прогноза нужно хотя бы {MIN_MONTHS_FOR_FORECAST} месяцев "
            f"истории, сейчас {report.months_covered}"
        )
    if report.customers < MIN_CUSTOMERS:
        warnings.append(
            f"Клиентов меньше {MIN_CUSTOMERS} — оценки будут неустойчивыми"
        )
    if report.repeat_rate < MIN_REPEAT_RATE:
        warnings.append(
            f"Повторных покупок почти нет ({report.repeat_rate:.1%}). "
            "Модели удержания бессмысленны: клиенты приходят по одному разу"
        )
    if report.rows_dropped:
        share = report.rows_dropped / report.rows_raw
        warnings.append(
            f"В расчёт не попало строк: {report.rows_dropped} ({share:.1%}) — "
            "без обязательных полей, дубли и неполный последний месяц"
        )

    report.warnings = warnings

    # Деградируем ступенчато: чего не хватило — то и недоступно,
    # остальное считаем как обычно.
    enough_customers = report.customers >= MIN_CUSTOMERS
    report.available = {
        "rfm": True,
        "cohorts": report.months_covered >= MIN_MONTHS_FOR_COHORTS,
        "clv": (
            report.months_covered >= MIN_MONTHS_FOR_FORECAST
            and report.repeat_rate >= MIN_REPEAT_RATE
        ),
        "churn": (
            report.months_covered >= MIN_MONTHS_FOR_FORECAST
            and report.repeat_rate >= MIN_REPEAT_RATE
            and enough_customers
        ),
    }
