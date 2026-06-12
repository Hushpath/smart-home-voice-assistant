from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import Device, Home, Room, Scene, SceneAction, User


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_initial_data(db: Session) -> None:
    if db.query(Home).filter(Home.name == "默认家庭").first():
        print("初始化数据已存在，跳过重复写入。")
        return

    home = Home(name="默认家庭", address="课程设计虚拟家庭")
    db.add(home)
    db.flush()

    rooms: dict[str, Room] = {}
    for room_name in ["客厅", "卧室", "厨房", "书房"]:
        room = Room(name=room_name, home_id=home.id)
        db.add(room)
        rooms[room_name] = room
    db.flush()

    device_specs = [
        ("客厅", "灯", "light", False, True, {"brightness": 60, "color_temperature": "暖白"}),
        ("客厅", "空调", "air_conditioner", False, True, {"temperature": 26, "mode": "制冷", "fan_speed": "自动"}),
        ("客厅", "电视", "tv", False, True, {"volume": 20, "channel": "CCTV-1"}),
        ("客厅", "窗帘", "curtain", False, True, {"open_percent": 0}),
        ("卧室", "灯", "light", False, True, {"brightness": 40, "color_temperature": "暖黄"}),
        ("卧室", "空调", "air_conditioner", False, True, {"temperature": 26, "mode": "制冷", "fan_speed": "低速"}),
        ("卧室", "窗帘", "curtain", False, True, {"open_percent": 0}),
        ("厨房", "灯", "light", False, True, {"brightness": 70, "color_temperature": "自然光"}),
        ("厨房", "排风扇", "fan", False, True, {"speed": "中速"}),
        ("书房", "灯", "light", False, True, {"brightness": 75, "color_temperature": "冷白"}),
        ("书房", "空调", "air_conditioner", False, True, {"temperature": 25, "mode": "制冷", "fan_speed": "自动"}),
    ]

    devices: dict[tuple[str, str], Device] = {}
    for room_name, name, device_type, is_on, is_online, properties in device_specs:
        device = Device(
            name=name,
            device_type=device_type,
            room_id=rooms[room_name].id,
            is_on=is_on,
            is_online=is_online,
            properties=properties,
        )
        db.add(device)
        devices[(room_name, name)] = device
    db.flush()

    user = User(
        username="testuser",
        password_hash=hash_password("test123456"),
        nickname="默认测试用户",
        home_id=home.id,
        is_active=True,
    )
    db.add(user)

    scene_specs = [
        (
            "回家模式",
            "打开客厅常用设备，营造回家环境。",
            [
                ("客厅", "灯", {"is_on": True, "properties": {"brightness": 80}}),
                ("客厅", "空调", {"is_on": True, "properties": {"temperature": 26, "mode": "制冷"}}),
                ("客厅", "电视", {"is_on": True, "properties": {"volume": 20}}),
            ],
        ),
        (
            "睡眠模式",
            "关闭灯光并调整卧室空调。",
            [
                ("卧室", "灯", {"is_on": False}),
                ("卧室", "空调", {"is_on": True, "properties": {"temperature": 26, "mode": "睡眠"}}),
                ("卧室", "窗帘", {"is_on": False, "properties": {"open_percent": 0}}),
            ],
        ),
        (
            "离家模式",
            "关闭主要用电设备。",
            [
                ("客厅", "灯", {"is_on": False}),
                ("客厅", "空调", {"is_on": False}),
                ("客厅", "电视", {"is_on": False}),
                ("厨房", "排风扇", {"is_on": False}),
                ("书房", "空调", {"is_on": False}),
            ],
        ),
    ]

    for scene_name, description, actions in scene_specs:
        scene = Scene(home_id=home.id, name=scene_name, description=description)
        db.add(scene)
        db.flush()
        for index, (room_name, device_name, target_state) in enumerate(actions, start=1):
            db.add(
                SceneAction(
                    scene_id=scene.id,
                    device_id=devices[(room_name, device_name)].id,
                    action="set_state",
                    target_state=target_state,
                    sort_order=index,
                )
            )

    db.commit()
    print("数据库初始化完成。")


def init_db() -> None:
    create_tables()
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
