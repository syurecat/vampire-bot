import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import random
import time
import json
import uuid
import traceback
import asyncio
import logging
import logging.handlers
from rich.logging import RichHandler
from datetime import datetime
from version import VERSION
from database import init_db
import database.crud as crud
from database.crud import get_session

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
CONSOLE_LEVEL_NAME = os.getenv("CONSOLE_LOG_LEVEL", "INFO").upper()
FILE_LEVEL_NAME = os.getenv("FILE_LOG_LEVEL", "DEBUG").upper()
LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
ADVANCED_LEVEL_NAME = os.getenv("ADVANCED_LOG_LEVEL", "WARNING").upper()
EVENT_LEVEL_NAME = os.getenv("EVENT_LOG_LEVEL", "INFO").upper()
CONSOLE_LOG_LEVEL = getattr(logging, CONSOLE_LEVEL_NAME, logging.INFO)
FILE_LOG_LEVEL = getattr(logging, FILE_LEVEL_NAME, logging.DEBUG)
LOG_LEVEL = getattr(logging, LEVEL_NAME, logging.DEBUG)
ADVANCED_LOG_LEVEL = getattr(logging, ADVANCED_LEVEL_NAME, logging.INFO)
EVENT_LOG_LEVEL = getattr(logging, EVENT_LEVEL_NAME, logging.INFO)
startup_time = int(time.time())
memes_enabled = True

# logging setting reset
root = logging.getLogger()
root.setLevel(logging.DEBUG)
root.handlers.clear()

# logging setting
LOG_CONSOLE_FMT = ' %(name)s: %(message)s'
LOG_FILE_FMT  = '[%(asctime)s.%(msecs)03d] [%(levelname)-8s] %(name)s: %(message)s'
DATE_FMT = '%Y-%m-%d %H:%M:%S'

# console
console_handler = RichHandler(
    markup=True,
    rich_tracebacks=True
)
console_handler.setLevel(CONSOLE_LOG_LEVEL)
console_handler.setFormatter(logging.Formatter(LOG_CONSOLE_FMT, DATE_FMT))
root.addHandler(console_handler)

# log file
file_handler = logging.handlers.RotatingFileHandler(
    filename='log/vampire.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,
    backupCount=7,
)
file_handler.setLevel(FILE_LOG_LEVEL)
file_handler.setFormatter(logging.Formatter(LOG_FILE_FMT, DATE_FMT))
root.addHandler(file_handler)  

error_handler = logging.handlers.RotatingFileHandler(
    filename='log/error.log',
    encoding='utf-8',
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter(LOG_FILE_FMT, DATE_FMT))
root.addHandler(error_handler)

# Discord log setting
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(LOG_LEVEL)

# SQLAlchemy log setting
sqlalchemy_logger = logging.getLogger('sqlalchemy')
sqlalchemy_logger.setLevel(LOG_LEVEL)

logging.getLogger('discord.client').setLevel(EVENT_LOG_LEVEL)
logging.getLogger('discord.dispatcher').setLevel(EVENT_LOG_LEVEL)
logging.getLogger('discord.http').setLevel(ADVANCED_LOG_LEVEL)
logging.getLogger('discord.gateway').setLevel(ADVANCED_LOG_LEVEL)
logging.getLogger('sqlalchemy.engine').setLevel(ADVANCED_LOG_LEVEL)
logging.getLogger('sqlalchemy.orm').setLevel(ADVANCED_LOG_LEVEL)
logging.getLogger('sqlalchemy.pool').setLevel(ADVANCED_LOG_LEVEL)

logger = logging.getLogger('vampire')
logger.info(f"Logging start")
logger.info(f"Log Levels - Console: {CONSOLE_LEVEL_NAME}, File: {FILE_LEVEL_NAME}, Event: {EVENT_LEVEL_NAME}")
logger.info(f"Version: {VERSION}")

# 初期準備
def log_error(error: Exception, context: str = "") -> str:
    error_code = f"E-{uuid.uuid4()}"
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    logger.error(f"{error_code} | {context}\n{tb}")
    return error_code

if not DISCORD_TOKEN:
    logger.critical("DISCORD_TOKEN is not set. The bot cannot start.")
    raise ValueError("DISCORD_TOKEN is missing. Please set the environment variable.")

init_db()
try:
    with open("messages/memes.json", "r", encoding="utf-8") as f:
        meme_dict = json.load(f)
except FileNotFoundError:
    logger.warning("memes.json not found. Meme feature disabled.")
    memes_enabled = False
