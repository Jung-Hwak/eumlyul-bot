import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)

DATA_PATH = "data/channel_move.json"

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_data():
    if not os.path.exists(DATA_PATH):
        os.makedirs("data", exist_ok=True)
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class ChannelMoveCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        """채널이 진행중¹ 카테고리로 이동되는 순간 등록 시각 기록"""
        try:
            config = load_config()
            stage1_name = config.get("category_stage1", "진행중¹")

            if not hasattr(after, "category") or after.category is None:
                return
            if before.category == after.category:
                return
            if after.category.name != stage1_name:
                return

            data = load_data()
            channel_id = str(after.id)
            if channel_id not in data:
                data[channel_id] = {
                    "name": after.name,
                    "stage": 1,
                    "stage1_at": datetime.now(timezone.utc).isoformat(),
                    "stage2_at": None
                }
                save_data(data)
                log.info(f"진행중¹ 등록 = {after.name} | 시각 = {data[channel_id]['stage1_at']}")
        except Exception as e:
            log.error(f"채널 업데이트 감지 오류 = {e}")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """채널 생성 시 진행중¹ 카테고리면 바로 기록"""
        try:
            config = load_config()
            stage1_name = config.get("category_stage1", "진행중¹")

            if not hasattr(channel, "category") or channel.category is None:
                return
            if channel.category.name != stage1_name:
                return

            data = load_data()
            channel_id = str(channel.id)
            if channel_id not in data:
                data[channel_id] = {
                    "name": channel.name,
                    "stage": 1,
                    "stage1_at": datetime.now(timezone.utc).isoformat(),
                    "stage2_at": None
                }
                save_data(data)
                log.info(f"진행중¹ 신규 채널 등록 = {channel.name}")
        except Exception as e:
            log.error(f"채널 생성 감지 오류 = {e}")

# ── 루프에서 호출되는 이동 실행 함수 ─────────────────────────────
async def check_and_move_channels(bot: discord.Client):
    try:
        config = load_config()
        guild_id = config.get("guild_id")
        stage2_name = config.get("category_stage2", "진행중²")
        stage3_name = config.get("category_stage3", "진행중³")
        stage1_days = config.get("stage1_days", 28)
        stage2_days = config.get("stage2_days", 14)

        guild = bot.get_guild(guild_id)
        if not guild:
            log.warning("guild를 찾을 수 없음 — guild_id 확인 필요")
            return

        data = load_data()
        now = datetime.now(timezone.utc)
        changed = False

        for channel_id, info in list(data.items()):
            try:
                channel = guild.get_channel(int(channel_id))
                if not channel:
                    # 삭제된 채널은 데이터에서 제거
                    del data[channel_id]
                    changed = True
                    continue

                stage = info.get("stage", 1)

                # 진행중¹ → 진행중² (28일)
                if stage == 1 and info.get("stage1_at"):
                    stage1_at = datetime.fromisoformat(info["stage1_at"])
                    if now >= stage1_at + timedelta(days=stage1_days):
                        target_category = discord.utils.get(guild.categories, name=stage2_name)
                        if target_category:
                            await channel.edit(category=target_category)
                            info["stage"] = 2
                            info["stage2_at"] = now.isoformat()
                            changed = True
                            log.info(f"채널 이동 = {channel.name} | 진행중¹ → 진행중²")
                        else:
                            log.warning(f"카테고리 없음 = {stage2_name}")

                # 진행중² → 진행중³ (14일)
                elif stage == 2 and info.get("stage2_at"):
                    stage2_at = datetime.fromisoformat(info["stage2_at"])
                    if now >= stage2_at + timedelta(days=stage2_days):
                        target_category = discord.utils.get(guild.categories, name=stage3_name)
                        if target_category:
                            await channel.edit(category=target_category)
                            info["stage"] = 3
                            changed = True
                            log.info(f"채널 이동 = {channel.name} | 진행중² → 진행중³")
                        else:
                            log.warning(f"카테고리 없음 = {stage3_name}")
            except Exception as e:
                log.error(f"채널 이동 오류 = {channel_id} | {e}")

        if changed:
            save_data(data)
    except Exception as e:
        log.error(f"check_and_move_channels 오류 = {e}")

async def setup(bot):
    await bot.add_cog(ChannelMoveCog(bot))
