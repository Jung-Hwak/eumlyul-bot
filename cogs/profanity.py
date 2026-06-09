import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)

DATA_PATH = "data/profanity.json"

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

# 운영진 역할 체크 (여러 역할 지원)
def is_admin(user_roles, admin_roles: list) -> bool:
    user_role_names = [r.name for r in user_roles]
    return any(role in user_role_names for role in admin_roles)

# ── 화이트리스트: 정상 문맥 조합 (탐지 제외) ─────────────────────
WHITELIST_PHRASES = [
    "새끼 고양이", "새끼 강아지", "새끼 고양", "새끼 강아",
    "만화를 보지", "영상을 보지", "유튜브를 보지", "드라마를 보지",
    "미친 노래", "미친 곡", "미친 목소리", "미친 실력",
]

# 오탐지 많은 단어별 안전 패턴 (이 패턴 포함이면 정상 문장으로 판단)
CONTEXT_SAFE = {
    "보지": ["를 보지", "도 보지", "만 보지", "고 보지", "나 보지", "서 보지", "은 보지"],
    "새끼": ["새끼 고양", "새끼 강아", "새끼 돼지", "새끼 양"],
    "미친": ["미친 노래", "미친 곡", "미친 목소리", "미친 실력", "미친듯"],
    "자지": ["자지 않", "자지 말", "자지 마", "안 자지", "못 자지"],
}

def check_profanity_with_context(content: str, profanity_list: list) -> list:
    """문맥 기반 비속어 탐지 - 정상 문맥이면 제외"""
    content_lower = content.lower()
    detected = []

    # 화이트리스트 구문 먼저 제거
    for phrase in WHITELIST_PHRASES:
        content_lower = content_lower.replace(phrase.lower(), " " * len(phrase))

    for word in profanity_list:
        word_lower = word.lower()
        if word_lower not in content_lower:
            continue
        # 문맥 안전 패턴 체크
        if word_lower in CONTEXT_SAFE:
            safe_patterns = CONTEXT_SAFE[word_lower]
            if any(pattern in content_lower for pattern in safe_patterns):
                continue
        detected.append(word)

    return detected

class ProfanityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── 메시지 감지 ───────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return

        try:
            config = load_config()
            profanity_list = config.get("profanity_list", [])
            log_channel_name = config.get("log_channel_name", "봇-비속어-기록")

            detected = check_profanity_with_context(message.content, profanity_list)
            if not detected:
                return

            data = load_data()
            user_id = str(message.author.id)
            user_name = message.author.display_name

            if user_id not in data:
                data[user_id] = {"name": user_name, "count": 0, "history": []}

            data[user_id]["name"] = user_name
            data[user_id]["count"] += len(detected)
            data[user_id]["history"].append({
                "word": detected,
                "channel": message.channel.name,
                "time": datetime.now(timezone.utc).isoformat()
            })
            save_data(data)
            log.info(f"비속어 감지 = {user_name} | 단어 = {detected} | 채널 = {message.channel.name}")

            log_channel = discord.utils.get(message.guild.text_channels, name=log_channel_name)
            if log_channel:
                embed = discord.Embed(
                    title="🚨 비속어 감지",
                    color=discord.Color.red(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="멤버", value=f"{message.author.mention} ({user_name})", inline=True)
                embed.add_field(name="채널", value=message.channel.mention, inline=True)
                embed.add_field(name="감지된 단어", value=", ".join(detected), inline=False)
                embed.add_field(name="누적 횟수", value=f"{data[user_id]['count']}회", inline=True)
                embed.set_footer(text=f"메시지: {message.content[:100]}")
                await log_channel.send(embed=embed)
        except Exception as e:
            log.error(f"비속어 감지 오류 = {e}")

    # ── /비속어조회 (운영진 전용) ─────────────────────────────────
    @app_commands.command(name="비속어조회", description="멤버별 비속어 사용 횟수 조회 (운영진 전용)")
    async def check_profanity(self, interaction: discord.Interaction):
        config = load_config()
        admin_roles = config.get("admin_roles", ["COC", "FM", "Manager"])

        if not is_admin(interaction.user.roles, admin_roles):
            await interaction.response.send_message("❌ 운영진만 사용 가능한 명령어입니다.", ephemeral=True)
            return

        data = load_data()
        if not data:
            await interaction.response.send_message("📋 기록된 비속어가 없습니다.", ephemeral=True)
            return

        sorted_data = sorted(data.items(), key=lambda x: x[1]["count"], reverse=True)
        embed = discord.Embed(
            title="📊 비속어 사용 현황",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        lines = [f"`{rank}.` **{info['name']}** — {info['count']}회"
                 for rank, (uid, info) in enumerate(sorted_data, 1)]
        embed.description = "\n".join(lines)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /비속어상세 (운영진 전용) ─────────────────────────────────
    @app_commands.command(name="비속어상세", description="특정 멤버 비속어 상세 조회 (운영진 전용)")
    @app_commands.describe(member="조회할 멤버")
    async def check_profanity_detail(self, interaction: discord.Interaction, member: discord.Member):
        config = load_config()
        admin_roles = config.get("admin_roles", ["COC", "FM", "Manager"])

        if not is_admin(interaction.user.roles, admin_roles):
            await interaction.response.send_message("❌ 운영진만 사용 가능한 명령어입니다.", ephemeral=True)
            return

        data = load_data()
        user_id = str(member.id)

        if user_id not in data:
            await interaction.response.send_message(f"📋 {member.display_name}의 비속어 기록이 없습니다.", ephemeral=True)
            return

        info = data[user_id]
        embed = discord.Embed(title=f"📋 {info['name']} 비속어 상세", color=discord.Color.orange())
        embed.add_field(name="총 횟수", value=f"{info['count']}회", inline=False)
        recent = info["history"][-5:]
        history_text = "\n".join([
            f"• {h['time'][:10]} [{h['channel']}] `{'`, `'.join(h['word'])}`"
            for h in reversed(recent)
        ])
        embed.add_field(name="최근 기록 (최대 5건)", value=history_text or "없음", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ProfanityCog(bot))
