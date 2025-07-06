import asyncio
import discord
import os

async def delete_all_messages(channel, command_message, send_status):
    status = await send_status(channel, "🧹 Deleting all messages...")
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

async def delete_user_messages(channel, user, command_message, send_status, max_count=None):
    status = await send_status(channel, f"🧹 Deleting messages from {user.display_name}...")
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

async def delete_filtered(channel, command_message, send_status, check):
    status = await send_status(channel, "🧹 Deleting filtered messages...")
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

async def delete_channel(channel, send_status):
    await send_status(channel, "🗑️ Deleting this channel...")
    await asyncio.sleep(1)
    await channel.delete()

async def delete_word_messages(channel, command_message, send_status, word):
    status = await send_status(channel, f"🧹 Deleting messages containing '{word}'...")
    await asyncio.sleep(1)
    word_lower = word.lower()
    async for msg in channel.history(limit=None, oldest_first=False):
        if msg.id in [command_message.id, status.id]:
            continue
        if word_lower in msg.content.lower():
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

async def lock_channel(channel, send_status):
    overwrite = channel.overwrites_for(channel.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)
    await send_status(channel, "🔒 Channel locked. Members cannot send messages.")

async def unlock_channel(channel, send_status):
    overwrite = channel.overwrites_for(channel.guild.default_role)
    overwrite.send_messages = None  # Reset to default
    await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)
    await send_status(channel, "🔓 Channel unlocked. Members can send messages.")

async def send_help(message):
    help_text = (
        "**Berry Bot Commands:**\n"
        "• `berry all` — Delete all messages in the channel\n"
        "• `berry all @user` — Delete all messages from the mentioned user\n"
        "• `berry <number> @user` — Delete N messages from the mentioned user\n"
        "• `berry <number>` — Delete N messages from the channel\n"
        "• `berry bot` — Delete all bot messages\n"
        "• `berry user` — Delete all user (not bot) messages\n"
        "• `berry dlt <word>` — Delete all messages containing the word\n"
        "• `berry dlt ch` — Delete this channel\n"
        "• `berry lock` — Lock this channel (prevent @everyone from sending messages)\n"
        "• `berry unlock` — Unlock this channel (allow @everyone to send messages)\n"
        "• `kick @user` — Kick the mentioned user\n"
        "• `berry help` — Show this help message\n"
    )
    try:
        await message.author.send(help_text)
    except Exception:
        # fallback if DM fails
        await message.channel.send(f"{message.author.mention} Could not send you a DM. Here are the commands:\n{help_text}")

async def handle_command(client, message, send_status):
    content = message.content.lower()
    args = message.content.split()
    args_lower = [arg.lower() for arg in args]
    mentions = message.mentions

    # berry help
    if content.strip() == "berry help":
        await send_help(message)
        return

    # berry all
    if content.strip() == "berry all":
        await delete_all_messages(message.channel, message, send_status)
        return

    # berry all @user
    if len(args_lower) >= 3 and args_lower[0] == "berry" and args_lower[1] == "all" and mentions:
        await delete_user_messages(message.channel, mentions[0], message, send_status)
        return

    # berry <number> @user
    if len(args_lower) >= 3 and args_lower[0] == "berry" and args_lower[1].isdigit() and mentions:
        count = int(args_lower[1])
        await delete_user_messages(message.channel, mentions[0], message, send_status, max_count=count)
        return

    # berry <number>
    if len(args_lower) == 2 and args_lower[0] == "berry" and args_lower[1].isdigit():
        count = int(args_lower[1])
        status = await send_status(message.channel, f"🧹 Deleting {count} messages...")
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

    # berry bot
    if content.strip() == "berry bot":
        await delete_filtered(message.channel, message, send_status, lambda m: m.author.bot)
        return

    # berry user
    if content.strip() == "berry user":
        await delete_filtered(message.channel, message, send_status, lambda m: not m.author.bot)
        return

    # berry dlt <word>
    if len(args_lower) >= 3 and args_lower[0] == "berry" and args_lower[1] == "dlt" and args_lower[2] != "ch":
        word = ' '.join(args[2:])
        await delete_word_messages(message.channel, message, send_status, word)
        return

    # berry dlt ch
    if content.strip() == "berry dlt ch":
        await delete_channel(message.channel, send_status)
        return

    # berry lock
    if content.strip() == "berry lock":
        await lock_channel(message.channel, send_status)
        return

    # berry unlock
    if content.strip() == "berry unlock":
        await unlock_channel(message.channel, send_status)
        return

    # kick @user
    if args_lower[0] == "kick" and mentions:
        await mentions[0].kick(reason=f"Kicked by {message.author}")
        await send_status(message.channel, f"👢 {mentions[0].mention} has been kicked.")
        return