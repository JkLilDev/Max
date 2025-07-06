import discord
import os
from dotenv import load_dotenv
from commands import handle_command
from keep_alive import keep_alive
keep_alive()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

# Status function (now accepts more args, including 'view')
async def send_status(channel, text, **kwargs):
    return await channel.send(text, **kwargs)

@client.event
async def on_ready():
    print(f"✅ Bot is ready. Logged in as {client.user}")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="JK"))

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.author.id != OWNER_ID:
        return

    await handle_command(client, message, send_status)

client.run(TOKEN)