import discord
import json
import os
import re
import asyncio
from discord.ext import commands
from typing import Dict, Any, Optional
import time
import datetime

MOD_CHANNEL_ID = 1387165662975103139

pending_actions: Dict[str, Dict[str, Any]] = {}

def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

def save_pending_action(message_id: str, data: Dict[str, Any]):
    pending_actions[message_id] = data

def get_pending_action(message_id: str) -> Optional[Dict[str, Any]]:
    return pending_actions.get(message_id)

def remove_pending_action(message_id: str):
    if message_id in pending_actions:
        del pending_actions[message_id]

class PersistentAutoModView(discord.ui.View):
    def __init__(self, user_id: int = None, original_message: str = None, channel_id: int = None, guild_id: int = None, message_id: str = None):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.original_message = original_message
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.message_id = message_id

    async def send_dm(self, user, text):
        try:
            await user.send(text)
            return True
        except discord.Forbidden:
            return False
        except Exception:
            return False

    async def take_action(self, interaction: discord.Interaction, action: str):
        await interaction.response.defer(ephemeral=True)

        if not self.user_id and self.message_id:
            stored_data = get_pending_action(self.message_id)
            if stored_data:
                self.user_id = stored_data.get('user_id')
                self.original_message = stored_data.get('original_message')
                self.channel_id = stored_data.get('channel_id')
                self.guild_id = stored_data.get('guild_id')

        guild = interaction.guild
        user = guild.get_member(self.user_id) if self.user_id else None

        if not user:
            await interaction.followup.send("<a:Error:1393537029148639232> User not found in server.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        # Role & permission checks before modifying embed or removing action
        if action == "Kick":
            if user.top_role >= guild.me.top_role:
                await interaction.followup.send("<a:Error:1393537029148639232> Cannot kick user - they have a higher or equal role than the bot.", ephemeral=True)
                return
        if action == "Ban":
            if user.top_role >= guild.me.top_role:
                await interaction.followup.send("<a:Error:1393537029148639232> Cannot ban user - they have a higher or equal role than the bot.", ephemeral=True)
                return
            if user.guild_permissions.administrator:
                await interaction.followup.send("<a:Error:1393537029148639232> Cannot ban user - they are an administrator.", ephemeral=True)
                return

        # Remove dropdown and update embed
        self.clear_items()
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(
            text=f"{action} by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )

        color_map = {
            "Ban": discord.Color.dark_red(),
            "Kick": discord.Color.orange(),
            "Warn": discord.Color.yellow(),
            "Ignore": discord.Color.grey()
        }
        embed.color = color_map.get(action, discord.Color.grey())

        try:
            await interaction.message.edit(embed=embed, view=None)
        except Exception:
            pass

        if self.message_id:
            remove_pending_action(self.message_id)

        # Only reply on failures (already handled above), so now only act
        if action == "Warn":
            await self.send_dm(user, f"You have been warned in **{guild.name}** for breaking the server rules.")
        elif action == "Kick":
            await self.send_dm(user, f"You have been kicked from **{guild.name}** for breaking the server rules.")
            try:
                await guild.kick(user, reason=f"AutoMod violation - Actioned by {interaction.user}")
            except Exception:
                pass
        elif action == "Ban":
            await self.send_dm(user, f"You have been banned from **{guild.name}** for breaking the server rules.")
            try:
                await guild.ban(user, reason=f"AutoMod violation - Actioned by {interaction.user}", delete_message_days=0)
            except Exception:
                pass
        elif action == "Ignore":
            pass  # No reply needed

    @discord.ui.select(
        placeholder="Choose an action...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Warn", description="Warn user", emoji="<a:Error:1393537029148639232>"),
            discord.SelectOption(label="Kick", description="Kick user", emoji="<a:Kick:1393539202783645696>"),
            discord.SelectOption(label="Ban", description="Ban user", emoji="<a:Ban:1393539007648104580>"),
            discord.SelectOption(label="Ignore", description="Ignore alert", emoji="<a:Sleep:1393538986697293994>"),
        ],
        custom_id="persistent_automod_dropdown"
    )
    async def select_callback(self, interaction: discord.Interaction, select):
        action = select.values[0]
        await self.take_action(interaction, action)

async def setup_persistent_views(client):
    view = PersistentAutoModView()
    client.add_view(view)

def contains_sensitive_content(text: str, config: dict) -> tuple:
    text_lower = text.lower()
    for word in config.get("sensitive_words", []):
        word_lower = word.lower()
        if re.search(r'\b' + re.escape(word_lower) + r'\b', text_lower):
            return True, word, "word"
    for link in config.get("sensitive_links", []):
        if link.lower() in text_lower:
            return True, link, "link"
    return False, "", ""

async def check_message(message: discord.Message, client):
    if message.author.bot:
        return
    if not message or not message.content:
        return
    if not message.guild:
        return
    config = load_config()
    if not config:
        return
    is_triggered, triggered_content, content_type = contains_sensitive_content(message.content, config)
    if is_triggered:
        try:
            await message.delete()
        except discord.Forbidden:
            pass
        except discord.NotFound:
            pass
        except Exception:
            pass

        mod_channel = message.guild.get_channel(MOD_CHANNEL_ID)
        if not mod_channel:
            return

        embed = discord.Embed(
            title="<a:Alert:1393535690859479052> Auto-Mod Alert",
            color=discord.Color.red(),
            timestamp=message.created_at
        )
        embed.add_field(name="User", value=f"{message.author.mention}", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content Type", value=content_type.title(), inline=True)
        safe_content = discord.utils.escape_markdown(message.content)
        if len(safe_content) > 1000:
            safe_content = safe_content[:997] + "..."
        embed.add_field(name="Message Content", value=f"```{safe_content}```", inline=False)
        joined_at = "Unknown"
        if hasattr(message.author, 'joined_at') and message.author.joined_at:
            joined_at = f"<t:{int(message.author.joined_at.timestamp())}:R>"
        embed.add_field(name="Joined Server", value=joined_at, inline=True)
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text="Choose an action below.")

        view = PersistentAutoModView(
            user_id=message.author.id,
            original_message=message.content,
            channel_id=message.channel.id,
            guild_id=message.guild.id
        )

        try:
            sent_message = await mod_channel.send(embed=embed, view=view)
            save_pending_action(str(sent_message.id), {
                'user_id': message.author.id,
                'original_message': message.content,
                'channel_id': message.channel.id,
                'guild_id': message.guild.id
            })
            view.message_id = str(sent_message.id)
        except discord.Forbidden:
            pass
        except Exception:
            pass

def get_pending_actions_count():
    return len(pending_actions)

def clear_all_pending_actions():
    global pending_actions
    pending_actions = {}

__all__ = [
    'setup_persistent_views',
    'check_message',
    'PersistentAutoModView',
    'load_config',
    'get_pending_actions_count',
    'clear_all_pending_actions'
]