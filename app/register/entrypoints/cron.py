import json
from os import path
from typing import Callable

import aiocron
import aiofiles  # type: ignore

from app.commons import time
from app.commons.logger import logger
from app.register import model, ports, adapters


class Sync:
    def __init__(
        self, db: ports.Repository, in_memory_repo: adapters.InMemoryRepo
    ) -> None:
        self.db = db
        self.in_memory_repo = in_memory_repo

    async def sync_bills(self) -> None:
        """
        Sincroniza todos los días que no están sincronizados con DynamoDB
        """
        # load daily shifts from file
        async with aiofiles.open("daily_shifts.json", "r") as file:
            data_loaded = json.loads(await file.read())
            daily_shifts = {
                int(k): model.DailyShift.parse_obj(v) for k, v in data_loaded.items()
            }

        if not daily_shifts:
            return

        # Obtener días que NO están sincronizados
        unsynced_days = await self._get_unsynced_days(daily_shifts)

        if not unsynced_days:
            logger.info("All days are already synced")
            return

        logger.info(f"Found {len(unsynced_days)} unsynced days")

        # Sincronizar cada día no sincronizado
        synced_count = 0
        last_synced_bill_id = None

        # Ordenar días para sincronizar en orden cronológico
        sorted_unsynced_days = sorted(unsynced_days)

        for day_id in sorted_unsynced_days:
            daily_shift = daily_shifts.get(day_id)
            if not daily_shift or not daily_shift.bills:
                continue

            try:
                # Intentar sincronización del día
                await self.db.save(daily_shift=daily_shift)
                synced_count += 1

                # Actualizar el último bill_id sincronizado con el último bill de este día
                last_bill_of_day = daily_shift.bills[-1]
                last_synced_bill_id = last_bill_of_day.id

                logger.info(f"Day {day_id} synced successfully (day_id={day_id}, bills_count={len(daily_shift.bills)})")

            except Exception as e:
                logger.error(f"Failed to sync day {day_id} (day_id={day_id}, error={str(e)})")
                # Si falla la sincronización de un día, continuar con los siguientes
                continue

        # Solo actualizar last_bill_id si se sincronizó al menos un día
        if synced_count > 0 and last_synced_bill_id:
            try:
                async with aiofiles.open("last_bill_id.json", "w") as file:
                    await file.write(json.dumps({"last_id": last_synced_bill_id}))
                logger.info(f"Sync completed: {synced_count} days synced")
            except Exception as e:
                logger.error(f"Failed to update last_bill_id: {str(e)}")
        else:
            logger.error("No days could be synced")

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
        """
        Cleanup conservador: mantiene día actual + días NO sincronizados
        """
        current_day = time.get_posix_time_until_day()

        # Cargar datos actuales
        async with aiofiles.open("daily_shifts.json", "r") as file:
            data_loaded = json.loads(await file.read())
            daily_shifts = {
                int(k): model.DailyShift.parse_obj(v) for k, v in data_loaded.items()
            }

        if not daily_shifts:
            return

        # Obtener días que NO están sincronizados
        unsynced_days = await self._get_unsynced_days(daily_shifts)

        # ✅ CORRECTO - Mantener día actual + días NO sincronizados
        days_to_keep = {current_day} | unsynced_days

        # Aplicar filtro conservador
        cleaned_shifts = {
            k: v for k, v in daily_shifts.items() 
            if k in days_to_keep
        }

        # Solo escribir si hay cambios
        if len(cleaned_shifts) != len(daily_shifts):
            await self._write_cleaned_shifts(cleaned_shifts)
            days_removed = len(daily_shifts) - len(cleaned_shifts)
            logger.info(f"Conservative cleanup completed (days_kept={len(cleaned_shifts)}, days_removed={days_removed})")
        else:
            logger.info("No cleanup required")

    async def _get_unsynced_days(self, daily_shifts: dict) -> set[int]:
        """
        Identifica qué días NO están sincronizados con DynamoDB
        """
        unsynced_days = set()

        # Cargar último bill_id sincronizado
        last_synced_bill_id = await self._load_bill_id()

        for day_id, daily_shift in daily_shifts.items():
            if not daily_shift.bills:
                continue

            # Si el último bill del día no coincide con el último sincronizado,
            # significa que este día tiene datos no sincronizados
            last_bill_of_day = daily_shift.bills[-1]

            if day_id == time.get_posix_time_until_day():
                # Para el día actual, verificar si hay bills nuevos
                if last_bill_of_day.id != last_synced_bill_id:
                    unsynced_days.add(day_id)
            else:
                # Para días anteriores, verificar si fueron sincronizados
                if not await self._is_day_synced(day_id, daily_shift):
                    unsynced_days.add(day_id)

        return unsynced_days

    async def _is_day_synced(self, day_id: int, daily_shift: model.DailyShift) -> bool:
        """
        Verifica si un día específico está sincronizado con DynamoDB
        """
        try:
            # Intentar obtener el día desde DynamoDB
            dynamo_shift = await self.db.get(day_id)

            if not dynamo_shift:
                return False

            # Comparar número de bills y último bill ID
            local_bills_count = len(daily_shift.bills)
            dynamo_bills_count = len(dynamo_shift.bills)

            if local_bills_count != dynamo_bills_count:
                return False

            if daily_shift.bills and dynamo_shift.bills:
                local_last_bill = daily_shift.bills[-1].id
                dynamo_last_bill = dynamo_shift.bills[-1].id
                return local_last_bill == dynamo_last_bill

            return True

        except Exception as e:
            logger.error(f"Error verifying sync status for day {day_id}: {str(e)}")
            # En caso de error, asumir que NO está sincronizado (conservador)
            return False

    async def _write_cleaned_shifts(self, cleaned_shifts: dict) -> None:
        """
        Escribe los datos limpios de forma segura
        """
        # Escribir al archivo
        async with aiofiles.open("daily_shifts.json", "w") as file:
            serialized_shifts = {
                k: v.model_dump() for k, v in cleaned_shifts.items()
            }
            await file.write(json.dumps(serialized_shifts, indent=2))

        # Actualizar memoria
        self.in_memory_repo._daily_shifts = cleaned_shifts


async def set_up_sync_process(
    sync_bills: Callable, clean_daily_shifts: Callable, time_sync: int, time_clean: int
) -> None:
    time_to_sync = f"* * * * * */{time_sync}"
    time_to_clean = f"* * * * * */{time_clean}"
    aiocron.crontab(time_to_sync, func=sync_bills, start=True)
    aiocron.crontab(time_to_clean, func=clean_daily_shifts, start=True)


# asyncio.get_event_loop().run_forever()
