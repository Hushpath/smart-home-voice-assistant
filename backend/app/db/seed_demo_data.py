from datetime import datetime, timedelta, timezone

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models import CommandLog, User


DEMO_COMMANDS = [
    ("打开客厅灯", 5),
    ("开启睡眠模式", 7),
    ("提醒我晚上8点吃药", 4),
    ("打开卧室空调", 3),
    ("将电视机声量调到三十", 3),
    ("打开书房台灯", 2),
    ("关闭书房灯", 2),
    ("打开客厅窗帘", 2),
    ("启动扫地机器人", 2),
    ("打开厨房排风扇", 2),
    ("查询卧室灯状态", 2),
    ("打开空气净化器", 1),
    ("打开卧室加湿器", 1),
    ("开启回家模式", 1),
    ("开启离家模式", 1),
    ("提醒我晚上九点关灯", 1),
    ("帮我打开客厅冷气", 1),
]


def seed_demo_data() -> None:
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "testuser").first()
        if user is None:
            return

        now = datetime.now(timezone.utc).replace(microsecond=0)
        offset = 0
        added = 0
        for command, target_count in DEMO_COMMANDS:
            existing_count = (
                db.query(CommandLog)
                .filter(
                    CommandLog.user_id == user.id,
                    CommandLog.raw_command == command,
                    CommandLog.success.is_(True),
                )
                .count()
            )
            for _ in range(max(target_count - existing_count, 0)):
                created_at = now - timedelta(minutes=offset)
                db.add(
                    CommandLog(
                        user_id=user.id,
                        raw_command=command,
                        parsed_result={
                            "original_text": command,
                            "normalized_text": command,
                        },
                        execution_result={
                            "success": True,
                            "message": "演示数据",
                        },
                        success=True,
                        created_at=created_at,
                    )
                )
                offset += 7
                added += 1

        if added:
            db.commit()
        print("演示数据初始化完成。")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
