import json
from os import path
from typing import Callable

import aiocron
import aiofiles  # type: ignore

from app.commons import time
from app.register import model, ports, adapters


class Sync:
    def __init__(
        self, db: ports.Repository, in_memory_repo: adapters.InMemoryRepo
    ) -> None:
        self.db = db
        self.in_memory_repo = in_memory_repo

    async def sync_bills(self) -> None:
        # load daily shifts from file
        async with aiofiles.open("daily_shifts.json", "r") as file:
            data_loaded = json.loads(await file.read())
            daily_shifts = {
                int(k): model.DailyShift.parse_obj(v) for k, v in data_loaded.items()
            }

        last_bill_id = await self._load_bill_id()

        # compare last bill from daily shifts with last bill id
        current_daily_shift = daily_shifts.get(time.get_posix_time_until_day(), None)
        if not current_daily_shift:
            return
        last_bill = current_daily_shift.bills[-1]
        if last_bill.id != last_bill_id:
            # update shift to dynamo db
            await self.db.save(daily_shift=current_daily_shift)
            async with aiofiles.open("last_bill_id.json", "w") as file:
                await file.write(json.dumps({"last_id": last_bill.id}))

    @staticmethod
    async def _load_bill_id() -> str:
        # load last bill id from file
        if not path.exists("last_bill_id.json"):
            async with aiofiles.open("last_bill_id.json", "w") as file:
                await file.write(json.dumps({"last_id": "no_id"}))
            return "no_id"
        async with aiofiles.open("last_bill_id.json", "r+") as file:
            content = await file.read()
            if not content:
                last_bill_id = "no_id"
                await file.write(json.dumps({"last_id": last_bill_id}))
            else:
                last_bill_id = json.loads(content)["last_id"]
            return last_bill_id

    async def clean_daily_shifts(self) -> None:
        # get current id shift
        current_id_shift = time.get_posix_time_until_day()
        # load daily shifts from file
        async with aiofiles.open("daily_shifts.json", "r") as file:
            data_loaded = json.loads(await file.read())
            daily_shifts = {
                int(k): model.DailyShift.parse_obj(v) for k, v in data_loaded.items()
            }
        if not daily_shifts.get(current_id_shift):
            return
        # clean daily shifts
        daily_shifts = {current_id_shift: daily_shifts[current_id_shift]}
        # write daily shifts to file
        async with aiofiles.open("daily_shifts.json", "w") as file:
            serialized_daily_shifts = {
                k: v.model_dump() for k, v in daily_shifts.items()
            }
            await file.write(json.dumps(serialized_daily_shifts))
        self.in_memory_repo.clean_daily_shifts()


async def set_up_sync_process(
    sync_bills: Callable, clean_daily_shifts: Callable, time_sync: int, time_clean: int
) -> None:
    time_to_sync = f"* * * * * */{time_sync}"
    time_to_clean = f"* * * * * */{time_clean}"
    aiocron.crontab(time_to_sync, func=sync_bills, start=True)
    aiocron.crontab(time_to_clean, func=clean_daily_shifts, start=True)


# asyncio.get_event_loop().run_forever()
