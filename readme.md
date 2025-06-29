# Company Tools - Register App

A point-of-sale (POS) register application that manages bills and daily shifts with hybrid storage architecture for data reliability.

## Features

### Core Functionality
- **Bill Management**: Create, modify, and track individual bills with items
- **Item Operations**: Add/remove items with price, quantity, and ID tracking
- **Daily Shift Aggregation**: Group bills by day with automatic totaling
- **Real-time Calculations**: Automatic total calculation for bills and daily shifts

### Data Models
- **Item**: Basic product with ID, price, and quantity
- **Bill**: Transaction record with unique ID, timestamp, items list, and total
- **DailyShift**: Daily aggregate containing all bills for a specific day

## Storage Architecture

### Hybrid Storage System
The application uses a **dual-storage approach** to ensure data reliability:

1. **Primary Storage (Local JSON Files)**
   - Bills are immediately stored in `daily_shifts.json`
   - Fast write operations for real-time POS operations
   - No network dependency for core functionality
   - Automatic file-based persistence

2. **Secondary Storage (AWS DynamoDB)**
   - Cloud backup for data durability
   - Periodic synchronization from local storage
   - Configurable sync intervals via environment variables
   - Table name: `daily_shifts`

### Data Flow
```
User Input → Bill Creation → Local JSON Storage → Periodic Sync → DynamoDB
```

## Synchronization Process

### How Bills Are Stored
1. **Immediate Local Storage**: When a bill is saved, it's instantly written to local JSON files
2. **Change Detection**: System tracks the last synced bill ID to detect new transactions
3. **Periodic Sync**: Background process runs at configurable intervals to sync new data to DynamoDB
4. **Cleanup Process**: Old daily shifts are periodically cleaned from local storage

### Sync Configuration
Configure sync behavior via environment variables:
- `TIME_TO_SYNC`: Interval in seconds for DynamoDB synchronization
- `TIME_TO_CLEAN`: Interval in seconds for local cleanup operations
- `AWS_ACCESS_KEY_ID`: AWS credentials for DynamoDB access
- `AWS_SECRET_ACCESS_KEY`: AWS secret key for DynamoDB access

## DynamoDB Connection Failure Handling

### Current Behavior
⚠️ **Critical Issue**: The application currently has **limited error handling** for DynamoDB failures:

- If DynamoDB connection fails during sync, the sync process will crash
- Local operations continue normally (bills are still saved locally)
- No retry mechanism for failed sync operations
- No alerting when sync failures occur

### Data Loss Scenarios
1. **Extended DynamoDB Outage**: If DynamoDB is unavailable for extended periods, only local data exists
2. **Local File Corruption**: If local JSON files are corrupted and DynamoDB sync has failed, data could be lost
3. **Application Restart**: If the application restarts after DynamoDB failures, unsync'd data might be lost

## Recommended Improvements

### 1. Enhanced Error Handling
```python
# Add try-catch blocks in sync operations
try:
    await self.db.save(daily_shift=current_daily_shift)
    # Update last_bill_id only on successful sync
except Exception as e:
    logger.error(f"DynamoDB sync failed: {e}")
    # Keep local data, retry later
```

### 2. Retry Mechanism
- Implement exponential backoff for failed sync operations
- Queue failed sync operations for retry
- Maximum retry attempts with fallback strategies

### 3. Health Monitoring
- Add health checks for DynamoDB connectivity
- Implement alerting for sync failures
- Dashboard for monitoring sync status and lag

### 4. Data Integrity Checks
- Implement checksums for local data validation
- Periodic data consistency checks between local and DynamoDB
- Automatic data recovery procedures

### 5. Backup Strategies
- Multiple local backup locations
- Periodic exports to external storage (S3, local backups)
- Database transaction logs for point-in-time recovery

### 6. Configuration Improvements
- Circuit breaker pattern for DynamoDB operations
- Configurable retry policies
- Graceful degradation modes

## Usage

### Environment Setup
Create a `.env` file with:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
TIME_TO_SYNC=30
TIME_TO_CLEAN=3600
```

### Running the Application
```bash
python -m app.register.main
```

## Architecture Benefits

### Advantages of Current Design
- **High Availability**: Local storage ensures POS operations continue during network issues
- **Performance**: Fast local operations with background cloud sync
- **Cost Effective**: Reduced DynamoDB read/write operations through batching

### Areas for Improvement
- **Error Resilience**: Need robust error handling for cloud operations
- **Data Durability**: Multiple backup strategies required
- **Monitoring**: Better visibility into sync status and failures
- **Recovery**: Automated recovery procedures for various failure scenarios