except json.JSONDecodeError:
    logger.warning("memes.json is invalid. Check JSON format. Meme feature disabled.")
    memes_enabled = False
except Exception as e:
    logger.warning(f"Unexpected error loading memes.json: {e}. Meme feature disabled.")
    memes_enabled = False

trigger_set = set(meme_dict.keys())

# Discord
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
# Command Group
serverSettings = app_commands.Group(name="server-settings", description="サーバー設定", guild_only=True, default_permissions=discord.Permissions(manage_guild=True))

@client.event
async def on_ready():
    logger.info(f"Bot is ready as {client.user} (ID: {client.user.id})")
    logger.info(f"Connected to {len(client.guilds)} guild(s)")
    logger.info(f"Startup Time: {datetime.fromtimestamp(startup_time)}")

    logger.debug("Debug ON")
    with get_session() as session:
        crud.clearVcSessions(session)
    await tree.sync()

@client.event
async def on_guild_join(guild):
    logger.info(f"Joined the guild {guild.name} id={guild.id}")
    message = f"初めまして！{guild.name}の皆さん！\n{client.user.name}です！"
    if guild.system_channel:
        if guild.system_channel.permissions_for(guild.me).send_messages:
            await guild.system_channel.send(message)
            return

    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send(message)
            return

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.author.bot:
        return
    
    if message.guild:
        permissions = message.channel.permissions_for(message.guild.me)
        if not permissions.send_messages:   
            return

    content = message.content.strip()

    if client.user in message.mentions:
        await message.channel.send(f"{message.author.mention} 呼んだ？")

    if isinstance(message.channel, discord.DMChannel):
        return
    
    if not memes_enabled:
        return

    if content in trigger_set:
        responses = meme_dict[content]
        response = random.choice(responses)
        logger.debug(f"Triggered meme response to '{content}' by {message.author} in {message.guild.name}")
        await message.channel.send(response)


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    error_code = log_error(error, f"user={interaction.user} command={interaction.command}")
    if not interaction.response.is_done():
        await interaction.response.send_message(f"予期しないエラーが発生しました (エラーコード: `{error_code}`)", ephemeral=True)


async def ping(interaction: discord.Interaction):
    logger.debug(f"{interaction.user.id} executed /ping command in {f"guild id={interaction.guild.id}" if interaction.guild else f"{interaction.channel.type.name} id={interaction.channel.id}"}")
    with get_session() as session:
        crud.addUserCount(session, interaction.user.id)
    await interaction.response.send_message("pong!")

@tree.command(name = 'ping', description = 'pingを返します')
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ping_slash(interaction: discord.Interaction):
    await ping(interaction = interaction)


async def notification_channel(interaction: discord.Integration, channel: discord.TextChannel):
    logger.debug(f"{interaction.user.id} executed /notification-channel command in {f"guild id={interaction.guild.id}" if interaction.guild else f"{interaction.channel.type.name} id={interaction.channel.id}"}")
    with get_session() as session:
        crud.updateServerNotificationChannel(session, interaction.guild.id, channel.id)
    await interaction.response.send_message(f"通知チャンネルを <#{channel.id}> に設定しました！")

@serverSettings.command(name = 'notification-channel', description = 'botの通知チャンネルを変更します。')
@app_commands.describe(channel="通知するチャンネル")
async def notification_channel_slash(interaction: discord.Integration, channel: discord.TextChannel):
    await notification_channel(interaction = interaction, channel = channel)


async def vc_log(interaction: discord.Interaction, channel: discord.VoiceChannel, year: app_commands.Range[int, 2025, 2099] = None, month: app_commands.Range[int, 1, 12] = None, ephemeral: bool = True):
    try:
        with get_session() as session:
            connection_time, mic_on_time  = crud.readVcSummary(session, interaction.guild.id, interaction.user.id, channel.id, year, month)
    except crud.FutureDateError:
        await interaction.response.send_message(f"ごめんね～\n私、未来のことはわかんないんだよね......\nその時まで一緒にいれると嬉しいな！", ephemeral=True)
        return
    except crud.NoDataError:
        await interaction.response.send_message(f"{year or datetime.now().year}年 {month or datetime.now().month}月のデータがなかったよ！", ephemeral = ephemeral)
        return
    logger.debug(f"{interaction.user.id} queried vc-time for {channel.name}: Connection Time: {connection_time}, Mic Time: {mic_on_time}")
    if year is not None and month is None:
        await interaction.response.send_message(f"{year or datetime.now().year}年に <#{channel.id}> に接続していた時間の発表です！\n接続時間: {connection_time}\nミュート: {mic_on_time}", ephemeral = ephemeral)
    else:
        await interaction.response.send_message(f"{year or datetime.now().year}年 {month or datetime.now().month}月に <#{channel.id}> に接続していた時間の発表です！\n接続時間: {connection_time}\nミュート: {mic_on_time}", ephemeral = ephemeral)

