from dataclasses import dataclass
from typing import Dict, List
from app.register import model


@dataclass(frozen=True)
class DayIds:
    """Day IDs constants for testing"""
    DAY_1: int = 1704067200  # 2024-01-01
    DAY_2: int = 1704153600  # 2024-01-02
    DAY_3: int = 1704240000  # 2024-01-03
    DAY_4: int = 1704326400  # 2024-01-04


@dataclass(frozen=True)
class BillIds:
    """Bill IDs constants for testing"""
    BILL_1: str = "test_bill_1"
    BILL_2: str = "test_bill_2"
    BILL_3: str = "test_bill_3"
    BILL_4: str = "test_bill_4"
    BILL_5: str = "test_bill_5"
    BILL_6: str = "test_bill_6"
    NO_ID: str = "no_id"


@dataclass(frozen=True)
class FileNames:
    """File names constants for testing"""
    DAILY_SHIFTS_JSON: str = "daily_shifts.json"
    LAST_BILL_ID_JSON: str = "last_bill_id.json"


@dataclass(frozen=True)
class Messages:
    """Messages constants for testing"""
    SYNC_ALL_SYNCED: str = "Sync: Todos los días están sincronizados"
    SYNC_FOUND_UNSYNCED: str = "Sync: Encontrados {} días sin sincronizar"
    SYNC_COMPLETED: str = "Sync completado: {} días sincronizados"
    SYNC_NO_DAYS: str = "Sync: No se pudo sincronizar ningún día"
    CLEANUP_CONSERVATIVE: str = "Cleanup conservador: Mantenidos {} días, eliminados {} días"
    CLEANUP_NO_REQUIRED: str = "Cleanup: No se requiere limpieza"


@dataclass
class BillData:
    """Bill data structure for testing"""
    id: str
    created_at: int
    total: float

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "items": [],
            "total": self.total
        }

    def to_model(self) -> model.Bill:
        return model.Bill(
            id=self.id,
            created_at=self.created_at,
            items=[],
            total=self.total
        )


@dataclass
class DailyShiftData:
    """Daily shift data structure for testing"""
    id: int
    bills: List[BillData]
    total: float

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "bills": [bill.to_dict() for bill in self.bills],
            "total": self.total
        }

    def to_model(self) -> model.DailyShift:
        return model.DailyShift(
            id=self.id,
            bills=[bill.to_model() for bill in self.bills],
            total=self.total
        )


class DataFactory:
    """Factory for creating test data"""

    @staticmethod
    def create_bill(bill_id: str, day_timestamp: int, total: float = 100.0) -> BillData:
        return BillData(
            id=bill_id,
            created_at=day_timestamp * 1_000_000_000,  # Convert to nanoseconds
            total=total
        )

    @staticmethod
    def create_daily_shift(day_id: int, bills: List[BillData]) -> DailyShiftData:
        total = sum(bill.total for bill in bills)
        return DailyShiftData(
            id=day_id,
            bills=bills,
            total=total
        )

    @staticmethod
    def create_multi_day_scenario() -> Dict[str, DailyShiftData]:
        """Creates a multi-day test scenario with mixed sync states"""
        # Day 1: 2 bills, should be synced
        day1_bills = [
            DataFactory.create_bill(BillIds.BILL_1, DayIds.DAY_1, 100.0),
            DataFactory.create_bill(BillIds.BILL_2, DayIds.DAY_1, 150.0)
        ]

        # Day 2: 2 bills, not synced
        day2_bills = [
            DataFactory.create_bill(BillIds.BILL_3, DayIds.DAY_2, 200.0),
            DataFactory.create_bill(BillIds.BILL_4, DayIds.DAY_2, 300.0)
        ]

        # Day 3: 1 bill, not synced
        day3_bills = [
            DataFactory.create_bill(BillIds.BILL_5, DayIds.DAY_3, 400.0)
        ]

        # Day 4: 1 bill, current day
        day4_bills = [
            DataFactory.create_bill(BillIds.BILL_6, DayIds.DAY_4, 500.0)
        ]

        return {
            str(DayIds.DAY_1): DataFactory.create_daily_shift(DayIds.DAY_1, day1_bills),
            str(DayIds.DAY_2): DataFactory.create_daily_shift(DayIds.DAY_2, day2_bills),
            str(DayIds.DAY_3): DataFactory.create_daily_shift(DayIds.DAY_3, day3_bills),
            str(DayIds.DAY_4): DataFactory.create_daily_shift(DayIds.DAY_4, day4_bills)
        }


@dataclass(frozen=True)
class ExpectedResults:
    """Expected results for various test scenarios"""
    MULTI_DAY_SYNC_EXPECTED_DAYS: frozenset = frozenset({DayIds.DAY_2, DayIds.DAY_3, DayIds.DAY_4})
    CONSERVATIVE_CLEANUP_KEPT_DAYS: frozenset = frozenset({DayIds.DAY_2, DayIds.DAY_4})  # Unsynced + current
    LAST_SYNCED_BILL_AFTER_MULTI_SYNC: str = BillIds.BILL_6
