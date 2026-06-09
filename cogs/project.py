import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def is_admin(user_roles, admin_roles: list) -> bool:
    user_role_names = [r.name for r in user_roles]
    return any(role in user_role_names for role in admin_roles)

def get_initial(name: str, initials: dict) -> str:
    return initials.get(name, name[:2].upper())

def find_member(guild: discord.Guild, name: str) -> discord.Member | None:
    return discord.utils.find(
        lambda m: m.display_name == name or m.name == name,
        guild.members
    )

class ProjectCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── /create 명령어 ────────────────────────────────────────────
    @app_commands.command(name="create", description="프로젝트 채널 생성")
    @app_commands.describe(
        title="노래 제목",
        p="프로듀서 닉네임",
        v="참여자 닉네임 (쉼표로 구분, 예: 망찐,히네,이설)"
    )
    async def create_project(self, interaction: discord.Interaction, title: str, p: str, v: str):
        await interaction.response.defer(ephemeral=True)

        try:
            config = load_config()
            guild = interaction.guild
            initials = config.get("initials", {})
            waiting_category_name = config.get("category_waiting", "대기중인 마감")
            admin_roles = config.get("admin_roles", ["COC", "FM", "Manager"])

            participants_names = [name.strip() for name in v.split(",") if name.strip()]

            if not participants_names:
                await interaction.followup.send("❌ 참여자를 한 명 이상 입력해주세요.", ephemeral=True)
                return

            producer_initial = get_initial(p, initials)
            channel_name = f"{producer_initial}_{title}"

            log.info(f"프로젝트 생성 요청 = {channel_name} | 프로듀서 = {p} | 참여자 = {participants_names}")

            waiting_category = discord.utils.get(guild.categories, name=waiting_category_name)
            if not waiting_category:
                await interaction.followup.send(f"❌ '{waiting_category_name}' 카테고리를 찾을 수 없습니다.", ephemeral=True)
                return

            # 멤버 객체 수집
            members = []
            not_found = []
            for name in participants_names:
                member = find_member(guild, name)
                if member:
                    members.append(member)
                else:
                    not_found.append(name)

            if not_found:
                await interaction.followup.send(
                    f"⚠️ 다음 멤버를 찾을 수 없습니다: {', '.join(not_found)}\n닉네임을 정확히 입력해주세요.",
                    ephemeral=True
                )
                return

            # 권한 설정: 기본 비공개, 참여자만 허용
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }

            # 운영진 역할 모두 볼 수 있게 (COC, FM, Manager)
            for role_name in admin_roles:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            # 참여자 개별 권한
            for member in members:
                overwrites[member] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

            new_channel = await guild.create_text_channel(
                name=channel_name,
                category=waiting_category,
                overwrites=overwrites
            )

            log.info(f"채널 생성 완료 = {new_channel.name} | ID = {new_channel.id}")

            # 봇이 채널에 안내 메시지 작성
            producer_member = find_member(guild, p)
            producer_mention = producer_member.mention if producer_member else f"@{p}"
            voice_mentions = " ".join([m.mention for m in members])

            embed = discord.Embed(
                title=f"[ {title} ]",
                color=discord.Color.purple(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="P", value=producer_mention, inline=False)
            embed.add_field(name="V", value=voice_mentions, inline=False)

            await new_channel.send(embed=embed)

            await interaction.followup.send(
                f"✅ **{channel_name}** 채널이 '{waiting_category_name}'에 생성되었습니다!\n"
                f"참여자 {len(members)}명에게 접근 권한이 부여되었습니다.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send("❌ 봇에 채널 생성 권한이 없습니다. 서버 설정을 확인해주세요.", ephemeral=True)
        except Exception as e:
            log.error(f"채널 생성 오류 = {e}")
            await interaction.followup.send("❌ 오류가 발생했습니다. 로그를 확인해주세요.", ephemeral=True)

    # ── /이니셜등록 (운영진 전용) ─────────────────────────────────
    @app_commands.command(name="이니셜등록", description="멤버 이니셜 등록/수정 (운영진 전용)")
    @app_commands.describe(nickname="디코 닉네임", initial="이니셜 (예: 𝗠𝗭)")
    async def set_initial(self, interaction: discord.Interaction, nickname: str, initial: str):
        config = load_config()
        admin_roles = config.get("admin_roles", ["COC", "FM", "Manager"])

        if not is_admin(interaction.user.roles, admin_roles):
            await interaction.response.send_message("❌ 운영진만 사용 가능한 명령어입니다.", ephemeral=True)
            return

        config["initials"][nickname] = initial
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        log.info(f"이니셜 등록 = {nickname} → {initial}")
        await interaction.response.send_message(f"✅ `{nickname}` → `{initial}` 등록 완료!", ephemeral=True)

    # ── /이니셜목록 ────────────────────────────────────────────────
    @app_commands.command(name="이니셜목록", description="등록된 이니셜 목록 조회")
    async def list_initials(self, interaction: discord.Interaction):
        config = load_config()
        initials = config.get("initials", {})

        if not initials:
            await interaction.response.send_message("📋 등록된 이니셜이 없습니다.", ephemeral=True)
            return

        lines = [f"**{name}** → `{initial}`" for name, initial in initials.items()]
        embed = discord.Embed(
            title="📋 이니셜 목록",
            description="\n".join(lines),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ProjectCog(bot))
