import asyncio
import json
from decimal import Decimal

import boto3

from app.commons import time
from app.register import ports, model

lock = asyncio.Lock()


class InMemoryRepo(ports.Repository):
    def __init__(self, path_file: str = "daily_shifts.json") -> None:
        self._daily_shifts = self._load_daily_shifts_from_file(path_file)

    @staticmethod
    def _load_daily_shifts_from_file(path_file: str) -> dict[int, model.DailyShift]:
        try:
            with open(path_file, "r") as file:
                data_loaded = json.load(file)
                if not data_loaded:
                    return {}
                data_loaded = {
                    int(k): model.DailyShift.parse_obj(v)
                    for k, v in data_loaded.items()
                }
                return data_loaded  # type: ignore
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            return {}

    async def get(self, id_: int) -> model.DailyShift | None:
        return self._daily_shifts.get(id_, None)

    async def save(self, daily_shift: model.DailyShift) -> None:
        self._daily_shifts[daily_shift.id] = daily_shift
        await asyncio.to_thread(self._write_daily_shift_to_file)

    def _write_daily_shift_to_file(self) -> None:
        with open("daily_shifts.json", "w") as file:
            serialized_daily_shifts = {
                k: v.model_dump() for k, v in self._daily_shifts.items()
            }
            json.dump(serialized_daily_shifts, file)

    def clean_daily_shifts(self) -> None:
        current_id_shift = time.get_posix_time_until_day()
        if not self._daily_shifts.get(current_id_shift):
            return
        self._daily_shifts = {current_id_shift: self._daily_shifts[current_id_shift]}


class DynamoDb(ports.Repository):
    def __init__(self, table_name: str, access_key: str, secret_key: str) -> None:
        self._client = boto3.resource(
            "dynamodb",
            region_name="us-east-1",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self._table = self._client.Table(table_name)

    async def get(self, id_: int) -> model.DailyShift | None:
        response = self._table.get_item(Key={"id": id_})
        if "Item" not in response:
            return None
        return model.DailyShift.parse_obj(response["Item"])  # type: ignore

    async def save(self, daily_shift: model.DailyShift) -> None:
        await asyncio.to_thread(
            self._table.put_item,
            Item=json.loads(json.dumps(daily_shift.model_dump()), parse_float=Decimal),
        )  # this is a workaround to avoid serialization issues with Decimal
