import discord
import os
from dotenv import load_dotenv
from commands import handle_command, setup_help_command
from keep_alive import keep_alive
import automod

keep_alive()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
MOD_CHANNEL_ID = int(os.getenv("MOD_CHANNEL"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f"✅ Bot is ready. Logged in as {client.user}")
    # Set invisible status with "Listening to JK"
    try:
        await client.change_presence(
            status=discord.Status.invisible,
            activity=discord.Activity(type=discord.ActivityType.listening, name="JK")
        )
        print("Presence set to invisible with 'Listening to JK'")
    except Exception as e:
        print(f"Failed to set presence: {e}")
    # Setup help command
    try:
        await setup_help_command(tree, OWNER_ID)
        print("Help command setup completed")
    except Exception as e:
        print(f"Failed to setup help command: {e}")
    # Sync slash commands
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands globally")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    # Setup automod
    try:
        await automod.setup(client, MOD_CHANNEL_ID)
        print("Automod setup completed")
    except Exception as e:
        print(f"Failed to setup automod: {e}")

@client.event
async def on_message(message):
    if message.author.bot:
        return
    # Handle owner commands
    if message.author.id == OWNER_ID:
        print(f"Processing command from owner: {message.content}")
        try:
            await handle_command(client, message, send_status)
        except Exception as e:
            print(f"Error handling owner command: {e}")
    # Call automod's on_message listener
    try:
        for listener in client._listeners.get('on_message', []):
            if listener != on_message:  # Avoid recursive call
                await listener(message)
    except Exception as e:
        print(f"Error in message listener: {e}")

async def send_status(channel, text, **kwargs):
    return await channel.send(text, **kwargs)

client.run(TOKEN)