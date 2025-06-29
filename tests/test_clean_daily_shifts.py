import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock
from typing import Dict, Any

import pytest
import pytest_asyncio

from app.register.entrypoints.cron import Sync
from app.register import adapters
from tests.test_constants import (
    DayIds, BillIds, FileNames, Messages,
    DataFactory, ExpectedResults
)


class TestCleanDailyShifts:
    """Test suite for clean_daily_shifts method"""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create a mock DynamoDB repository"""
        return AsyncMock()

    @pytest.fixture
    def in_memory_repo(self, temp_dir: Path) -> adapters.InMemoryRepo:
        """Create a real InMemoryRepo instance"""
        daily_shifts_path = temp_dir / FileNames.DAILY_SHIFTS_JSON
        return adapters.InMemoryRepo(path_file=str(daily_shifts_path))

    @pytest.fixture
    def temp_dir(self, monkeypatch) -> Path:
        """Create a temporary directory and change to it"""
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir_path = Path(temp_dir_str)
            monkeypatch.chdir(temp_dir_path)
            yield temp_dir_path

    @pytest.fixture
    def sync_instance(self, mock_db: AsyncMock, in_memory_repo: adapters.InMemoryRepo) -> Sync:
        """Create a Sync instance with mocked DB and real in-memory repo"""
        return Sync(db=mock_db, in_memory_repo=in_memory_repo)

    def _write_test_data(self, temp_dir: Path, data: Dict[str, Any]) -> None:
        """Helper method to write test data to files"""
        # Write daily_shifts.json
        daily_shifts_path = temp_dir / FileNames.DAILY_SHIFTS_JSON
        with open(daily_shifts_path, 'w') as f:
            json.dump({k: v.to_dict() for k, v in data.items()}, f, indent=2)

    def _write_last_bill_id(self, temp_dir: Path, bill_id: str) -> None:
        """Helper method to write last_bill_id.json"""
        last_bill_path = temp_dir / FileNames.LAST_BILL_ID_JSON
        with open(last_bill_path, 'w') as f:
            json.dump({"last_id": bill_id}, f)

    def _read_daily_shifts(self, temp_dir: Path) -> Dict[str, Any]:
        """Helper method to read daily_shifts.json"""
        daily_shifts_path = temp_dir / FileNames.DAILY_SHIFTS_JSON
        with open(daily_shifts_path, 'r') as f:
            return json.load(f)

    @pytest.mark.asyncio
    async def test_clean_daily_shifts_empty_file(
        self, 
        sync_instance: Sync, 
        temp_dir: Path
    ) -> None:
        """Test clean_daily_shifts with empty daily_shifts.json"""
        # Arrange
        self._write_test_data(temp_dir, {})

        # Act
        await sync_instance.clean_daily_shifts()

        # Assert
        sync_instance.db.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_clean_daily_shifts_conservative_cleanup(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test conservative cleanup keeps current day and unsynced days"""
        # Arrange
        test_data = DataFactory.create_multi_day_scenario()
        self._write_test_data(temp_dir, test_data)
        self._write_last_bill_id(temp_dir, BillIds.BILL_2)  # Only Day 1 synced

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Mock DynamoDB - only Day 1 exists (synced)
        async def mock_get(day_id: int):
            if day_id == DayIds.DAY_1:
                return test_data[str(day_id)].to_model()
            return None

        sync_instance.db.get.side_effect = mock_get

        # Act
        await sync_instance.clean_daily_shifts()

        # Assert
        result_data = self._read_daily_shifts(temp_dir)
        kept_days = {int(day_id) for day_id in result_data.keys()}

        # Should keep Day 2 (unsynced), Day 3 (unsynced), Day 4 (current)
        # Should remove Day 1 (synced)
        expected_kept_days = {DayIds.DAY_2, DayIds.DAY_3, DayIds.DAY_4}
        assert kept_days == expected_kept_days

        # Verify in-memory repo was updated
        assert set(sync_instance.in_memory_repo._daily_shifts.keys()) == expected_kept_days

    @pytest.mark.asyncio
    async def test_clean_daily_shifts_all_days_synced(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test cleanup when all days except current are synced"""
        # Arrange
        test_data = DataFactory.create_multi_day_scenario()
        self._write_test_data(temp_dir, test_data)
        self._write_last_bill_id(temp_dir, BillIds.BILL_6)  # All synced

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Mock DynamoDB - all days exist (synced)
        async def mock_get(day_id: int):
            if str(day_id) in test_data:
                return test_data[str(day_id)].to_model()
            return None

        sync_instance.db.get.side_effect = mock_get

        # Act
        await sync_instance.clean_daily_shifts()

        # Assert
        result_data = self._read_daily_shifts(temp_dir)
        kept_days = {int(day_id) for day_id in result_data.keys()}

        # Should only keep current day (Day 4)
        expected_kept_days = {DayIds.DAY_4}
        assert kept_days == expected_kept_days

    @pytest.mark.asyncio
    async def test_clean_daily_shifts_no_cleanup_needed(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test cleanup when no cleanup is needed (only current day exists)"""
        # Arrange
        current_day_data = {
            str(DayIds.DAY_4): DataFactory.create_daily_shift(
                DayIds.DAY_4, 
                [DataFactory.create_bill(BillIds.BILL_6, DayIds.DAY_4)]
            )
        }
        self._write_test_data(temp_dir, current_day_data)
        self._write_last_bill_id(temp_dir, BillIds.BILL_5)  # Previous bill synced

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Act
        await sync_instance.clean_daily_shifts()

        # Assert
        result_data = self._read_daily_shifts(temp_dir)
        kept_days = {int(day_id) for day_id in result_data.keys()}

        # Should keep only current day
        assert kept_days == {DayIds.DAY_4}

    @pytest.mark.asyncio
    async def test_clean_daily_shifts_dynamodb_error_conservative(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test cleanup is conservative when DynamoDB errors occur"""
        # Arrange
        test_data = DataFactory.create_multi_day_scenario()
        self._write_test_data(temp_dir, test_data)
        self._write_last_bill_id(temp_dir, BillIds.BILL_2)  # Only Day 1 synced

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Mock DynamoDB to raise errors (conservative approach)
        async def mock_get_with_error(day_id: int):
            if day_id == DayIds.DAY_1:
                return test_data[str(day_id)].to_model()
            elif day_id == DayIds.DAY_2:
                raise Exception("DynamoDB connection error")
            return None

        sync_instance.db.get.side_effect = mock_get_with_error

        # Act
        await sync_instance.clean_daily_shifts()

        # Assert
        result_data = self._read_daily_shifts(temp_dir)
        kept_days = {int(day_id) for day_id in result_data.keys()}

        # Should keep Day 2 (error = conservative), Day 3 (unsynced), Day 4 (current)
        # Should remove Day 1 (confirmed synced)
        expected_kept_days = {DayIds.DAY_2, DayIds.DAY_3, DayIds.DAY_4}
        assert kept_days == expected_kept_days

    @pytest.mark.asyncio
    async def test_clean_daily_shifts_current_day_unsynced(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test cleanup when current day has unsynced bills"""
        # Arrange
        test_data = DataFactory.create_multi_day_scenario()
        self._write_test_data(temp_dir, test_data)
        self._write_last_bill_id(temp_dir, BillIds.BILL_5)  # Up to Day 3 synced

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Mock DynamoDB - Days 1, 2, 3 exist (synced)
        async def mock_get(day_id: int):
            if day_id in [DayIds.DAY_1, DayIds.DAY_2, DayIds.DAY_3]:
                return test_data[str(day_id)].to_model()
            return None

        sync_instance.db.get.side_effect = mock_get

        # Act
        await sync_instance.clean_daily_shifts()

        # Assert
        result_data = self._read_daily_shifts(temp_dir)
        kept_days = {int(day_id) for day_id in result_data.keys()}

        # Should only keep Day 4 (current day with unsynced bills)
        expected_kept_days = {DayIds.DAY_4}
        assert kept_days == expected_kept_days

    @pytest.mark.asyncio
    async def test_clean_daily_shifts_mixed_sync_states(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test cleanup with mixed sync states across multiple days"""
        # Arrange
        test_data = DataFactory.create_multi_day_scenario()
        self._write_test_data(temp_dir, test_data)
        self._write_last_bill_id(temp_dir, BillIds.BILL_3)  # Day 1 and part of Day 2 synced

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Mock DynamoDB - Day 1 fully synced, Day 2 partially synced
        async def mock_get(day_id: int):
            if day_id == DayIds.DAY_1:
                return test_data[str(day_id)].to_model()
            elif day_id == DayIds.DAY_2:
                # Return partial data (missing bill4)
                partial_day2 = test_data[str(day_id)].to_model()
                partial_day2.bills = partial_day2.bills[:1]  # Only first bill
                return partial_day2
            return None

        sync_instance.db.get.side_effect = mock_get

        # Act
        await sync_instance.clean_daily_shifts()

        # Assert
        result_data = self._read_daily_shifts(temp_dir)
        kept_days = {int(day_id) for day_id in result_data.keys()}

        # Should keep Day 2 (partially synced), Day 3 (unsynced), Day 4 (current)
        # Should remove Day 1 (fully synced)
        expected_kept_days = {DayIds.DAY_2, DayIds.DAY_3, DayIds.DAY_4}
        assert kept_days == expected_kept_days

    @pytest.mark.asyncio
    async def test_clean_daily_shifts_no_bills_in_days(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test cleanup with days that have no bills"""
        # Arrange
        empty_days_data = {
            str(DayIds.DAY_1): DataFactory.create_daily_shift(DayIds.DAY_1, []),
            str(DayIds.DAY_2): DataFactory.create_daily_shift(DayIds.DAY_2, []),
            str(DayIds.DAY_4): DataFactory.create_daily_shift(DayIds.DAY_4, [])
        }
        self._write_test_data(temp_dir, empty_days_data)
        self._write_last_bill_id(temp_dir, BillIds.NO_ID)

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Act
        await sync_instance.clean_daily_shifts()

        # Assert
        result_data = self._read_daily_shifts(temp_dir)
        kept_days = {int(day_id) for day_id in result_data.keys()}

        # Should keep only current day (Day 4) since empty days are skipped in unsynced logic
        expected_kept_days = {DayIds.DAY_4}
        assert kept_days == expected_kept_days

    @pytest.mark.asyncio
    async def test_clean_daily_shifts_file_write_preserves_data(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test that file write operations preserve data integrity"""
        # Arrange
        test_data = DataFactory.create_multi_day_scenario()
        self._write_test_data(temp_dir, test_data)
        self._write_last_bill_id(temp_dir, BillIds.BILL_2)

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Mock DynamoDB - only Day 1 exists
        async def mock_get(day_id: int):
            if day_id == DayIds.DAY_1:
                return test_data[str(day_id)].to_model()
            return None

        sync_instance.db.get.side_effect = mock_get

        # Act
        await sync_instance.clean_daily_shifts()

        # Assert
        result_data = self._read_daily_shifts(temp_dir)

        # Verify data integrity for kept days
        for day_str in result_data:
            day_id = int(day_str)
            original_day = test_data[day_str]
            result_day = result_data[day_str]

            assert result_day["id"] == original_day.id
            assert result_day["total"] == original_day.total
            assert len(result_day["bills"]) == len(original_day.bills)

            for i, bill in enumerate(result_day["bills"]):
                original_bill = original_day.bills[i]
                assert bill["id"] == original_bill.id
                assert bill["total"] == original_bill.total
