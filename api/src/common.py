import asyncio


async def gather_cancel(*tasks, **kwargs):
    tasks = [task if isinstance(task, asyncio.Task) else asyncio.create_task(task) for task in tasks]
    try:
        return await asyncio.gather(*tasks, **kwargs)
    except BaseException as e:
        for task in tasks:
            task.cancel()
        raise
