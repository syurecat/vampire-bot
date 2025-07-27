import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import random
import time
import json
import asyncio
import logging
import logging.handlers
from rich.logging import RichHandler
from datetime import datetime
from database import init_db
from database.crud import get_session, addUserCount, clearVcSessions, addVcSessions, endVcSessions, readVcSummary, updateServerNotificationChannel, readServerSetting, FutureDateError

init_db()
load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LEVEL_NAME, logging.INFO)
ADVANCED_LEVEL_NAME = os.getenv("ADVANCED_LOG_LEVEL", "WARNING").upper()
ADVANCED_LOG_LEVEL = getattr(logging, ADVANCED_LEVEL_NAME, logging.INFO)
startup_time = int(time.time())

with open("messages/memes.json", "r", encoding="utf-8") as f:
    meme_dict = json.load(f)

trigger_set = set(meme_dict.keys())

# logging setting reset
root = logging.getLogger()
root.setLevel(LOG_LEVEL)
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
console_handler.setFormatter(logging.Formatter(LOG_CONSOLE_FMT, DATE_FMT))
root.addHandler(console_handler)

# log file
file_handler = logging.handlers.RotatingFileHandler(
    filename='discord.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,
    backupCount=7,
)
file_handler.setFormatter(logging.Formatter(LOG_FILE_FMT, DATE_FMT))
root.addHandler(file_handler)  

# Discord log setting
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(LOG_LEVEL)

# SQLAlchemy log setting
sqlalchemy_logger = logging.getLogger('sqlalchemy')
sqlalchemy_logger.setLevel(LOG_LEVEL)

logging.getLogger('discord.http').setLevel(ADVANCED_LOG_LEVEL)
logging.getLogger('discord.gateway').setLevel(ADVANCED_LOG_LEVEL)
logging.getLogger('sqlalchemy.engine').setLevel(ADVANCED_LOG_LEVEL)
logging.getLogger('sqlalchemy.orm').setLevel(ADVANCED_LOG_LEVEL)
logging.getLogger('sqlalchemy.pool').setLevel(ADVANCED_LOG_LEVEL)

logger = logging.getLogger('vampire')
logger.setLevel(LOG_LEVEL)

# Discord
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
# Command Group
serverSettings = app_commands.Group(name="server-settings", description="サーバー設定", default_permissions=discord.Permissions(manage_guild=True))

@client.event
async def on_ready():
    logger.info(f'We have logged in as {client.user}')
    logger.debug("debug on")
    with get_session() as session:
        clearVcSessions(session)
    await tree.sync()

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    content = message.content.strip()

    if content in trigger_set:
        responses = meme_dict[content]
        response = random.choice(responses)
        await message.channel.send(response)

    elif client.user in message.mentions:
        await message.channel.send(f"{message.author.mention} 呼んだ？")

@tree.command(
    name = 'ping',
    description = 'pingを返します'
)
async def ping(interaction: discord.Interaction):
    with get_session() as session:
        addUserCount(session, interaction.user.id)
    await interaction.response.send_message("pong!")

@serverSettings.command(
        name = 'notification-channel',
        description = 'botの通知チャンネルを変更します。'
)
@app_commands.describe(
    channel="通知するチャンネル"
)
async def notificationChannel(interaction: discord.Integration, channel: discord.TextChannel):
    with get_session() as session:
        updateServerNotificationChannel(session, interaction.guild.id, channel.id)
    await interaction.response.send_message(f"通知チャンネルを <#{channel.id}> に設定しました！")


@tree.command(
        name= 'vc-time',
        description= 'あなたのvc接続時間を表示します。'
)
@app_commands.describe(
    channel="閲覧するチャンネル",
    ephemeral="自分にしか表示しないかどうかです。defaultでTrueです。"
)
async def vcLog(interaction: discord.Interaction, channel: discord.VoiceChannel,year: app_commands.Range[int, 2025, 2099] = None, month: app_commands.Range[int, 1, 12] = None, ephemeral: bool=True):
    try:
        with get_session() as session:
            connection_time, mic_on_time  = readVcSummary(session, interaction.guild.id, interaction.user.id, channel.id, year, month)
    except FutureDateError:
        await interaction.response.send_message(f"ごめんね～\n私、未来のことはわかんないんだよね......\nその時まで一緒にいれると嬉しいな！", ephemeral=True)
        return
    if year is not None and month is None:
        await interaction.response.send_message(f"{year or datetime.now().year}年に {channel.name} に接続していた時間の発表です！\n接続時間: {connection_time}\nミュート: {mic_on_time}", ephemeral=ephemeral)
    else:
        await interaction.response.send_message(f"{year or datetime.now().year}年 {month or datetime.now().month}月に {channel.name} に接続していた時間の発表です！\n接続時間: {connection_time}\nミュート: {mic_on_time}", ephemeral=ephemeral)

