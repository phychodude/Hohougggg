import discord
from discord.ext import commands
import asyncio
import os
import json
from datetime import datetime

class DMBroadcast(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dm_sessions = {}
        self.sessions_file = "dm_sessions.json"
        self.load_persistent_data()

    def load_persistent_data(self):
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, 'r') as f:
                    data = json.load(f)
                    self.dm_sessions = {int(k): v for k, v in data.items()}
            except:
                self.dm_sessions = {}

    def save_persistent_data(self):
        with open(self.sessions_file, 'w') as f:
            json.dump(self.dm_sessions, f, indent=2)

    async def send_webhook_update(self, message: str):
        from config import WEBHOOK_URL
        if not WEBHOOK_URL:
            return
        try:
            async with self.bot.session.post(WEBHOOK_URL, json={"content": message}):
                pass
        except:
            pass

    @commands.command(name="dmrole")
    @commands.has_permissions(administrator=True)
    async def dm_role(self, ctx, role: discord.Role, *, message: str):
        if ctx.guild is None:
            await ctx.send("❌ This command can only be used in a server!")
            return

        if ctx.guild.id in self.dm_sessions:
            await ctx.send("❌ There's already an active DM broadcast session in this server!")
            return

        members_with_role = [m for m in ctx.guild.members if role in m.roles and not m.bot]

        if not members_with_role:
            await ctx.send(f"❌ No members found with the role {role.mention}!")
            return

        embed = discord.Embed(
            title="📢 DM Broadcast Confirmation",
            description=f"**Role:** {role.mention}\n**Recipients:** {len(members_with_role)} members\n**Message Preview:** {message[:100]}{'...' if len(message) > 100 else ''}",
            color=discord.Color.blue()
        )
        embed.add_field(name="⚠️ Warning", value="This will send DMs to all users with this role. React with ✅ to confirm or ❌ to cancel.", inline=False)

        confirmation_msg = await ctx.send(embed=embed)
        await confirmation_msg.add_reaction("✅")
        await confirmation_msg.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation_msg.id

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ DM broadcast cancelled.")
                return
        except asyncio.TimeoutError:
            await ctx.send("⏰ Confirmation timed out. DM broadcast cancelled.")
            return

        session_id = ctx.guild.id
        self.dm_sessions[session_id] = {
            'guild_id': ctx.guild.id,
            'channel_id': ctx.channel.id,
            'role_id': role.id,
            'message': message,
            'members': [m.id for m in members_with_role],
            'processed_ids': [],
            'sent': 0,
            'failed': 0,
            'total': len(members_with_role),
            'author_id': ctx.author.id,
            'started_at': datetime.now().isoformat(),
        }
        self.save_persistent_data()

        await ctx.send(f"🚀 Starting DM broadcast to {len(members_with_role)} members with role {role.mention}...")
        self.bot.loop.create_task(self.broadcast_dms(ctx, session_id, members_with_role))

    async def broadcast_dms(self, ctx, session_id, members):
        session = self.dm_sessions[session_id]
        for member in members:
            if member.id in session['processed_ids']:
                continue
            try:
                embed = discord.Embed(description=session['message'], color=discord.Color.green())
                embed.set_footer(text=f"Sent from {ctx.guild.name}")
                await member.send(embed=embed)
                session['sent'] += 1
            except:
                session['failed'] += 1
            session['processed_ids'].append(member.id)
            self.save_persistent_data()
            await asyncio.sleep(15)

        await ctx.send(f"✅ Broadcast finished. Sent: {session['sent']} | Failed: {session['failed']}")
        if session_id in self.dm_sessions:
            del self.dm_sessions[session_id]
            self.save_persistent_data()
