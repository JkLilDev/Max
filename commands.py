import asyncio
import discord
import os

BERRY_EMOJI = "<a:Berry:1391268294182305905>"

COMMANDS_HELP_TEXT = (
    "**Berry Bot Commands:**\n\n"
    "• **/help** — Show this help message\n\n"
    "• **berry clean all** — Delete all messages in the channel\n\n"
    "• **berry @user clean all** — Delete all messages from the mentioned user\n\n"
    "• **berry @user <number> clean** — Delete N messages from the mentioned user\n\n"
    "• **berry <number> clean** — Delete N messages from the channel\n\n"
    "• **berry clean bot** — Delete all bot messages\n\n"
    "• **berry clean user** — Delete all user (not bot) messages\n\n"
    "• **berry <word> clean** — Delete all messages containing the word\n\n"
    "• **berry dlt** — Delete this channel\n\n"
    "• **berry dlt #channel** — Delete the mentioned channel\n\n"
    "• **berry lock** — Lock this channel (prevent @everyone from sending messages)\n\n"
    "• **berry unlock** — Unlock this channel (allow @everyone to send messages)\n\n"
    "• **berry lock #channel** — Lock the mentioned channel\n\n"
    "• **berry unlock #channel** — Unlock the mentioned channel\n\n"
    "• **berry kick @user** — Kick the mentioned user\n\n"
    "• **berry ban @user** — Ban the mentioned user\n\n"
)

async def setup_help_command(tree, owner_id):
    @tree.command(
        name="help",
        description="Show all bot commands"
    )
    async def help_command(interaction: discord.Interaction):
        if interaction.user.id == owner_id:
            embed = discord.Embed(
                title="LilBerry Commands",
                description=COMMANDS_HELP_TEXT,
                color=discord.Color.purple()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            owner_mention = f"<@{owner_id}>"
            await interaction.response.send_message(
                f"Sorry, I am only listening to {owner_mention}",
                ephemeral=True
            )

async def delete_all_messages(channel, command_message, send_status):
    status = await send_status(channel, f"{BERRY_EMOJI} Deleting all messages...")
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
    status = await send_status(channel, f"{BERRY_EMOJI} Deleting messages from {user.display_name}...")
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
    status = await send_status(channel, f"{BERRY_EMOJI} Deleting filtered messages...")
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
    await send_status(channel, f"{BERRY_EMOJI} Deleting this channel...")
    await asyncio.sleep(1)
    await channel.delete()

async def delete_mentioned_channel(channel, send_status):
    await send_status(channel, f"{BERRY_EMOJI} Deleting the mentioned channel...")
    await asyncio.sleep(1)
    await channel.delete()

async def delete_word_messages(channel, command_message, send_status, word):
    status = await send_status(channel, f"{BERRY_EMOJI} Deleting messages containing '{word}'...")
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

async def lock_channel(channel, send_status, info_message=None):
    overwrite = channel.overwrites_for(channel.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)
    msg = info_message if info_message else "🔒 Channel locked."
    await send_status(channel, msg)

async def unlock_channel(channel, send_status, info_message=None):
    overwrite = channel.overwrites_for(channel.guild.default_role)
    overwrite.send_messages = None  # Reset to default
    await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)
    msg = info_message if info_message else "🔓 Channel unlocked."
    await send_status(channel, msg)

