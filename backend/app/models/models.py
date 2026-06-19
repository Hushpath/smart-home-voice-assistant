from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Home(Base):
    __tablename__ = "homes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    address = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    users = relationship("User", back_populates="home")
    rooms = relationship("Room", back_populates="home", cascade="all, delete-orphan")
    scenes = relationship("Scene", back_populates="home", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(100), nullable=True)
    home_id = Column(Integer, ForeignKey("homes.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    home = relationship("Home", back_populates="users")
    command_logs = relationship("CommandLog", back_populates="user")
    reminders = relationship("Reminder", back_populates="user")
    status_history = relationship("DeviceStatusHistory", back_populates="user")
    preference = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    device_aliases = relationship("DeviceAlias", back_populates="user", cascade="all, delete-orphan")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    home_id = Column(Integer, ForeignKey("homes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    home = relationship("Home", back_populates="rooms")
    devices = relationship("Device", back_populates="room", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    device_type = Column(String(50), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    is_on = Column(Boolean, default=False, nullable=False)
    is_online = Column(Boolean, default=True, nullable=False)
    properties = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    room = relationship("Room", back_populates="devices")
    status_history = relationship("DeviceStatusHistory", back_populates="device")
    scene_actions = relationship("SceneAction", back_populates="device")
    aliases = relationship("DeviceAlias", back_populates="device", cascade="all, delete-orphan")


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_preferences_user_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    preferred_dialect = Column(String(20), default="auto", nullable=False)
    preferred_input_mode = Column(String(30), default="browser_speech", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="preference")


class DeviceAlias(Base):
    __tablename__ = "device_aliases"
    __table_args__ = (UniqueConstraint("user_id", "alias", name="uq_device_aliases_user_alias"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    alias = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="device_aliases")
    device = relationship("Device", back_populates="aliases")


class CommandLog(Base):
    __tablename__ = "command_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    raw_command = Column(Text, nullable=False)
    parsed_result = Column(JSON, nullable=True)
    execution_result = Column(JSON, nullable=True)
    success = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="command_logs")


class DeviceStatusHistory(Base):
    __tablename__ = "device_status_history"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    before_state = Column(JSON, nullable=False)
    after_state = Column(JSON, nullable=False)
    change_source = Column(String(50), nullable=False, default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    device = relationship("Device", back_populates="status_history")
    user = relationship("User", back_populates="status_history")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    remind_time = Column(DateTime(timezone=True), nullable=True)
    is_done = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="reminders")


class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, index=True)
    home_id = Column(Integer, ForeignKey("homes.id"), nullable=False)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    home = relationship("Home", back_populates="scenes")
    actions = relationship("SceneAction", back_populates="scene", cascade="all, delete-orphan")


class SceneAction(Base):
    __tablename__ = "scene_actions"

    id = Column(Integer, primary_key=True, index=True)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    action = Column(String(50), nullable=False)
    target_state = Column(JSON, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    scene = relationship("Scene", back_populates="actions")
    device = relationship("Device", back_populates="scene_actions")
