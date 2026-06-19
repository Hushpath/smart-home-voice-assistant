from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import Device, Home, Room, Scene, SceneAction, User

ROOM_NAMES = ["客厅", "卧室", "厨房", "书房"]

DEVICE_SPECS = [
    ("客厅", "灯", "light", False, True, {"brightness": 60, "color_temperature": "暖白"}),
    ("客厅", "空调", "air_conditioner", False, True, {"temperature": 26, "mode": "制冷", "fan_speed": "自动"}),
    ("客厅", "电视", "tv", False, True, {"volume": 20, "channel": "CCTV-1"}),
    ("客厅", "窗帘", "curtain", False, True, {"open_percent": 0}),
    ("客厅", "扫地机器人", "robot_vacuum", False, True, {"mode": "待机", "battery": 92}),
    ("客厅", "音箱", "speaker", False, True, {"volume": 35, "mode": "待机"}),
    ("卧室", "灯", "light", False, True, {"brightness": 40, "color_temperature": "暖黄"}),
    ("卧室", "空调", "air_conditioner", False, True, {"temperature": 26, "mode": "制冷", "fan_speed": "低速"}),
    ("卧室", "窗帘", "curtain", False, True, {"open_percent": 0}),
    ("卧室", "床头灯", "bedside_lamp", False, True, {"brightness": 35, "color_temperature": "暖黄"}),
    ("卧室", "加湿器", "humidifier", False, True, {"humidity_target": 55, "mode": "自动"}),
    ("厨房", "灯", "light", False, True, {"brightness": 70, "color_temperature": "自然光"}),
    ("厨房", "排风扇", "fan", False, True, {"speed": "中速"}),
    ("厨房", "冰箱", "fridge", True, True, {"temperature": 4, "mode": "保鲜"}),
    ("厨房", "烟雾传感器", "smoke_sensor", True, True, {"status": "正常", "battery": 88}),
    ("书房", "灯", "light", False, True, {"brightness": 75, "color_temperature": "冷白"}),
    ("书房", "空调", "air_conditioner", False, True, {"temperature": 25, "mode": "制冷", "fan_speed": "自动"}),
    ("书房", "台灯", "desk_lamp", False, True, {"brightness": 65, "color_temperature": "冷白"}),
    ("书房", "空气净化器", "air_purifier", False, True, {"mode": "自动", "air_quality": "良"}),
    ("书房", "智能插座", "smart_plug", False, True, {"power_watt": 0}),
]

SCENE_SPECS = [
    (
        "回家模式",
        "打开客厅常用设备，营造回家环境。",
        [
            ("客厅", "灯", {"is_on": True, "properties": {"brightness": 80}}),
            ("客厅", "空调", {"is_on": True, "properties": {"temperature": 26, "mode": "制冷"}}),
            ("客厅", "电视", {"is_on": True, "properties": {"volume": 20}}),
            ("客厅", "音箱", {"is_on": True, "properties": {"volume": 35, "mode": "播放"}}),
            ("客厅", "扫地机器人", {"is_on": False, "properties": {"mode": "充电"}}),
        ],
    ),
    (
        "睡眠模式",
        "关闭灯光并调整卧室环境。",
        [
            ("卧室", "灯", {"is_on": False}),
            ("卧室", "床头灯", {"is_on": True, "properties": {"brightness": 20, "color_temperature": "暖黄"}}),
            ("卧室", "空调", {"is_on": True, "properties": {"temperature": 26, "mode": "睡眠"}}),
            ("卧室", "加湿器", {"is_on": True, "properties": {"humidity_target": 55, "mode": "睡眠"}}),
            ("卧室", "窗帘", {"is_on": False, "properties": {"open_percent": 0}}),
        ],
    ),
    (
        "离家模式",
        "关闭主要用电设备，保留安全设备运行。",
        [
            ("客厅", "灯", {"is_on": False}),
            ("客厅", "空调", {"is_on": False}),
            ("客厅", "电视", {"is_on": False}),
            ("客厅", "音箱", {"is_on": False}),
            ("厨房", "排风扇", {"is_on": False}),
            ("书房", "空调", {"is_on": False}),
            ("书房", "灯", {"is_on": False}),
            ("书房", "台灯", {"is_on": False}),
            ("书房", "智能插座", {"is_on": False, "properties": {"power_watt": 0}}),
        ],
    ),
]


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_initial_data(db: Session) -> None:
    home = db.query(Home).filter(Home.name == "默认家庭").first()
    if home is None:
        home = Home(name="默认家庭", address="课程设计虚拟家庭")
        db.add(home)
        db.flush()

    rooms: dict[str, Room] = {}
    for room_name in ROOM_NAMES:
        room = db.query(Room).filter(Room.name == room_name, Room.home_id == home.id).first()
        if room is None:
            room = Room(name=room_name, home_id=home.id)
            db.add(room)
            db.flush()
        rooms[room_name] = room

    devices: dict[tuple[str, str], Device] = {}
    for room_name, name, device_type, is_on, is_online, properties in DEVICE_SPECS:
        room = rooms[room_name]
        device = db.query(Device).filter(Device.room_id == room.id, Device.name == name).first()
        if device is None:
            device = Device(
                name=name,
                device_type=device_type,
                room_id=room.id,
                is_on=is_on,
                is_online=is_online,
                properties=properties,
            )
            db.add(device)
            db.flush()
        devices[(room_name, name)] = device

    user = db.query(User).filter(User.username == "testuser").first()
    if user is None:
        user = User(
            username="testuser",
            password_hash=hash_password("test123456"),
            nickname="默认测试用户",
            home_id=home.id,
            is_active=True,
        )
        db.add(user)
    elif user.home_id != home.id:
        user.home_id = home.id

    for scene_name, description, actions in SCENE_SPECS:
        scene = db.query(Scene).filter(Scene.home_id == home.id, Scene.name == scene_name).first()
        if scene is None:
            scene = Scene(home_id=home.id, name=scene_name, description=description)
            db.add(scene)
            db.flush()
        else:
            scene.description = description
        for index, (room_name, device_name, target_state) in enumerate(actions, start=1):
            device = devices[(room_name, device_name)]
            action = db.query(SceneAction).filter(SceneAction.scene_id == scene.id, SceneAction.device_id == device.id).first()
            if action is None:
                action = SceneAction(
                    scene_id=scene.id,
                    device_id=device.id,
                    action="set_state",
                )
                db.add(action)
            action.target_state = target_state
            action.sort_order = index

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
