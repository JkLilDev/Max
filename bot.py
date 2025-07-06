import discord
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

DELETE_EMOJI = "🧹"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

# Delete all messages in channel
async def delete_all_messages(channel, command_message):
    status = await channel.send(f"{DELETE_EMOJI} Deleting all messages...")
    await asyncio.sleep(1)

    async for msg in channel.history(limit=None, oldest_first=False):
        if msg.id not in [command_message.id, status.id]:
            try:
                await msg.delete()
                await asyncio.sleep(0.3)
            except:
                continue

    try:
        await command_message.delete()
        await status.delete()
    except:
        pass

# Delete all messages from user
async def delete_user_messages(channel, user, command_message, max_count=None):
    status = await channel.send(f"{DELETE_EMOJI} Deleting messages from {user.display_name}...")
    await asyncio.sleep(1)
    deleted = 0

    async for msg in channel.history(limit=None, oldest_first=False):
        if msg.id in [command_message.id, status.id]:
            continue
        if msg.author.id == user.id:
            try:
                await msg.delete()
                deleted += 1
                await asyncio.sleep(0.3)
                if max_count and deleted >= max_count:
                    break
            except:
                continue

    try:
        await command_message.delete()
        await status.delete()
    except:
        pass

# Delete filtered messages (e.g., bot/user)
async def delete_filtered(channel, command_message, check):
    status = await channel.send(f"{DELETE_EMOJI} Deleting filtered messages...")
    await asyncio.sleep(1)

    async for msg in channel.history(limit=None, oldest_first=False):
        if msg.id in [command_message.id, status.id]:
            continue
        if check(msg):
            try:
                await msg.delete()
                await asyncio.sleep(0.3)
            except:
                continue

    try:
        await command_message.delete()
        await status.delete()
    except:
        pass

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

    content = message.content.lower()
    args = content.split()
    mentions = message.mentions

    # clean all
    if content == "clean all":
        await delete_all_messages(message.channel, message)
        return

    # clean all @user
    if len(args) >= 3 and args[0] == "clean" and args[1] == "all" and mentions:
        await delete_user_messages(message.channel, mentions[0], message)
        return

    # clean <number> @user
    if len(args) >= 3 and args[0] == "clean" and args[1].isdigit() and mentions:
        count = int(args[1])
        await delete_user_messages(message.channel, mentions[0], message, max_count=count)
        return

    # clean <number>
    if len(args) == 2 and args[0] == "clean" and args[1].isdigit():
        count = int(args[1])
        status = await message.channel.send(f"{DELETE_EMOJI} Deleting {count} messages...")
        await asyncio.sleep(1)
        deleted = 0

        async for msg in message.channel.history(limit=None, oldest_first=False):
            if msg.id in [message.id, status.id]:
                continue
            try:
                await msg.delete()
                deleted += 1
                await asyncio.sleep(0.3)
                if deleted >= count:
                    break
            except:
                continue

        try:
            await message.delete()
            await status.delete()
        except:
            pass
        return

    # clean bot
    if content == "clean bot":
        await delete_filtered(message.channel, message, lambda m: m.author.bot)
        return

    # clean user
    if content == "clean user":
        await delete_filtered(message.channel, message, lambda m: not m.author.bot)
        return

    # kick @user
    if content.startswith("kick") and mentions:
        await mentions[0].kick(reason=f"Kicked by {message.author}")
        await message.channel.send(f"👢 {mentions[0].mention} has been kicked.")
        return

    # ban @user
    if content.startswith("ban") and mentions:
        await mentions[0].ban(reason=f"Banned by {message.author}")
        await message.channel.send(f"🔨 {mentions[0].mention} has been banned.")
        return

client.run(TOKEN)