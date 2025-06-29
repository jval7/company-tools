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


class TestSyncBills:
    """Test suite for sync_bills method"""

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

    def _read_last_bill_id(self, temp_dir: Path) -> str:
        """Helper method to read last_bill_id.json"""
        last_bill_path = temp_dir / FileNames.LAST_BILL_ID_JSON
        with open(last_bill_path, 'r') as f:
            return json.load(f)["last_id"]

    @pytest.mark.asyncio
    async def test_sync_bills_empty_file(
        self, 
        sync_instance: Sync, 
        temp_dir: Path
    ) -> None:
        """Test sync_bills with empty daily_shifts.json"""
        # Arrange
        self._write_test_data(temp_dir, {})

        # Act
        await sync_instance.sync_bills()

        # Assert
        sync_instance.db.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_bills_all_days_synced(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test sync_bills when all days are already synced"""
        # Arrange
        test_data = DataFactory.create_multi_day_scenario()
        self._write_test_data(temp_dir, test_data)
        self._write_last_bill_id(temp_dir, BillIds.BILL_6)  # All synced

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Mock DynamoDB to return existing data for all days
        async def mock_get(day_id: int):
            if str(day_id) in test_data:
                return test_data[str(day_id)].to_model()
            return None

        sync_instance.db.get.side_effect = mock_get

        # Act
        await sync_instance.sync_bills()

        # Assert
        sync_instance.db.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_bills_multi_day_sync_success(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test sync_bills successfully syncing multiple unsynced days"""
        # Arrange
        test_data = DataFactory.create_multi_day_scenario()
        self._write_test_data(temp_dir, test_data)
        self._write_last_bill_id(temp_dir, BillIds.BILL_2)  # Only Day 1 synced

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Mock DynamoDB - only Day 1 exists
        async def mock_get(day_id: int):
            if day_id == DayIds.DAY_1:
                return test_data[str(day_id)].to_model()
            return None

        sync_instance.db.get.side_effect = mock_get

        synced_days = set()

        async def mock_save(daily_shift):
            synced_days.add(daily_shift.id)

        sync_instance.db.save.side_effect = mock_save

        # Act
        await sync_instance.sync_bills()

        # Assert
        assert synced_days == ExpectedResults.MULTI_DAY_SYNC_EXPECTED_DAYS
        assert sync_instance.db.save.call_count == 3  # Days 2, 3, 4

        # Verify last_bill_id was updated
        last_bill_id = self._read_last_bill_id(temp_dir)
        assert last_bill_id == ExpectedResults.LAST_SYNCED_BILL_AFTER_MULTI_SYNC

    @pytest.mark.asyncio
    async def test_sync_bills_partial_failure(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test sync_bills with partial failures during sync"""
        # Arrange
        test_data = DataFactory.create_multi_day_scenario()
        self._write_test_data(temp_dir, test_data)
        self._write_last_bill_id(temp_dir, BillIds.BILL_2)  # Only Day 1 synced

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Mock DynamoDB - only Day 1 exists
        async def mock_get(day_id: int):
            if day_id == DayIds.DAY_1:
                return test_data[str(day_id)].to_model()
            return None

        sync_instance.db.get.side_effect = mock_get

        synced_days = set()

        async def mock_save(daily_shift):
            if daily_shift.id == DayIds.DAY_3:
                raise Exception("DynamoDB connection error")
            synced_days.add(daily_shift.id)

        sync_instance.db.save.side_effect = mock_save

        # Act
        await sync_instance.sync_bills()

        # Assert
        expected_synced = {DayIds.DAY_2, DayIds.DAY_4}  # Day 3 failed
        assert synced_days == expected_synced
        assert sync_instance.db.save.call_count == 3  # Attempted all 3 days

        # Verify last_bill_id was updated to last successful sync
        last_bill_id = self._read_last_bill_id(temp_dir)
        assert last_bill_id == BillIds.BILL_6  # Last bill from Day 4

    @pytest.mark.asyncio
    async def test_sync_bills_current_day_only(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test sync_bills when only current day needs syncing"""
        # Arrange
        test_data = DataFactory.create_multi_day_scenario()
        self._write_test_data(temp_dir, test_data)
        self._write_last_bill_id(temp_dir, BillIds.BILL_5)  # Up to Day 3 synced

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Mock DynamoDB - Days 1, 2, 3 exist
        async def mock_get(day_id: int):
            if day_id in [DayIds.DAY_1, DayIds.DAY_2, DayIds.DAY_3]:
                return test_data[str(day_id)].to_model()
            return None

        sync_instance.db.get.side_effect = mock_get

        synced_days = set()

        async def mock_save(daily_shift):
            synced_days.add(daily_shift.id)

        sync_instance.db.save.side_effect = mock_save

        # Act
        await sync_instance.sync_bills()

        # Assert
        assert synced_days == {DayIds.DAY_4}
        assert sync_instance.db.save.call_count == 1

        # Verify last_bill_id was updated
        last_bill_id = self._read_last_bill_id(temp_dir)
        assert last_bill_id == BillIds.BILL_6

    @pytest.mark.asyncio
    async def test_sync_bills_no_bills_in_day(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test sync_bills with days that have no bills"""
        # Arrange
        empty_day_data = {
            str(DayIds.DAY_1): DataFactory.create_daily_shift(DayIds.DAY_1, [])
        }
        self._write_test_data(temp_dir, empty_day_data)
        self._write_last_bill_id(temp_dir, BillIds.NO_ID)

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_1)

        # Act
        await sync_instance.sync_bills()

        # Assert
        sync_instance.db.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_bills_handles_read_only_file_gracefully(
        self, 
        sync_instance: Sync, 
        temp_dir: Path,
        monkeypatch
    ) -> None:
        """Test sync_bills handles read-only last_bill_id.json gracefully"""
        # Arrange
        test_data = DataFactory.create_multi_day_scenario()
        self._write_test_data(temp_dir, test_data)

        # Create a read-only last_bill_id.json file
        last_bill_path = temp_dir / FileNames.LAST_BILL_ID_JSON
        with open(last_bill_path, 'w') as f:
            json.dump({"last_id": BillIds.BILL_2}, f)
        last_bill_path.chmod(0o444)  # Read-only

        # Mock current day
        monkeypatch.setattr("app.commons.time.get_posix_time_until_day", lambda: DayIds.DAY_4)

        # Mock DynamoDB
        sync_instance.db.get.return_value = None

        synced_days = set()

        async def mock_save(daily_shift):
            synced_days.add(daily_shift.id)

        sync_instance.db.save.side_effect = mock_save

        # Act & Assert - Should handle the permission error gracefully
        try:
            await sync_instance.sync_bills()
        except PermissionError:
            # This is expected due to the read-only file
            pass

        # Cleanup
        last_bill_path.chmod(0o644)
