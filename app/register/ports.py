import abc

from app.register import model


class Repository(abc.ABC):
    @abc.abstractmethod
    async def get(self, id_: int) -> model.DailyShift | None:
        pass

    @abc.abstractmethod
    async def save(self, daily_shift: model.DailyShift) -> None:
        pass
