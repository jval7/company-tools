import asyncio

from app.register import entrypoints, usecases, adapters
from app.register.configurations import configs


async def start_app() -> None:
    # bootstrap
    in_memory_repo = adapters.InMemoryRepo()
    register = usecases.Register(repo=in_memory_repo)

    dynamo_db = adapters.DynamoDb(
        table_name="daily_shifts",
        access_key=configs.aws_access_key_id,
        secret_key=configs.aws_secret_access_key,
    )
    syncronizer = entrypoints.Sync(db=dynamo_db, in_memory_repo=in_memory_repo)

    await asyncio.gather(
        entrypoints.set_up_sync_process(
            sync_bills=syncronizer.sync_bills,
            clean_daily_shifts=syncronizer.clean_daily_shifts,
            time_sync=configs.time_to_sync,
            time_clean=configs.time_to_clean,
        ),
        entrypoints.start_view(register=register, syncronizer=syncronizer),
    )


if __name__ == "__main__":
    asyncio.run(start_app())
