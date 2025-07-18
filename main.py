import discord
from discord.ext import commands
import json
import os

with open("config.json") as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.add_cog(DMBroadcast(bot))
    print("📣 Cog loaded.")

from cogs.dm_broadcast import DMBroadcast
bot.run(os.getenv("BOT_TOKEN") or config.get("token"))
