import boto3

from app.reporter import utils


def get_monthly_report() -> str | dict:
    first_day, last_day = utils.get_first_and_last_day_posix()
    client = boto3.resource("dynamodb")
    table = client.Table("daily_shifts")
    response = table.scan(
        FilterExpression="id >= :first_day AND id <= :last_day",
        ExpressionAttributeValues={":first_day": first_day, ":last_day": last_day},
    )
    if "Items" not in response:
        return "No data found"
    total = get_total_from_daily_shifts(response["Items"])
    return {
        "total": total["total"],
        "max": total["max"],
        "min": total["min"],
        "avg": total["avg"],
    }


def get_daily_report(params: dict | None) -> str | dict:
    client = boto3.resource("dynamodb")
    table = client.Table("daily_shifts")
    if not params:
        id_shift = utils.get_posix_time_until_day()
        response = table.get_item(Key={"id": id_shift})
        if "Item" not in response:
            return "No data found"
        response = response["Item"].get("total")

        return {
            "total": utils.SetMoneda(response),
            "max": None,
            "min": None,
            "avg": None,
        }

    start_date = params.get("start-date")
    end_date = params.get("end-date")
    start_date_posix = utils.convert_to_posix(start_date)  # type: ignore
    end_date_posix = utils.convert_to_posix(end_date)  # type: ignore

    response = table.scan(
        FilterExpression="id >= :start_date AND id <= :end_date",
        ExpressionAttributeValues={
            ":start_date": start_date_posix,
            ":end_date": end_date_posix,
        },
    )
    if "Items" not in response:
        return "No data found"
    total = get_total_from_daily_shifts(response["Items"])

    return total


def get_total_from_daily_shifts(shifts: list) -> dict:
    total = 0
    for shift in shifts:
        total += shift["total"]
    return {
        "total": utils.SetMoneda(total),
        "max": utils.SetMoneda(max(shifts, key=lambda x: x["total"])["total"]),
        "min": utils.SetMoneda(min(shifts, key=lambda x: x["total"])["total"]),
        "avg": utils.SetMoneda(total / len(shifts)),
    }
