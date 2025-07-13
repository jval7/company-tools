import boto3
from boto3.dynamodb.conditions import Key

from app.reporter import utils
from app.commons.logger import setup_console_logger

# Use console-only logger for reporter app (no file logging)
logger = setup_console_logger("reporter_logger")


def get_monthly_report() -> str | dict:
    logger.info("Starting get_monthly_report")
    first_day, last_day = utils.get_first_and_last_day_posix()
    logger.info(f"Querying monthly report from {first_day} to {last_day}")
    client = boto3.resource("dynamodb")
    table = client.Table("daily_shifts")

    # Use query operations for each day in the range instead of scan
    items = []
    current_day = first_day
    while current_day <= last_day:
        response = table.query(
            KeyConditionExpression=Key('id').eq(current_day)
        )
        if "Items" in response and response["Items"]:
            items.extend(response["Items"])
        current_day += 86400  # Add one day in seconds

    logger.info(f"Found {len(items)} items for monthly report")
    if not items:
        logger.warning("No data found for monthly report")
        return "No data found"
    total = get_total_from_daily_shifts(items)
    result = {
        "total": total["total"],
        "max": total["max"],
        "min": total["min"],
        "avg": total["avg"],
    }
    logger.info(f"Monthly report completed successfully: {result}")
    return result


def get_daily_report(params: dict | None) -> str | dict:
    logger.info(f"Starting get_daily_report with params: {params}")
    client = boto3.resource("dynamodb")
    table = client.Table("daily_shifts")
    if not params:
        logger.info("Getting daily report for current day (no params provided)")
        id_shift = utils.get_posix_time_until_day()
        logger.info(f"Querying for shift ID: {id_shift}")
        response = table.get_item(Key={"id": id_shift})
        if "Item" not in response:
            logger.warning("No data found for current day")
            return "No data found"
        response = response["Item"].get("total")
        result = {
            "total": utils.SetMoneda(response),
            "max": None,
            "min": None,
            "avg": None,
        }
        logger.info(f"Daily report for current day completed: {result}")
        return result

    start_date = params.get("start-date")
    end_date = params.get("end-date")
    logger.info(f"Getting daily report for date range: {start_date} to {end_date}")
    start_date_posix = utils.convert_to_posix(start_date)  # type: ignore
    end_date_posix = utils.convert_to_posix(end_date)  # type: ignore
    logger.info(f"Converted to posix: {start_date_posix} to {end_date_posix}")

    # Use query operations for each day in the range instead of scan
    items = []
    current_day = start_date_posix
    while current_day <= end_date_posix:
        response = table.query(
            KeyConditionExpression=Key('id').eq(current_day)
        )
        if "Items" in response and response["Items"]:
            items.extend(response["Items"])
        current_day += 86400  # Add one day in seconds

    logger.info(f"Found {len(items)} items for date range report")
    if not items:
        logger.warning("No data found for specified date range")
        return "No data found"
    total = get_total_from_daily_shifts(items)
    logger.info(f"Daily report for date range completed successfully: {total}")

    return total


def get_total_from_daily_shifts(shifts: list) -> dict:
    logger.info(f"Starting get_total_from_daily_shifts with {len(shifts)} shifts")
    total = 0
    for shift in shifts:
        total += shift["total"]
    result = {
        "total": utils.SetMoneda(total),
        "max": utils.SetMoneda(max(shifts, key=lambda x: x["total"])["total"]),
        "min": utils.SetMoneda(min(shifts, key=lambda x: x["total"])["total"]),
        "avg": utils.SetMoneda(total / len(shifts)),
    }
    logger.info(f"Calculated totals from daily shifts: {result}")
    return result