@tree.command(name= 'vc-time', description= 'あなたのvc接続時間を表示します。')
@app_commands.guild_only()
@app_commands.describe(channel="閲覧するチャンネル", ephemeral="自分にしか表示しないかどうかです。defaultでTrueです。")
async def vc_log_slash(interaction: discord.Interaction, channel: discord.VoiceChannel, year: app_commands.Range[int, 2025, 2099] = None, month: app_commands.Range[int, 1, 12] = None, ephemeral: bool = True):
    await vc_log(interaction = interaction, channel = channel, year = year, month = month, ephemeral = ephemeral)


async def vc_rank(interaction: discord.Integration, channel: discord.VoiceChannel = None, year: app_commands.Range[int, 2025, 2099] = None, month: app_commands.Range[int, 1, 12] = None, ephemeral: bool = False):
    channel_id = channel.id if channel is not None else None
    user_nodata = False
    try:
        with get_session() as session:
            vc_rank = crud.readVcRankEntries(session, interaction.guild.id, channel_id, year, month)
            user_rank = crud.readUserVcRankEntry(session, interaction.guild.id, interaction.user.id, channel_id, year, month)
    except crud.FutureDateError:
        await interaction.response.send_message(f"ごめんね～\n私、未来のことはわかんないんだよね......\nその時まで一緒にいれると嬉しいな！", ephemeral=True)
        return
    except crud.NoDataError:
        user_nodata = True
    logger.debug(f"{interaction.user.id} queried vc-rank for {interaction.guild.id}/{channel_id}: {vc_rank}")
    await interaction.response.defer(thinking=True)

    lines = []
    channel_display = f"<#{channel_id}>" if channel is not None else interaction.guild.name
    lines.append(f"{year or datetime.now().year}年 {month or datetime.now().month}月に {channel_display} に接続していた人のランキングの発表です！")
    if vc_rank.entries:
        for entry in vc_rank.entries:
            member = interaction.guild.get_member(entry.user_id)
            if member is None:
                member = await interaction.guild.fetch_member(entry.user_id)
            name = member.display_name if member else "unknown"
            lines.append(f"{entry.rank}位 {name} | 接続: {entry.total_connection_time} | マイク: {entry.total_mic_on_time}")
    else:
        lines.append(f"データなし")
    if not user_nodata:
        lines.append(f"{user_rank.rank}位 {interaction.user.display_name} | 接続: {user_rank.total_connection_time} | マイク: {user_rank.total_mic_on_time}")

    await interaction.followup.send("\n".join(lines))

@tree.command(name= 'vc-rank', description= 'あなたのvc接続時間を表示します。')
@app_commands.guild_only()
@app_commands.describe(channel="閲覧するチャンネル", ephemeral="自分にしか表示しないかどうかです。defaultでFalseです。")
async def vc_rank_slash(interaction: discord.Integration, channel: discord.VoiceChannel = None, year: app_commands.Range[int, 2025, 2099] = None, month: app_commands.Range[int, 1, 12] = None, ephemeral: bool = False):
        await vc_rank(interaction = interaction, channel = channel, year = year, month = month, ephemeral = ephemeral)


async def rps(interaction: discord.Interaction):
    logger.debug(f"{interaction.user.id} executed /rps command in {f"guild id={interaction.guild.id}" if interaction.guild else f"{interaction.channel.type.name} id={interaction.channel.id}"}")
    with get_session() as session:
        crud.addUserCount(session, interaction.user.id)
    if random.randint(1, 100) == 1:
        await interaction.response.send_message(":hand_with_index_finger_and_thumb_crossed:")
    else:
        faces = ["✊", "✌️", "🖐️"]
        await interaction.response.send_message(f'{random.choice(faces)}')

@tree.command(name = 'rps', description = 'じゃんけんをします。')
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def rps_slash(interaction: discord.Interaction, ):
    await rps(interaction = interaction)


