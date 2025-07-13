import json

from app.reporter import usecases


def route(path: str, params: dict | None) -> dict:
    match path:
        case "/reporter/get-monthly-report":
            return usecases.get_monthly_report()  # type: ignore
        case "/reporter/get-daily-report":
            return usecases.get_daily_report(params=params)  # type: ignore
        case _:
            return {"statusCode": 404, "body": f"Route don't exist {path}"}


def lambda_handler(event, context):  # type: ignore
    try:
        response = route(
            path=event.get("rawPath"), params=event.get("queryStringParameters")
        )
    except Exception as e:
        raise e
    return {"statusCode": 200, "body": json.dumps(response)}
