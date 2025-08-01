from sqlalchemy import (
    Column, Integer, ForeignKey, String, TIMESTAMP, create_engine, PrimaryKeyConstraint, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

class ReprMixin:
    def __repr__(self):
        values = ', '.join(
            f"{column.name}={getattr(self, column.name)}"
            for column in self.__table__.columns
        )
        return f"<{self.__class__.__name__}({values})>"


class Guild(ReprMixin, Base):
    __tablename__ = "guilds"
    guild_id = Column(Integer, primary_key=True)
    notification_channel = Column(Integer, nullable=True)

class User(ReprMixin, Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    speaker_id = Column(Integer, default=1)
    command_count = Column(Integer, default=0)
    likeability = Column(Integer, default=0)

class GuildUser(ReprMixin, Base):
    __tablename__ = "guild_users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(Integer, ForeignKey("guilds.guild_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    join_date = Column(Integer, nullable=True)
    __table_args__ = (
        UniqueConstraint('guild_id', 'user_id', name='_guild_user_uc'),
    )

class VCSummary(ReprMixin, Base):
    __tablename__ = "vc_summary"
    id = Column(Integer, ForeignKey("guild_users.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, nullable=False)
    year = Column(Integer, nullable=True)
    month = Column(Integer, nullable=True)
    total_connection_time = Column(Integer, default=0)
    total_mic_on_time = Column(Integer, default=0)
    __table_args__ = (
        PrimaryKeyConstraint("id", "channel_id", "year", "month"),
    )

class VCSession(ReprMixin, Base):
    __tablename__ = "vc_sessions"
    id = Column(Integer, ForeignKey("guild_users.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, nullable=False)
    event_time = Column(Integer, nullable=False)
    mic_on = Column(Integer, nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint("id", "channel_id"),
    )
