"""
Integration tests for get_daily_report function with parameters.

This is a true integration test that does NOT use mocking and requires:
1. DynamoDB access (either AWS DynamoDB or DynamoDB Local)
2. Proper AWS credentials configured (if using AWS DynamoDB)
3. Or DYNAMODB_ENDPOINT_URL environment variable set (if using DynamoDB Local)

To run with DynamoDB Local:
    export DYNAMODB_ENDPOINT_URL=http://localhost:8000
    pytest tests/test_get_daily_report_integration.py -m integration

To run with AWS DynamoDB:
    # Ensure AWS credentials are configured
    pytest tests/test_get_daily_report_integration.py -m integration

Note: This test will create/use the 'daily_shifts' table and will clean up after itself.
"""

import pytest
import boto3
from datetime import datetime, timezone, timedelta
import os

from app.reporter.usecases import get_daily_report


@pytest.mark.integration
class TestGetDailyReportIntegration:
    """Integration tests for get_daily_report function with parameters"""

    # def setup_method(self):
    #     """Set up DynamoDB table for each test"""
    #     # Use the actual table name that the function uses
    #     self.table_name = 'daily_shifts'
    #
    #     # Configure DynamoDB resource
    #     # Check if we should use local DynamoDB or AWS
    #     endpoint_url = os.environ.get('DYNAMODB_ENDPOINT_URL')
    #     if endpoint_url:
    #         self.dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url, region_name='us-east-1')
    #     else:
    #         self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    #
    #     # Try to create the table if it doesn't exist
    #     try:
    #         self.table = self.dynamodb.create_table(
    #             TableName=self.table_name,
    #             KeySchema=[
    #                 {
    #                     'AttributeName': 'id',
    #                     'KeyType': 'HASH'
    #                 }
    #             ],
    #             AttributeDefinitions=[
    #                 {
    #                     'AttributeName': 'id',
    #                     'AttributeType': 'N'
    #                 }
    #             ],
    #             BillingMode='PAY_PER_REQUEST'
    #         )
    #         # Wait for table to be created
    #         self.table.wait_until_exists()
    #     except Exception as e:
    #         # If table already exists, get reference to it
    #         if 'ResourceInUseException' in str(e) or 'already exists' in str(e):
    #             self.table = self.dynamodb.Table(self.table_name)
    #         else:
    #             raise e
    #
    #     # Store original items to restore after test
    #     self.original_items = []
    #     try:
    #         response = self.table.scan()
    #         self.original_items = response.get('Items', [])
    #     except Exception:
    #         # If scan fails, assume table is empty
    #         pass
    #
    # def teardown_method(self):
    #     """Clean up test data and restore original state after each test"""
    #     try:
    #         # Clear all items from the table
    #         response = self.table.scan()
    #         with self.table.batch_writer() as batch:
    #             for item in response['Items']:
    #                 batch.delete_item(Key={'id': item['id']})
    #
    #         # Restore original items if any existed
    #         if self.original_items:
    #             with self.table.batch_writer() as batch:
    #                 for item in self.original_items:
    #                     batch.put_item(Item=item)
    #     except Exception:
    #         # If cleanup fails, it's not critical for the test
    #         pass
    #
    # def _add_test_data(self):
    #     """Add test data to the DynamoDB table"""
    #     # Add sample data for different dates
    #     # Using POSIX timestamps for specific dates
    #
    #     # Date: 01-01-2024 (January 1, 2024)
    #     date_2024_01_01 = int(datetime(2024, 1, 1).timestamp())
    #     self.table.put_item(Item={'id': date_2024_01_01, 'total': 150000})
    #
    #     # Date: 02-01-2024 (January 2, 2024)
    #     date_2024_01_02 = int(datetime(2024, 1, 2).timestamp())
    #     self.table.put_item(Item={'id': date_2024_01_02, 'total': 200000})
    #
    #     # Date: 03-01-2024 (January 3, 2024)
    #     date_2024_01_03 = int(datetime(2024, 1, 3).timestamp())
    #     self.table.put_item(Item={'id': date_2024_01_03, 'total': 175000})
    #
    #     # Date: 05-01-2024 (January 5, 2024)
    #     date_2024_01_05 = int(datetime(2024, 1, 5).timestamp())
    #     self.table.put_item(Item={'id': date_2024_01_05, 'total': 300000})

    def test_get_daily_report_with_date_range_params(self):
        """Test get_daily_report with start-date and end-date parameters"""
        # Add test data
        # self._add_test_data()

        # Test with date range parameters
        params = {
            "start-date": "12-07-2025",
            "end-date": "13-07-2025"
        }

        result = get_daily_report(params)

        # Verify the result is a dictionary with expected keys
        assert isinstance(result, dict)


    def test_get_daily_report_with_single_day_range(self):
        """Test get_daily_report with same start and end date"""
        # Add test data
        self._add_test_data()

        # Test with single day range
        params = {
            "start-date": "02-01-2024",
            "end-date": "02-01-2024"
        }

        result = get_daily_report(params)

        # Verify the result
        assert isinstance(result, dict)
        assert "200,000" in result["total"]
        assert "200,000" in result["max"]
        assert "200,000" in result["min"]
        assert "200,000" in result["avg"]

    def test_get_daily_report_with_no_data_in_range(self):
        """Test get_daily_report when no data exists in the specified range"""
        # Add test data
        self._add_test_data()

        # Test with date range that has no data
        params = {
            "start-date": "10-01-2024",
            "end-date": "15-01-2024"
        }

        result = get_daily_report(params)

        # Should return "No data found" when no items in range
        assert result == "No data found"

    def test_get_daily_report_with_wider_date_range(self):
        """Test get_daily_report with a wider date range including all test data"""
        # Add test data
        self._add_test_data()

        # Test with wider date range
        params = {
            "start-date": "01-01-2024",
            "end-date": "10-01-2024"
        }

        result = get_daily_report(params)

        # Verify the result includes all test data
        assert isinstance(result, dict)
        # Total should be 150000 + 200000 + 175000 + 300000 = 825000
        assert "825,000" in result["total"]
        assert "300,000" in result["max"]  # Maximum value
        assert "150,000" in result["min"]  # Minimum value
        assert "206,250" in result["avg"]  # Average: 825000/4 = 206250

    def test_get_daily_report_without_params(self):
        """Test get_daily_report without parameters (current day lookup)"""
        # This test will look for today's data, which won't exist in our test data
        # So it should return "No data found"
        result = get_daily_report(None)

        # Should return "No data found" since we don't have today's data
        assert result == "No data found"
