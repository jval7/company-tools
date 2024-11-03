import app.commons.time
from app.commons import time
from app.register import ports, model


class Register:
    def __init__(self, repo: ports.Repository):
        self.repo = repo
        self._current_bill: model.Bill = model.Bill(items=[], total=0)
        self._new_bill_required = True

    def _create_bill(self) -> None:
        self._current_bill = model.Bill(items=[], total=0)

    def add_item(self, price: float, id_: str = "1", quantity: float = 1) -> None:
        if self._new_bill_required:
            self._create_bill()
            self._new_bill_required = False
        item = model.Item(id=id_, price=price, quantity=quantity)
        self._current_bill.add_item(item)

    def remove_last_item(self) -> None:
        self._current_bill.remove_last_item()

    async def save_bill(self) -> None:
        if self._new_bill_required:
            return
        daily_shift = await self.repo.get(app.commons.time.get_posix_time_until_day())
        if daily_shift is None:
            daily_shift = model.DailyShift(bills=[], total=0)
        daily_shift.add_bill(self._current_bill)
        await self.repo.save(daily_shift=daily_shift)
        self._new_bill_required = True

    def get_current_bill(self) -> model.Bill | None:
        if not self._current_bill:
            return None
        return self._current_bill

    async def get_daily_shift(self) -> model.DailyShift:
        daily_shift = await self.repo.get(time.get_posix_time_until_day())
        if not daily_shift:
            daily_shift = model.DailyShift(bills=[], total=0)
        return daily_shift
