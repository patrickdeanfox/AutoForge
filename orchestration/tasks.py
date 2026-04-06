import asyncio

from orchestration.scheduler import app


@app.task(name="orchestration.tasks.send_morning_summary")
def send_morning_summary() -> None:
    from telegram.notifications.morning_summary import send_morning_summary as _send

    asyncio.run(_send())
