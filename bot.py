import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from datetime import datetime, timezone
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

# ── 인텐트 설정 ─────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="/", intents=intents)

# ── 봇 준비 ─────────────────────────────────────────────────────
@bot.event
async def on_ready():
    log.info(f"봇 로그인 = {bot.user}")
    try:
        synced = await bot.tree.sync()
        log.info(f"슬래시 명령어 동기화 = {len(synced)}개")
    except Exception as e:
        log.error(f"명령어 동기화 실패 = {e}")
    # 루프 중복 시작 방지
    if not check_channel_move.is_running():
        check_channel_move.start()

# ── Cog 로드 ────────────────────────────────────────────────────
async def load_cogs():
    await bot.load_extension("cogs.profanity")
    await bot.load_extension("cogs.channel_move")
    await bot.load_extension("cogs.project")
    await bot.load_extension("cogs.forum_notify")

# ── 28일/14일 채널 이동 루프 ────────────────────────────────────
@tasks.loop(minutes=10)
async def check_channel_move():
    try:
        from cogs.channel_move import check_and_move_channels
        await check_and_move_channels(bot)
    except Exception as e:
        log.error(f"채널 이동 루프 오류 = {e}")

@check_channel_move.before_loop
async def before_check():
    await bot.wait_until_ready()  # 봇 준비 완료 후 루프 시작

# ── 봇 실행 ─────────────────────────────────────────────────────
async def main():
    async with bot:
        await load_cogs()
        config = load_config()
        await bot.start(config["token"])

asyncio.run(main())