def judge(player, bot):
    if player == bot:
        return "あいこでしょ！"
    if bot == ":hand_with_index_finger_and_thumb_crossed:":
        return "えへへっ"
    elif (player == "✊" and bot == "✌️") or \
         (player == "✌️" and bot == "🖐️") or \
         (player == "🖐️" and bot == "✊"):
        return "あれれ?まけちゃった......"
    else:
        return "私の勝ち！"

class rpsMeView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="✊", style=discord.ButtonStyle.primary)
    async def rock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.janken_result(interaction, "✊")

    @discord.ui.button(label="✌️", style=discord.ButtonStyle.success)
    async def scissors_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.janken_result(interaction, "✌️")

    @discord.ui.button(label="🖐️", style=discord.ButtonStyle.danger)
    async def paper_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.janken_result(interaction, "🖐️")

    async def janken_result(self, interaction: discord.Interaction, player_choice):
        try:
            if random.randint(1, 160) == 1:
                bot_choice = ":hand_with_index_finger_and_thumb_crossed:"
            else:
                faces = ["✊", "✌️", "🖐️"]
                bot_choice = random.choice(faces)
            result = judge(player_choice, bot_choice)
            await interaction.message.edit(
                content = f"わたし: {bot_choice} vs {player_choice} :あなた\n{result}",
                view = None
            )
        except discord.Forbidden:
            logger.debug(f"Missing Access when trying to edit message (ID: {interaction.message.id}) in channel (ID: {interaction.channel.id}) by user (ID: {interaction.user.id}")
            pass


async def rps_me(interaction: discord.Integration):
    logger.debug(f"{interaction.user.id} executed /rps-me command in {f"guild id={interaction.guild.id}" if interaction.guild else f"{interaction.channel.type.name} id={interaction.channel.id}"}")
    with get_session() as session:
        crud.addUserCount(session, interaction.user.id)
    if random.randint(1, 250) == 1:
        await interaction.response.send_message("zzz...")
    else:
        view = rpsMeView()
        await interaction.response.send_message("じゃんけん...\n||現状権限が無いとエラーを吐くよ？ごめんね||", view = view)

@tree.command(name = 'rps-me', description = '私とじゃんけんをしよう！')
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=False)
async def rps_me_slash(interaction: discord.Integration):
    await rps_me(interaction = interaction)


async def dice(interaction: discord.Interaction, roll: int, side: int):
    logger.debug(f"{interaction.user.id} executed /dice command in {f"guild id={interaction.guild.id}" if interaction.guild else f"{interaction.channel.type.name} id={interaction.channel.id}"}")
    with get_session() as session:
        crud.addUserCount(session, interaction.user.id)
    if side is None or roll is None:
        logger.error(f'Not a valid parameter: roll: {roll} side: {side}')
        await interaction.response.send_message("必要なオプションがが指定されていません。",ephemeral=True)
    elif roll <= 0 or side <= 0:
        await interaction.response.send_message("オプションは0以上の整数だよ!",ephemeral=True)
    elif roll >= 16777216 or side >= 16777216:
        await interaction.response.send_message("オプションは16777216以下の整数だよ!大きい数字は無理なんだ......ごめんね？\n後で大きい数字対応のコマンドも作るよ!がんばるね!",ephemeral=True)
    else:
        await interaction.response.defer(thinking=True)

        def calculate_roll():
            return sum(random.randint(1, side) for _ in range(roll))
        
        try:
            msg = await asyncio.to_thread(calculate_roll)
            await interaction.followup.send(f"{msg}")
        except Exception as e:
            logger.exception(f'Error in random calculation: roll: {roll} side: {side}')
            await interaction.followup.send("わかんないよぅ；；\nbot管理者まで連絡ください。")

@tree.command(name = 'dice', description = 'サイコロを振ります')
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(roll="サイコロを振る回数です", side="サイコロの面の数です")
async def dice_slash(interaction: discord.Interaction, roll: int, side: int):
    await dice(interaction = interaction, roll = roll, side = side)


async def chinchiro(interaction: discord.Interaction):
    logger.debug(f"{interaction.user.id} executed /chinchiro command in {f"guild id={interaction.guild.id}" if interaction.guild else f"{interaction.channel.type.name} id={interaction.channel.id}"}")
    with get_session() as session:
        crud.addUserCount(session, interaction.user.id)
    if random.randint(1, 50) == 1:
        await interaction.response.send_message("台からサイコロが落ちた！")
    else:
        await interaction.response.send_message(f'{random.randint(1, 6)}  {random.randint(1, 6)}  {random.randint(1, 6)}')

