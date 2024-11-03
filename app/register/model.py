import time
from typing import cast

import pydantic
import shortuuid

from app.commons import time as tm


def generate_uuid() -> str:
    return cast(str, shortuuid.uuid())


# value objects
class Item(pydantic.BaseModel):
    id: str = pydantic.Field(default=1)
    price: float
    quantity: float


# entities
class Bill(pydantic.BaseModel):
    id: str = pydantic.Field(default_factory=generate_uuid)
    created_at: int = pydantic.Field(default_factory=tm.now)
    items: list[Item]
    total: float

    def add_item(self, item: Item) -> None:
        self.items.append(item)
        self.total += item.price

    def remove_last_item(self) -> None:
        if self.items:
            item = self.items.pop()
            self.total -= item.price

    def get_total(self) -> float:
        return self.total

    def get_date_in_isoformat(self) -> str:
        # hour and minutes
        return time.strftime(
            "%H:%M:%S", time.localtime(self.created_at // 1_000_000_000)
        )


# Aggregates
class DailyShift(pydantic.BaseModel):
    id: int = pydantic.Field(default_factory=tm.get_posix_time_until_day)
    bills: list[Bill]
    total: float

    def add_bill(self, bill: Bill) -> None:
        self.bills.append(bill)
        self.total += bill.total

    def get_total(self) -> float:
        return self.total
