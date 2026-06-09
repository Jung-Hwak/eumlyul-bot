import discord
from discord.ext import commands
import json
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

class ForumNotifyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── 포럼 채널에 새 스레드(글) 생성될 때 감지 ─────────────────
    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        try:
            config = load_config()
            forum_channel_name = config.get("forum_channel_name", "🎧ᴘʀᴏᴅᴜᴄᴇʀ")
            notify_channel_name = config.get("forum_notify_channel_name", "🎧ᴘʀᴏᴅᴜᴄᴇʀ홍보방")

            # 포럼 채널에서 생성된 스레드인지 확인
            if not isinstance(thread.parent, discord.ForumChannel):
                return
            if thread.parent.name != forum_channel_name:
                return

            log.info(f"포럼 새 글 감지 = {thread.name} | 작성자 = {thread.owner}")

            # 홍보방 채널 찾기
            notify_channel = discord.utils.get(thread.guild.text_channels, name=notify_channel_name)
            if not notify_channel:
                log.warning(f"홍보방 채널을 찾을 수 없음 = {notify_channel_name}")
                return

            # 글 작성자 (owner가 None일 수 있어서 안전하게 처리)
            author = thread.owner
            author_mention = author.mention if author else "알 수 없음"

            embed = discord.Embed(
                title="🎧 새로운 글이 등록되었습니다!",
                color=discord.Color.purple(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="글 제목", value=thread.name, inline=False)
            embed.add_field(name="작성자", value=author_mention, inline=True)
            embed.add_field(name="바로가기", value=thread.mention, inline=True)

            await notify_channel.send(content="@everyone", embed=embed)
            log.info(f"홍보방 알림 전송 완료 = {thread.name}")
        except Exception as e:
            log.error(f"포럼 알림 오류 = {e}")

async def setup(bot):
    await bot.add_cog(ForumNotifyCog(bot))
