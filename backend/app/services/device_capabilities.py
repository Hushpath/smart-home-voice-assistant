from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PropertyCapability:
    property_name: str
    label: str
    value_type: str
    aliases: tuple[str, ...]
    minimum: int | None = None
    maximum: int | None = None
    options: tuple[Any, ...] = ()
    option_aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)


DEVICE_CAPABILITIES: dict[str, tuple[PropertyCapability, ...]] = {
    "light": (
        PropertyCapability("brightness", "亮度", "number", ("亮度", "灯光亮度", "光度"), 0, 100),
        PropertyCapability(
            "color_temperature",
            "色温",
            "enum",
            ("色温", "灯光色温", "颜色温度", "光色"),
            options=("暖黄", "暖白", "自然光", "冷白"),
        ),
    ),
    "desk_lamp": (
        PropertyCapability("brightness", "亮度", "number", ("亮度", "台灯亮度", "光度"), 0, 100),
        PropertyCapability(
            "color_temperature",
            "色温",
            "enum",
            ("色温", "台灯色温", "颜色温度", "光色"),
            options=("暖黄", "暖白", "自然光", "冷白"),
        ),
    ),
    "bedside_lamp": (
        PropertyCapability("brightness", "亮度", "number", ("亮度", "床头灯亮度", "光度"), 0, 100),
        PropertyCapability(
            "color_temperature",
            "色温",
            "enum",
            ("色温", "床头灯色温", "颜色温度", "光色"),
            options=("暖黄", "暖白", "自然光", "冷白"),
        ),
    ),
    "air_conditioner": (
        PropertyCapability("temperature", "温度", "number", ("温度", "空调温度", "度数"), 16, 30),
        PropertyCapability(
            "mode",
            "模式",
            "enum",
            ("模式", "空调模式", "运行模式"),
            options=("制冷", "制热", "除湿", "送风", "睡眠"),
            option_aliases={"睡眠": ("睡眠模式",)},
        ),
        PropertyCapability(
            "fan_speed",
            "风量",
            "enum",
            ("风量", "风速", "空调风量", "空调风速", "风档", "档位"),
            options=("低速", "中速", "高速", "自动"),
            option_aliases={
                "低速": ("低档", "低风", "小风"),
                "中速": ("中档", "中风"),
                "高速": ("高档", "高风", "大风"),
            },
        ),
    ),
    "tv": (
        PropertyCapability("volume", "音量", "number", ("音量", "电视音量", "声音", "声量"), 0, 100),
        PropertyCapability(
            "channel",
            "频道",
            "enum",
            ("频道", "电视台", "台"),
            options=("CCTV-1", "CCTV-5", "CCTV-13", "湖南卫视", "浙江卫视"),
            option_aliases={
                "CCTV-1": ("CCTV1", "央视一套", "中央一台", "一套"),
                "CCTV-5": ("CCTV5", "央视五套", "体育频道", "五套"),
                "CCTV-13": ("CCTV13", "央视十三套", "新闻频道", "十三套"),
            },
        ),
    ),
    "curtain": (
        PropertyCapability("open_percent", "开合比例", "number", ("开合比例", "开合", "开度", "打开比例", "开启比例"), 0, 100),
    ),
    "fan": (
        PropertyCapability(
            "speed",
            "风速",
            "enum",
            ("风速", "风量", "排风扇风速", "排风扇风量", "档位", "速度"),
            options=("低速", "中速", "高速"),
            option_aliases={
                "低速": ("低档", "低风", "小风"),
                "中速": ("中档", "中风"),
                "高速": ("高档", "高风", "大风"),
            },
        ),
    ),
    "speaker": (
        PropertyCapability("volume", "音量", "number", ("音量", "音箱音量", "声音", "声量"), 0, 100),
        PropertyCapability("mode", "模式", "enum", ("模式", "音箱模式", "播放模式"), options=("待机", "播放", "静音")),
    ),
    "humidifier": (
        PropertyCapability("humidity_target", "目标湿度", "number", ("目标湿度", "湿度", "加湿湿度"), 30, 80),
        PropertyCapability("mode", "模式", "enum", ("模式", "加湿模式"), options=("低档", "自动", "睡眠")),
    ),
    "air_purifier": (
        PropertyCapability("mode", "模式", "enum", ("模式", "净化模式", "档位"), options=("低速", "自动", "强力")),
    ),
    "smart_plug": (
        PropertyCapability("power_watt", "功率", "number", ("功率", "当前功率", "瓦数"), 0, 2400),
    ),
    "fridge": (
        PropertyCapability("temperature", "冷藏温度", "number", ("冷藏温度", "冰箱温度", "温度"), 2, 8),
        PropertyCapability("mode", "模式", "enum", ("模式", "冰箱模式"), options=("保鲜", "节能", "速冷")),
    ),
}


LEGACY_PROPERTY_INTENTS = {
    ("air_conditioner", "temperature"): "set_temperature",
    ("light", "brightness"): "set_brightness",
    ("desk_lamp", "brightness"): "set_brightness",
    ("bedside_lamp", "brightness"): "set_brightness",
    ("tv", "volume"): "set_volume",
    ("speaker", "volume"): "set_volume",
}


def get_device_capabilities(device_type: str | None) -> tuple[PropertyCapability, ...]:
    if not device_type:
        return ()
    return DEVICE_CAPABILITIES.get(device_type, ())


def get_property_capability(device_type: str | None, property_name: str | None) -> PropertyCapability | None:
    for capability in get_device_capabilities(device_type):
        if capability.property_name == property_name:
            return capability
    return None


def iter_device_capabilities() -> list[tuple[str, PropertyCapability]]:
    return [
        (device_type, capability)
        for device_type, capabilities in DEVICE_CAPABILITIES.items()
        for capability in capabilities
    ]


def all_property_aliases() -> list[str]:
    aliases = {
        alias
        for _, capability in iter_device_capabilities()
        for alias in capability.aliases
    }
    return sorted(aliases, key=len, reverse=True)


def all_option_aliases() -> list[tuple[str, Any]]:
    aliases: list[tuple[str, Any]] = []
    for _, capability in iter_device_capabilities():
        aliases.extend(option_aliases(capability))
    unique: dict[str, Any] = {}
    for alias, option in aliases:
        unique.setdefault(alias, option)
    return sorted(unique.items(), key=lambda item: len(item[0]), reverse=True)


def legacy_intent_for_property(device_type: str | None, property_name: str | None) -> str | None:
    if device_type is None or property_name is None:
        return None
    return LEGACY_PROPERTY_INTENTS.get((device_type, property_name))


def option_aliases(capability: PropertyCapability) -> list[tuple[str, Any]]:
    aliases: list[tuple[str, Any]] = []
    for option in capability.options:
        aliases.append((str(option), option))
        for alias in capability.option_aliases.get(str(option), ()):
            aliases.append((alias, option))
    return sorted(aliases, key=lambda item: len(item[0]), reverse=True)
