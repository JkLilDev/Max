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
            print(f"Cannot send DM to {user.display_name} - DMs disabled")
            return False
        except Exception as e:
            print(f"Error sending DM to {user.display_name}: {e}")
            return False

    async def take_action(self, interaction: discord.Interaction, action: str):
        try:
            # Defer the interaction immediately
            await interaction.response.defer(ephemeral=True)
            
            # Get user data from stored pending actions if not available
            if not self.user_id and self.message_id:
                stored_data = get_pending_action(self.message_id)
                if stored_data:
                    self.user_id = stored_data.get('user_id')
                    self.original_message = stored_data.get('original_message')
                    self.channel_id = stored_data.get('channel_id')
                    self.guild_id = stored_data.get('guild_id')

            # Get guild and user
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("❌ Could not find server information.", ephemeral=True)
                return
                
            user = guild.get_member(self.user_id) if self.user_id else None
            if not user:
                await interaction.followup.send("<a:Error:1393537029148639232> User not found in server.", ephemeral=True)
                return

            # Get the original embed
            if not interaction.message.embeds:
                await interaction.followup.send("❌ Could not find embed information.", ephemeral=True)
                return
                
            embed = interaction.message.embeds[0].copy()

            # Update embed with action taken
            embed.timestamp = discord.utils.utcnow()
            embed.set_footer(
                text=f"{action} by {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            # Set color based on action
            color_map = {
                "Warn": discord.Color.yellow(),
                "Ignore": discord.Color.grey()
            }
            embed.color = color_map.get(action, discord.Color.grey())

            # Remove the dropdown and update the message
            try:
                await interaction.message.edit(embed=embed, view=None)
            except Exception as e:
                print(f"Error updating message: {e}")

            # Remove from pending actions
            if self.message_id:
                remove_pending_action(self.message_id)

            # Take the appropriate action
            if action == "Warn":
                warning_message = (
                    f"🔔 **Warning: Rule Violation Detected**\n\n"
                    f"We have detected that you have violated one or more server rules in **{guild.name}**.\n\n"
                    f"📌 Please take a moment to read and understand our community guidelines to avoid further actions.\n\n"
                    f"⚠️ Continued violations may lead to stricter consequences, including timeouts, kicks, or bans.\n\n"
                    f"If you believe this was a mistake or need clarification, feel free to contact a staff member.\n\n"
                    f"— Moderation Team\n"
                    f"{guild.name}"
                )
                dm_success = await self.send_dm(user, warning_message)
                if dm_success:
                    await interaction.followup.send(f"✅ Warning sent to {user.display_name}", ephemeral=True)
                else:
                    await interaction.followup.send(f"⚠️ Warning processed, but couldn't send DM to {user.display_name}", ephemeral=True)
            elif action == "Ignore":
                await interaction.followup.send("✅ Alert ignored", ephemeral=True)

        except Exception as e:
            print(f"Error in take_action: {e}")
            try:
                await interaction.followup.send(f"❌ An error occurred while processing the action: {str(e)}", ephemeral=True)
            except:
                pass

    @discord.ui.select(
        placeholder="Choose an action...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Warn", description="Warn user", emoji="<a:Error:1393537029148639232>"),
            discord.SelectOption(label="Ignore", description="Ignore alert", emoji="<a:Sleep:1393538986697293994>"),
        ],
        custom_id="persistent_automod_dropdown"
    )
    async def select_callback(self, select, interaction: discord.Interaction):
        action = select.values[0]
        await self.take_action(interaction, action)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        print(f"View error: {error}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

async def setup_persistent_views(client):
    """Setup persistent views for the bot"""
    view = PersistentAutoModView()
    client.add_view(view)
    print("✅ Persistent automod views setup complete")

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
            print(f"Cannot delete message - missing permissions")
        except discord.NotFound:
            print(f"Message already deleted")
        except Exception as e:
            print(f"Error deleting message: {e}")

        mod_channel = message.guild.get_channel(MOD_CHANNEL_ID)
        if not mod_channel:
            print(f"Mod channel not found: {MOD_CHANNEL_ID}")
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
            print(f"Auto-mod alert sent for user {message.author.display_name}")
        except discord.Forbidden:
            print(f"Cannot send to mod channel - missing permissions")
        except Exception as e:
            print(f"Error sending auto-mod alert: {e}")

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