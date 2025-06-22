from sqlalchemy.orm import Session
from . import SessionLocal
from .models import Guild, User, GuildUser, VCSummary, VCSession
import logging
import time
from datetime import datetime, timezone
from contextlib import contextmanager

logger = logging.getLogger('discord')

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        logger.error(f"datebase error: {e}")
    finally:
        session.close()

class FormatTime:
    def __init__(self, hour, minute, second):
        self.hour = hour
        self.minute = minute
        self.second = second
    def __str__(self):
        return f'{self.hour:03d}時間 {self.minute:02d}分 {self.second:02d}秒'

def formatTime(seconds: int):
    hour = seconds // 3600
    minute = (seconds % 3600) // 60
    second = seconds % 60
    return FormatTime(hour, minute, second)

def checkExistsGuild(session: Session, guild_id: int):
    guild = session.query(Guild).filter_by(guild_id=guild_id).one_or_none()
    if guild is None:
        guild = Guild(guild_id=guild_id)
        session.add(guild)
    session.commit()

def checkExistsUser(session: Session, user_id: int):
    user = session.query(User).filter_by(user_id=user_id).one_or_none()
    if user is None:
        user = User(user_id=user_id)
        session.add(user)
    session.commit()

def checkExistsGuildUser(session: Session, guild_id: int, user_id: int):
    checkExistsGuild(session, guild_id)
    checkExistsUser(session, user_id)
    guild_user = session.query(GuildUser).filter_by(guild_id=guild_id, user_id=user_id).one_or_none()
    if guild_user is None:
        join_date = int(time.time())
        guild_user = GuildUser(guild_id=guild_id, user_id=user_id, join_date=join_date)
        session.add(guild_user)
    session.commit()

def checkExistsVCSummary(session: Session, id: int, channel_id: int, year: int, month: int):
    vc_summary = session.query(VCSummary).filter_by(id=id, channel_id=channel_id, year=year, month=month).one_or_none()
    if vc_summary is None:
        vc_summary = VCSummary(id=id, channel_id=channel_id, year=year, month=month)
        session.add(vc_summary)
    session.commit()

def updateServerNotificationChannel(session: Session, guild_id: int, notificationChannel_id: int):
    checkExistsGuild(session, guild_id)
    guild = session.query(Guild).filter_by(guild_id=guild_id).one()
    guild.notification_channel = notificationChannel_id
    session.commit()

def readServerSetting(session: Session, guild_id: int):
    checkExistsGuild(session, guild_id)
    guild = session.query(Guild).filter_by(guild_id=guild_id).one()
    return guild

def addUserCount(session: Session, user_id: int):
    checkExistsUser(session, user_id)
    session.commit()
    user = session.query(User).filter_by(user_id=user_id).one()
    user.command_count += 1
    session.commit()

def readVcSummary(session: Session, guild_id: int, user_id: int, channel_id: int, year: int = None, month: int = None):
    checkExistsGuildUser(session, guild_id, user_id)
    now_utc = datetime.now(timezone.utc)
    guild_user = session.query(GuildUser).filter_by(guild_id=guild_id, user_id=user_id).one()
    if month is None and year is not None:
        vc_summary = session.query(VCSummary).filter_by(id=guild_user.id, channel_id=channel_id, year=year).all()
        total_connection_time = sum(s.total_connection_time for s in vc_summary)
        total_mic_on_time = sum(s.total_mic_on_time for s in vc_summary)
        connection_time = formatTime(total_connection_time)
        mic_on_time = formatTime(total_mic_on_time)
    else:
        year = year or now_utc.year
        month = month or now_utc.month
        checkExistsVCSummary(session, id=guild_user.id, channel_id=channel_id, year=year, month=month)
        vc_summary = session.query(VCSummary).filter_by(id=guild_user.id, channel_id=channel_id, year=year, month=month).one()
        connection_time = formatTime(vc_summary.total_connection_time)
        mic_on_time = formatTime(vc_summary.total_mic_on_time)
    return connection_time, mic_on_time

def clearVcSessions(session: Session):
    session.query(VCSession).delete()
    session.commit()
    logger.info("cleared vc_sessions table")

def addVcSessions(session: Session, guild_id: int, user_id: int, channel_id: int, mic_on: bool):
    checkExistsGuildUser(session, guild_id, user_id)
    event_time = int(time.time())
    guild_user = session.query(GuildUser).filter_by(guild_id=guild_id, user_id=user_id).one_or_none()
    vc_session = VCSession(id=guild_user.id, channel_id=channel_id, event_time=event_time, mic_on=mic_on)
    session.add(vc_session)
    session.commit()

def endVcSessions(session: Session, guild_id: int, user_id: int, channel_id: int, mic_on: bool, startup_time: int):
    checkExistsGuildUser(session, guild_id, user_id)
    end_time = int(time.time())
    now_utc = datetime.now(timezone.utc)
    guild_user = session.query(GuildUser).filter_by(guild_id=guild_id, user_id=user_id).one()
    checkExistsVCSummary(session, id=guild_user.id, channel_id=channel_id, year=now_utc.year, month=now_utc.month)
    vc_session = session.query(VCSession).filter_by(id=guild_user.id, channel_id=channel_id).one_or_none()
    if vc_session is None:
        elapsed_time = end_time - startup_time
        mic_on_session = mic_on
    else:
        elapsed_time = end_time - vc_session.event_time
        mic_on_session = vc_session.mic_on
        session.delete(vc_session)
    
    if mic_on and mic_on_session:
        vc_summary = session.query(VCSummary).filter_by(id=guild_user.id, channel_id=channel_id, year=now_utc.year, month=now_utc.month).one()
        vc_summary.total_connection_time += elapsed_time
        vc_summary.total_mic_on_time += elapsed_time
        logger.debug("mic_on and mic_on_session")
    elif not mic_on and not mic_on_session:
        vc_summary = session.query(VCSummary).filter_by(id=guild_user.id, channel_id=channel_id, year=now_utc.year, month=now_utc.month).one()
        vc_summary.total_connection_time += elapsed_time
        logger.debug("not mic_on and not mic_on_session")
    else:
        logger.error(f'Integrity violation argument: {mic_on} db: {mic_on_session}')
    session.commit()