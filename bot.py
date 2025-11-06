import discord
from discord.ext import commands
import os
import asyncio

TOKEN = "MTQzNTM1MDMzNzg2MjEwNzI2MA.GcbKAa.2fZbaYqA94_s5NV9HjtqnacQQCtgLoqYDgfVA0"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

@bot.event
async def on_ready():
    # For testing - instant sync to your server
    guild = discord.Object(id=1435336552237498530)  # Replace with your server ID
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    
    print(f"✅ Connecté comme {bot.user} et commandes synchronisées sur le serveur de test.")

async def main():
    await load_cogs()
    await bot.start(TOKEN)

asyncio.run(main())