import discord
import os
from dotenv import load_dotenv
from commands import handle_command, setup_help_command
from keep_alive import keep_alive
from automod import handle_automod_message # Import the automod function

keep_alive()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
# Define your moderation channel ID. You might want to add this to your .env file too.
MOD_CHANNEL_ID = int(os.getenv("MOD_CHANNEL_ID")) # Make sure to add MOD_CHANNEL_ID to your .env file!

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f"✅ Bot is ready. Logged in as {client.user}")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="JK"))
    await setup_help_command(tree, OWNER_ID)
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands globally.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # First, let automod check the message
    # If automod handles the message (e.g., deletes it), it will return True.
    # In that case, we don't want to process it further for commands.
    automod_handled = await handle_automod_message(client, message, MOD_CHANNEL_ID)
    if automod_handled:
        return # Stop processing if automod took action

    # Continue with your existing command handling only if automod didn't act
    if message.author.id != OWNER_ID:
        return
    await handle_command(client, message, send_status)

async def send_status(channel, text, **kwargs):
    return await channel.send(text, **kwargs)

client.run(TOKEN)