@tree.command(name = 'chinchiro', description = 'チンチロを振ります')
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def chinchiro_slash(interaction: discord.Interaction):
    await chinchiro(interaction = interaction)


async def dice_poker(interaction: discord.Interaction):
    logger.debug(f"{interaction.user.id} executed /dice-poker command in {f"guild id={interaction.guild.id}" if interaction.guild else f"{interaction.channel.type.name} id={interaction.channel.id}"}")
    with get_session() as session:
        crud.addUserCount(session, interaction.user.id)
    faces = ["9", "10", "J", "Q", "K", "A"]
    await interaction.response.send_message(f'{random.choice(faces)}  {random.choice(faces)}  {random.choice(faces)}  {random.choice(faces)}  {random.choice(faces)}')

@tree.command(name = 'dice-poker', description = '一般的なダイスポーカーを振ります')
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def dice_poker_slash(interaction: discord.Interaction):
    await dice_poker(interaction = interaction)


async def dice_poker_stgr(interaction: discord.Integration):
    logger.debug(f"{interaction.user.id} executed /dice-poker-stgr command in {f"guild id={interaction.guild.id}" if interaction.guild else f"{interaction.channel.type.name} id={interaction.channel.id}"}")
    with get_session() as session:
        crud.addUserCount(session, interaction.user.id)
    await interaction.response.send_message(f'{random.randint(1, 6)}  {random.randint(1, 6)}  {random.randint(1, 6)}  {random.randint(1, 6)}  {random.randint(1, 6)}')

@tree.command(name = 'dice-poker-stgr', description = 'ストグラのカジノで行われているダイスポーカーを振ります')
@app_commands.user_install()
async def dice_poker_stgr_slash(interaction: discord.Integration):
    await dice_poker_stgr(interaction = interaction)


@client.event
async def on_voice_state_update(member, before, after):
    msg = None
    
    logger.debug(f"Event triggered: {member.display_name}, Before: {before.channel}, After: {after.channel}")
    with get_session() as session:
        alert_channel_id = crud.readServerSetting(session, member.guild.id).notification_channel
    alert_channel = client.get_channel(alert_channel_id) or member.guild.system_channel
    if alert_channel is None:
        logger.error(f"Alert channel with ID {alert_channel_id} not found or no access.")
        return
    
    if not alert_channel.permissions_for(member.guild.me).send_messages:
        return

    if before.channel is None and after.channel is not None:
        msg = f'{member.display_name} が {after.channel.name} に参加しました。'
        with get_session() as session:
            crud.addVcSessions(session, member.guild.id, member.id, after.channel.id, after.self_mute)
    elif after.channel is None and before.channel is not None:
        msg = f'{member.display_name} が {before.channel.name} から退出しました。'
        with get_session() as session:
            crud.endVcSessions(session, member.guild.id, member.id, before.channel.id, before.self_mute, startup_time)
    elif before.channel is not None and after.channel is not None:
        if before.channel.id != after.channel.id:
            msg = f'{member.display_name} が {before.channel.name} から {after.channel.name} に移動しました。'
            with get_session() as session:
                crud.endVcSessions(session, member.guild.id, member.id, before.channel.id, before.self_mute, startup_time)
                crud.addVcSessions(session, member.guild.id, member.id, after.channel.id, after.self_mute)
        elif before.self_mute != after.self_mute:
            if before.self_mute:
                with get_session() as session:
                    crud.endVcSessions(session, member.guild.id, member.id, before.channel.id, before.self_mute, startup_time)
                    crud.addVcSessions(session, member.guild.id, member.id, after.channel.id, after.self_mute)
            elif after.self_mute:
                with get_session() as session:
                    crud.endVcSessions(session, member.guild.id, member.id, before.channel.id, before.self_mute, startup_time)
                    crud.addVcSessions(session, member.guild.id, member.id, after.channel.id, after.self_mute)

    if msg is not None:
        logger.debug(f'Send message: {msg}')
        await alert_channel.send(msg)
    else:
        logger.debug("No relevant voice state changes detected.")

tree.add_command(serverSettings)

async def shutdown():
    logger.info("Start Shutdown")
    with get_session() as session:
        crud.endAllVcSessions(session, startup_time)
    await client.close()
    logger.info("Finish Shutdown! good by!")

async def runner(token):


    async with client:
        try:
            await client.start(token)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Received stop signal")
        finally:
            await shutdown()

if __name__ == "__main__":
    asyncio.run(runner(DISCORD_TOKEN))