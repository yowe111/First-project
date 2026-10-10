"""
analytics — ЯДРО ПРОДУКТА.

Здесь живёт вся предметная математика: подготовка данных, сегментация,
когорты, прогноз LTV и оттока.

**Главное правило слоя.** Ни один модуль отсюда не знает про HTTP, базу
данных и пользователей. На входе — DataFrame и параметры, на выходе —
DataFrame или объект с результатом. Никаких `session`, `request`, `await`.

Зачем так строго:

- любой модуль можно запустить в ноутбуке на реальных данных и сразу
  увидеть результат;
- тесты пишутся на синтетике и идут за секунды, без Docker и Postgres;
- тяжёлый расчёт легко унести в фоновый процесс — он самодостаточен.

Состояние модулей:

    schema.py   готов    контракт входных данных
    ingest.py   готов    чтение файла и приведение к контракту
    quality.py  готов    отчёт о данных и что на них можно считать
    rfm.py      впереди  сегментация по давности, частоте и сумме
    cohorts.py  впереди  удержание по когортам
    btyd.py     впереди  BG/NBD и Gamma-Gamma, прогноз LTV
    churn.py    впереди  модель оттока и объяснение причин
    pipeline.py впереди  оркестратор: файл на входе, полный отчёт на выходе

Модули «впереди» пишутся в ноутбуках (папка `notebooks/`) и переезжают
сюда, когда перестают меняться каждый вечер.
"""

from src.analytics.ingest import IngestError, guess_mapping, normalize, read_table
from src.analytics.quality import QualityReport, assess, drop_duplicates
from src.analytics.schema import ColumnMapping

__all__ = [
    "ColumnMapping",
    "IngestError",
    "QualityReport",
    "assess",
    "drop_duplicates",
    "guess_mapping",
    "normalize",
    "read_table",
]
