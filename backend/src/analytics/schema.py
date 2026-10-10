"""
schema.py — КОНТРАКТ ВХОДНЫХ ДАННЫХ.

Весь продукт держится на одном соглашении: как бы ни назывались колонки в
файле пользователя, внутри системы они приводятся к фиксированному набору
имён. Дальше ни один модуль аналитики не задумывается, откуда пришли
данные — из 1С, Shopify или Excel, набитого вручную.

Этот файл — единственный источник правды об этих именах. Если понадобится
новое поле, добавлять его нужно здесь, а не в десяти местах.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Канонические имена колонок ────────────────────────────────────────

ORDER_DATE = "order_date"
CUSTOMER_ID = "customer_id"
AMOUNT = "amount"
ORDER_ID = "order_id"
QUANTITY = "quantity"
UNIT_PRICE = "unit_price"
CATEGORY = "category"
CHANNEL = "channel"

#: Без этих трёх колонок посчитать нельзя ничего.
REQUIRED_FIELDS: tuple[str, ...] = (ORDER_DATE, CUSTOMER_ID, AMOUNT)

#: Эти колонки необязательны, но каждая добавляет разрез в отчёт.
OPTIONAL_FIELDS: tuple[str, ...] = (
    ORDER_ID,
    QUANTITY,
    UNIT_PRICE,
    CATEGORY,
    CHANNEL,
)

ALL_FIELDS: tuple[str, ...] = REQUIRED_FIELDS + OPTIONAL_FIELDS


#: Подсказки для автоматического распознавания колонок.
#: Ключ — каноническое имя, значение — варианты, которые встречаются в
#: выгрузках. Сравнение идёт по «очищенному» имени: нижний регистр,
#: без пробелов, дефисов и подчёркиваний (см. `ingest.normalize_name`).
COLUMN_SYNONYMS: dict[str, tuple[str, ...]] = {
    ORDER_DATE: (
        "orderdate", "invoicedate", "date", "datetime", "createdat",
        "дата", "датазаказа", "датапокупки", "датадокумента",
    ),
    CUSTOMER_ID: (
        "customerid", "customer", "clientid", "client", "userid", "buyerid",
        "клиент", "идклиента", "кодклиента", "покупатель", "контрагент",
    ),
    AMOUNT: (
        "amount", "revenue", "total", "totalprice", "sum", "sales", "gmv",
        "сумма", "выручка", "итого", "суммазаказа", "стоимость",
    ),
    ORDER_ID: (
        "orderid", "invoiceno", "invoice", "order", "transactionid", "receipt",
        "заказ", "номерзаказа", "чек", "номерчека", "документ",
    ),
    QUANTITY: (
        "quantity", "qty", "count", "units",
        "количество", "колво", "штук",
    ),
    UNIT_PRICE: (
        "unitprice", "price", "priceperunit",
        "цена", "ценазаединицу", "ценаштуки",
    ),
    CATEGORY: (
        "category", "productcategory", "group", "productgroup",
        "категория", "группа", "группатоваров", "товарнаягруппа",
    ),
    CHANNEL: (
        "channel", "source", "saleschannel", "store", "shop",
        "канал", "источник", "магазин", "точка",
    ),
}


@dataclass(slots=True)
class ColumnMapping:
    """Соответствие «наше имя → колонка в файле пользователя».

    Объект заполняется автоматически при загрузке, а потом пользователь
    поправляет его в интерфейсе. Именно он сохраняется в базу вместе с
    датасетом, чтобы при повторном расчёте не спрашивать то же самое.
    """

    order_date: str | None = None
    customer_id: str | None = None
    amount: str | None = None
    order_id: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    category: str | None = None
    channel: str | None = None

    #: Колонки файла, которым не нашлось пары. Полезно показать человеку:
    #: вдруг нужное поле просто названо непривычно.
    unmapped: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, str]:
        """Только заполненные пары — в виде `{наше_имя: имя_в_файле}`."""
        return {
            name: source
            for name, source in (
                (ORDER_DATE, self.order_date),
                (CUSTOMER_ID, self.customer_id),
                (AMOUNT, self.amount),
                (ORDER_ID, self.order_id),
                (QUANTITY, self.quantity),
                (UNIT_PRICE, self.unit_price),
                (CATEGORY, self.category),
                (CHANNEL, self.channel),
            )
            if source is not None
        }

    @property
    def missing_required(self) -> list[str]:
        """Каких обязательных полей не хватает.

        Сумму можно не присылать, если есть количество и цена за единицу:
        в Online Retail II и во многих выгрузках из 1С именно так.
        """
        mapped = self.as_dict()
        missing = [name for name in REQUIRED_FIELDS if name not in mapped]

        if AMOUNT in missing and QUANTITY in mapped and UNIT_PRICE in mapped:
            missing.remove(AMOUNT)

        return missing

    @property
    def is_valid(self) -> bool:
        return not self.missing_required
