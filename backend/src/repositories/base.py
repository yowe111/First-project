"""
base.py — БАЗОВЫЙ РЕПОЗИТОРИЙ.

**Что такое репозиторий.** Это единственное место в приложении, где пишутся
запросы к базе. Всё остальное работает с ним как с коллекцией объектов:
«дай пользователя с таким id», «посчитай, сколько подходит под фильтр».

**Зачем он нужен.** Раньше `select(...)` жил прямо в обработчиках
эндпоинтов. Это создаёт три проблемы:

1. Один и тот же запрос копируется по роутерам, и при изменении схемы его
   приходится чинить в пяти местах.
2. Бизнес-правило («чужую заметку не показывать») перемешано с техникой
   («как построить SQL»), и читать такой код тяжело.
3. Логику нельзя протестировать, не подняв веб-приложение целиком.

**Что даёт `Generic[ModelT]`.** Базовый класс написан один раз для любой
таблицы. Наследник указывает, с какой моделью работает:

    class UserRepository(BaseRepository[User]):
        model = User
        default_order_by = (User.id,)

После этого `await repo.get_by_id(1)` возвращает именно `User | None`, и
редактор подсказывает его поля. Повторять `get_by_id`, `count`, `paginate`
в каждом репозитории не нужно.

**Кто отвечает за транзакцию.** Методы `add` и `delete` только готовят
изменения — в базу они ещё не записаны. Решение «зафиксировать» принимает
сервис, вызывая `commit()`. Так одна бизнес-операция остаётся одной
транзакцией: если на середине что-то пойдёт не так, в базе не останется
половины изменений.
"""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from src.models.base import Base

# TypeVar — «переменная типа». Она запоминает, с какой моделью работает
# конкретный репозиторий, и подставляет её в возвращаемые значения.
ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Общие операции чтения и записи для любой таблицы."""

    # Эти два поля обязан задать каждый наследник.
    model: type[ModelT]

    # Сортировка по умолчанию. Это именно кортеж, и на то две причины.
    #
    # Первая — техническая. Колонка модели (`User.id`) — дескриптор: при
    # обращении через `self.default_order_by` SQLAlchemy решит, что
    # репозиторий и есть строка таблицы, и упадёт с UnmappedInstanceError.
    # Внутри кортежа колонка остаётся обычным значением.
    #
    # Вторая — практическая: так можно задать сортировку по нескольким
    # полям, например `(Note.created_at.desc(), Note.id.desc())`.
    default_order_by: tuple[Any, ...]

    def __init__(self, session: AsyncSession) -> None:
        # Сессия приходит снаружи, репозиторий её не создаёт.
        # Благодаря этому несколько репозиториев в одном запросе работают
        # в общей транзакции и видят изменения друг друга.
        self.session = session

    # ── Чтение ────────────────────────────────────────────────────────

    def select(self) -> Select[tuple[ModelT]]:
        """Заготовка запроса. Наследник может переопределить её, чтобы,
        например, всегда подгружать связанные объекты или отсекать
        мягко удалённые строки.
        """
        return select(self.model)

    async def get_by_id(self, obj_id: int) -> ModelT | None:
        """Найти строку по первичному ключу. Нет такой — `None`."""
        # session.get() сначала смотрит в уже загруженные объекты
        # и идёт в базу, только если там пусто.
        return await self.session.get(self.model, obj_id)

    async def find_one(self, *conditions: ColumnElement[bool]) -> ModelT | None:
        """Первая строка, подходящая под условия, либо `None`."""
        result = await self.session.execute(self.select().where(*conditions))
        return result.scalars().first()

    async def exists(self, *conditions: ColumnElement[bool]) -> bool:
        """Есть ли хоть одна подходящая строка.

        Дешевле, чем `find_one`: база останавливается на первом совпадении
        и не передаёт сам объект.
        """
        stmt = select(1).select_from(self.model).where(*conditions).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar() is not None

    async def count(self, *conditions: ColumnElement[bool]) -> int:
        """Сколько всего строк подходит под условия."""
        stmt = select(func.count()).select_from(self.model).where(*conditions)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def find_many(
        self,
        *conditions: ColumnElement[bool],
        limit: int | None = None,
        offset: int | None = None,
        order_by: Any | None = None,
    ) -> Sequence[ModelT]:
        """Список строк с необязательными ограничением и сдвигом.

        Метод называется `find_many`, а не `list`: имя `list` внутри тела
        класса перекрыло бы встроенный тип, и аннотации вида
        `tuple[list[ModelT], int]` перестали бы работать.
        """
        ordering = self.default_order_by if order_by is None else (order_by,)
        stmt = self.select().where(*conditions).order_by(*ordering)
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def paginate(
        self,
        *conditions: ColumnElement[bool],
        limit: int,
        offset: int,
        order_by: Any | None = None,
    ) -> tuple[list[ModelT], int]:
        """Страница плюс общее число подходящих строк.

        Возвращаются именно два значения: `total` считается по тем же
        условиям, но без `limit`, иначе клиент не сможет показать, сколько
        всего страниц. Это самая частая операция в списках, поэтому она
        живёт в базовом классе.
        """
        total = await self.count(*conditions)
        items = await self.find_many(
            *conditions,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )
        return list(items), total

    # ── Запись ────────────────────────────────────────────────────────

    def add(self, instance: ModelT) -> ModelT:
        """Поставить объект в очередь на сохранение. В базу ещё не пишет."""
        self.session.add(instance)
        return instance

    def create(self, **values: Any) -> ModelT:
        """Собрать новый объект модели и поставить его в очередь."""
        return self.add(self.model(**values))

    async def delete(self, instance: ModelT) -> None:
        """Пометить объект на удаление. Реально удалится при `commit`."""
        await self.session.delete(instance)

    # ── Транзакция ────────────────────────────────────────────────────

    async def commit(self) -> None:
        """Зафиксировать все накопленные изменения."""
        await self.session.commit()

    async def refresh(self, instance: ModelT) -> None:
        """Перечитать объект из базы.

        Нужно после вставки, чтобы увидеть поля, которые проставила сама
        база: `id` и `created_at`.
        """
        await self.session.refresh(instance)

    async def save(self, instance: ModelT) -> ModelT:
        """Короткий путь: зафиксировать и сразу перечитать.

        Подходит, когда операция меняет один объект. Если в рамках одного
        действия меняются несколько таблиц, лучше вызвать `commit()` один
        раз в конце, а не `save()` на каждую.
        """
        await self.commit()
        await self.refresh(instance)
        return instance