async def handle_command(client, message, send_status):
    content = message.content
    args = content.split()
    args_lower = [arg.lower() for arg in args]
    mentions = message.mentions
    channel_mentions = message.channel_mentions if hasattr(message, 'channel_mentions') else []

    # berry clean all
    if content.strip().lower() == "berry clean all":
        await delete_all_messages(message.channel, message, send_status)
        return

    # berry @user clean all
    if (
        len(args_lower) >= 4 and 
        args_lower[0] == "berry" and 
        len(mentions) >= 1 and
        args_lower[2] == "clean" and 
        args_lower[3] == "all"
    ):
        await delete_user_messages(message.channel, mentions[0], message, send_status)
        return

    # berry @user <number> clean
    if (
        len(args_lower) >= 4 and 
        args_lower[0] == "berry" and 
        len(mentions) >= 1 and
        args_lower[3] == "clean" and 
        args_lower[2].isdigit()
    ):
        count = int(args_lower[2])
        await delete_user_messages(message.channel, mentions[0], message, send_status, max_count=count)
        return

    # berry <number> clean
    if (
        len(args_lower) == 3 and 
        args_lower[0] == "berry" and 
        args_lower[2] == "clean" and
        args_lower[1].isdigit()
    ):
        count = int(args_lower[1])
        status = await send_status(message.channel, f"{BERRY_EMOJI} Deleting {count} messages...")
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

    # berry clean bot
    if content.strip().lower() == "berry clean bot":
        await delete_filtered(message.channel, message, send_status, lambda m: m.author.bot)
        return

    # berry clean user
    if content.strip().lower() == "berry clean user":
        await delete_filtered(message.channel, message, send_status, lambda m: not m.author.bot)
        return

    # berry <word> clean
    if (
        len(args_lower) >= 3 and 
        args_lower[0] == "berry" and 
        args_lower[-1] == "clean"
        and not (args_lower[1] == "clean" or args_lower[1].isdigit() or args_lower[1] == "dlt" or args_lower[1].startswith("<@"))  # skip other commands
    ):
        word = ' '.join(args[1:-1])
        await delete_word_messages(message.channel, message, send_status, word)
        return

    # berry dlt (delete this channel)
    if content.strip().lower() == "berry dlt":
        await delete_channel(message.channel, send_status)
        return

    # berry dlt #channel (delete mentioned channel)
    if (
        len(args_lower) >= 3 and
        args_lower[0] == "berry" and
        args_lower[1] == "dlt" and
        len(channel_mentions) > 0
    ):
        for ch in channel_mentions:
            await send_status(message.channel, f"{BERRY_EMOJI} Deleting the channel {ch.mention} ...")
            await asyncio.sleep(1)
            await ch.delete()
        return

    # berry lock (no mention)
    if content.strip().lower() == "berry lock":
        await lock_channel(message.channel, send_status)
        return

    # berry unlock (no mention)
    if content.strip().lower() == "berry unlock":
        await unlock_channel(message.channel, send_status)
        return

    # berry lock #channel (lock the mentioned channel, reply in original channel)
    if (
        len(args_lower) >= 3 and
        args_lower[0] == "berry" and
        args_lower[1] == "lock" and
        len(channel_mentions) > 0
    ):
        for ch in channel_mentions:
            await lock_channel(
                ch, 
                lambda chan, msg: send_status(message.channel, f"🔒 Channel lock {ch.mention}."),
                info_message=None
            )
        return

    # berry unlock #channel (unlock the mentioned channel, reply in original channel)
    if (
        len(args_lower) >= 3 and
        args_lower[0] == "berry" and
        args_lower[1] == "unlock" and
        len(channel_mentions) > 0
    ):
        for ch in channel_mentions:
            await unlock_channel(
                ch, 
                lambda chan, msg: send_status(message.channel, f"🔓 Channel unlock {ch.mention}."),
                info_message=None
            )
        return

    # berry kick @user
    if (
        len(args_lower) >= 3 and
        args_lower[0] == "berry" and
        args_lower[1] == "kick" and
        len(mentions) > 0
    ):
        await mentions[0].kick(reason=f"Kicked by {message.author}")
        await send_status(message.channel, f"👢 {mentions[0].mention} has been kicked.")
        return

    # berry ban @user
    if (
        len(args_lower) >= 3 and
        args_lower[0] == "berry" and
        args_lower[1] == "ban" and
        len(mentions) > 0
    ):
        await mentions[0].ban(reason=f"Banned by {message.author}")
        await send_status(message.channel, f"🔨 {mentions[0].mention} has been banned.")
        return