@tree.command(
    name = 'rps',
    description = 'じゃんけんをします。'
)
async def rps(interaction: discord.Interaction, ):
    with get_session() as session:
        addUserCount(session, interaction.user.id)
    if random.randint(1, 100) == 1:
        await interaction.response.send_message(":hand_with_index_finger_and_thumb_crossed:")
    else:
        faces = ["✊", "✌️", "🖐️"]
        await interaction.response.send_message(f'{random.choice(faces)}')

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

@tree.command(
    name = 'rps-me',
    description = '私とじゃんけんをしよう！'
)
async def rpsMe(interaction: discord.Integration):
    with get_session() as session:
        addUserCount(session, interaction.user.id)
    if random.randint(1, 250) == 1:
        await interaction.response.send_message("zzz...")
    else:
        view = rpsMeView()
        await interaction.response.send_message("じゃんけん...", view = view)

@tree.command(
    name = 'dice',
    description = 'サイコロを振ります'
)
@app_commands.describe(
    roll="サイコロを振る回数です",
    side="サイコロの面の数です"
)
async def dice(interaction: discord.Interaction, roll: int, side: int):
    with get_session() as session:
        addUserCount(session, interaction.user.id)
    if side is None or roll is None:
        logger.ERROR(f'Not a valid parameter: roll: {roll} side: {side}')
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
            logger.ERROR(f'Error in random calculation: roll: {roll} side: {side}')
            logger.ERROR(f'Error occurred: {e}')
            await interaction.followup.send("わかんないよぅ；；\nbot管理者まで連絡ください。")

@tree.command(
    name = 'chinchiro',
    description = 'チンチロを振ります'
)
async def chinchiro(interaction: discord.Interaction):
    with get_session() as session:
        addUserCount(session, interaction.user.id)
    if random.randint(1, 50) == 1:
        await interaction.response.send_message("台からサイコロが落ちた！")
    else:
        await interaction.response.send_message(f'{random.randint(1, 6)}  {random.randint(1, 6)}  {random.randint(1, 6)}')

@tree.command(
    name = 'dice-poker',
    description = '一般的なダイスポーカーを振ります'
)
async def dicePoker(interaction: discord.Interaction):
    with get_session() as session:
        addUserCount(session, interaction.user.id)
    faces = ["9", "10", "J", "Q", "K", "A"]
    await interaction.response.send_message(f'{random.choice(faces)}  {random.choice(faces)}  {random.choice(faces)}  {random.choice(faces)}  {random.choice(faces)}')

@tree.command(
    name = 'dice-poker-stgr',
    description = 'ストグラのカジノで行われているダイスポーカーを振ります'
)
async def dicePokerStgr(interaction: discord.Integration):
    with get_session() as session:
        addUserCount(session, interaction.user.id)
    await interaction.response.send_message(f'{random.randint(1, 6)}  {random.randint(1, 6)}  {random.randint(1, 6)}  {random.randint(1, 6)}  {random.randint(1, 6)}')

@client.event
async def on_voice_state_update(member, before, after):
    msg = None
    
    logger.debug(f"Event triggered: {member.display_name}, Before: {before.channel}, After: {after.channel}")
    with get_session() as session:
        alert_channel_id = readServerSetting(session, member.guild.id).notification_channel
    alert_channel = client.get_channel(alert_channel_id)
    if alert_channel is None:
        logger.error(f"Alert channel with ID {alert_channel_id} not found or no access.")
        return

    if before.channel is None and after.channel is not None:
        msg = f'{member.display_name} が {after.channel.name} に参加しました。'
        with get_session() as session:
            addVcSessions(session, member.guild.id, member.id, after.channel.id, after.self_mute)
    elif after.channel is None and before.channel is not None:
        msg = f'{member.display_name} が {before.channel.name} から退出しました。'
        with get_session() as session:
            endVcSessions(session, member.guild.id, member.id, before.channel.id, before.self_mute, startup_time)
    elif before.channel is not None and after.channel is not None:
        if before.channel.id != after.channel.id:
            msg = f'{member.display_name} が {before.channel.name} から {after.channel.name} に移動しました。'
            with get_session() as session:
                endVcSessions(session, member.guild.id, member.id, before.channel.id, before.self_mute, startup_time)
                addVcSessions(session, member.guild.id, member.id, after.channel.id, after.self_mute)
        elif before.self_mute != after.self_mute:
            if before.self_mute:
                with get_session() as session:
                    endVcSessions(session, member.guild.id, member.id, before.channel.id, before.self_mute, startup_time)
                    addVcSessions(session, member.guild.id, member.id, after.channel.id, after.self_mute)
            elif after.self_mute:
                with get_session() as session:
                    endVcSessions(session, member.guild.id, member.id, before.channel.id, before.self_mute, startup_time)
                    addVcSessions(session, member.guild.id, member.id, after.channel.id, after.self_mute)

    if msg is not None:
        logger.info(f'Send message: {msg}')
        await alert_channel.send(msg)
    else:
        logger.debug("nope")

tree.add_command(serverSettings)
# log_level=logging.DEBUG
client.run(DISCORD_TOKEN, log_handler=None)