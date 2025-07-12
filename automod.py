import discord
import json
import os
import re
from discord.ext import commands

# Set your mod channel ID here (replace with your actual channel ID)
MOD_CHANNEL_ID = 1387165662975103139

# Load configuration
def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ config.json not found! Bot will not work without it.")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing config.json: {e}")
        return None

class PersistentAutoModView(discord.ui.View):
    def __init__(self, user_id: int, original_message: str, channel_id: int, guild_id: int):
        super().__init__(timeout=None)  # No timeout for persistent views
        self.user_id = user_id
        self.original_message = original_message
        self.channel_id = channel_id
        self.guild_id = guild_id

    async def send_dm(self, user, text):
        try:
            await user.send(text)
            return True
        except discord.Forbidden:
            print(f"Cannot send DM to {user} - DMs disabled")
            return False
        except Exception as e:
            print(f"Error sending DM to {user}: {e}")
            return False

    async def take_action(self, interaction: discord.Interaction, action: str):
        # Defer the response first to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        # Get the user and guild
        guild = interaction.guild
        user = guild.get_member(self.user_id)

        if not user:
            await interaction.followup.send("❌ User not found in server.", ephemeral=True)
            return

        # Remove dropdown and update embed
        self.clear_items()
        embed = interaction.message.embeds[0]

        # Update footer with action taken
        embed.set_footer(
            text=f"{action} by {interaction.user.display_name} at {discord.utils.format_dt(discord.utils.utcnow(), 'F')}",
            icon_url=interaction.user.display_avatar.url,
        )

        # Update embed color based on action
        color_map = {
            "Ban": discord.Color.dark_red(),
            "Kick": discord.Color.orange(),
            "Warn": discord.Color.yellow(),
            "Ignore": discord.Color.light_grey()
        }
        embed.color = color_map.get(action, discord.Color.light_grey())

        # Update the message first
        try:
            await interaction.message.edit(embed=embed, view=None)
        except Exception as e:
            print(f"Error updating embed: {e}")

        # Take action
        if action == "Warn":
            dm_sent = await self.send_dm(user, f"⚠️ You have been warned in **{guild.name}** for breaking the server rules.")
            dm_status = " (DM sent)" if dm_sent else " (DM failed)"
            await interaction.followup.send(f"✅ Warned {user.mention}{dm_status}.", ephemeral=True)

        elif action == "Kick":
            dm_sent = await self.send_dm(user, f"👢 You have been kicked from **{guild.name}** for breaking the server rules.")
            try:
                # Check if bot can kick this user
                if user.top_role >= guild.me.top_role:
                    await interaction.followup.send("❌ Cannot kick user - they have a higher or equal role than the bot.", ephemeral=True)
                    return
                
                await guild.kick(user, reason=f"AutoMod violation - Actioned by {interaction.user}")
                dm_status = " (DM sent)" if dm_sent else " (DM failed)"
                await interaction.followup.send(f"✅ Kicked {user.mention}{dm_status}.", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("❌ Failed to kick user - insufficient permissions or user has higher role.", ephemeral=True)
            except discord.HTTPException as e:
                await interaction.followup.send(f"❌ Failed to kick user: {str(e)}", ephemeral=True)

        elif action == "Ban":
            dm_sent = await self.send_dm(user, f"🔨 You have been banned from **{guild.name}** for breaking the server rules.")
            try:
                # Check if bot can ban this user
                if user.top_role >= guild.me.top_role:
                    await interaction.followup.send("❌ Cannot ban user - they have a higher or equal role than the bot.", ephemeral=True)
                    return
                
                # Check if user is admin
                if user.guild_permissions.administrator:
                    await interaction.followup.send("❌ Cannot ban user - they are an administrator.", ephemeral=True)
                    return
                
                await guild.ban(user, reason=f"AutoMod violation - Actioned by {interaction.user}", delete_message_days=0)
                dm_status = " (DM sent)" if dm_sent else " (DM failed)"
                await interaction.followup.send(f"✅ Banned {user.mention}{dm_status}.", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("❌ Failed to ban user - insufficient permissions or user has higher role.", ephemeral=True)
            except discord.HTTPException as e:
                await interaction.followup.send(f"❌ Failed to ban user: {str(e)}", ephemeral=True)

        elif action == "Ignore":
            await interaction.followup.send("✅ Alert ignored.", ephemeral=True)

    @discord.ui.select(
        placeholder="Choose an action...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Warn", description="Warn user by DM", emoji="⚠️"),
            discord.SelectOption(label="Kick", description="Kick user", emoji="👢"),
            discord.SelectOption(label="Ban", description="Ban user", emoji="🔨"),
            discord.SelectOption(label="Ignore", description="Remove this menu", emoji="🚫"),
        ],
        custom_id="persistent_automod_dropdown"
    )
    async def select_callback(self, select, interaction: discord.Interaction):
        action = select.values[0]
        await self.take_action(interaction, action)

# Function to setup persistent views on bot startup
async def setup_persistent_views(client):
    """Call this function when the bot starts to re-add persistent views"""
    # Add a view with the custom_id to handle persistent interactions
    view = PersistentAutoModView(0, "", 0, 0)  # Dummy view for persistence
    client.add_view(view)
    print("✅ Persistent AutoMod views setup complete")

def contains_sensitive_content(text: str, config: dict) -> tuple:
    """
    Check if text contains sensitive content.
    Returns (is_triggered, triggered_content, content_type)
    """
    text_lower = text.lower()
    
    # Check sensitive words with word boundary matching
    for word in config.get("sensitive_words", []):
        word_lower = word.lower()
        # Use word boundaries for better matching
        if re.search(r'\b' + re.escape(word_lower) + r'\b', text_lower):
            return True, word, "word"
    
    # Check sensitive links
    for link in config.get("sensitive_links", []):
        if link.lower() in text_lower:
            return True, link, "link"
    
    return False, "", ""

async def check_message(message: discord.Message, client):
    """Main function to check messages for violations"""
    # Don't check bot messages
    if message.author.bot:
        return

    # Don't check if message is None or has no content
    if not message or not message.content:
        return

    # Don't check if guild exists (DM messages don't have guilds)
    if not message.guild:
        return

    # Load configuration
    config = load_config()
    if not config:
        print("❌ Cannot load config.json - AutoMod disabled")
        return
    
    # Check for sensitive content
    is_triggered, triggered_content, content_type = contains_sensitive_content(message.content, config)

    if is_triggered:
        print(f"🚨 AutoMod triggered by {content_type}: '{triggered_content}' in message from {message.author}")
        
        # Try to delete the message
        try:
            await message.delete()
            print(f"✅ Deleted message from {message.author}")
        except discord.Forbidden:
            print(f"❌ No permission to delete message in {message.channel}")
        except discord.NotFound:
            print("⚠️ Message already deleted")
        except Exception as e:
            print(f"❌ Error deleting message: {e}")

        # Get mod channel
        mod_channel = message.guild.get_channel(MOD_CHANNEL_ID)
        if not mod_channel:
            print(f"❌ Mod channel with ID {MOD_CHANNEL_ID} not found")
            return

        # Create embed
        embed = discord.Embed(
            title="🚨 Auto-Mod Alert",
            color=discord.Color.red(),
            timestamp=message.created_at
        )
        embed.add_field(name="User", value=f"{message.author.mention} ({message.author})", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="User ID", value=str(message.author.id), inline=True)
        embed.add_field(name="Triggered By", value=f"```{triggered_content}```", inline=True)
        embed.add_field(name="Content Type", value=content_type.title(), inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(message.author.created_at.timestamp())}:R>", inline=True)
        
        # Handle joined_at safely
        joined_at = "Unknown"
        if hasattr(message.author, 'joined_at') and message.author.joined_at:
            joined_at = f"<t:{int(message.author.joined_at.timestamp())}:R>"
        embed.add_field(name="Joined Server", value=joined_at, inline=True)
        
        # Safely escape and truncate message content
        safe_content = discord.utils.escape_markdown(message.content)
        if len(safe_content) > 1000:
            safe_content = safe_content[:997] + "..."
        embed.add_field(name="Message Content", value=f"```{safe_content}```", inline=False)
        
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text="Choose an action below - This alert will persist across bot restarts")

        # Create persistent view
        view = PersistentAutoModView(
            user_id=message.author.id,
            original_message=message.content,
            channel_id=message.channel.id,
            guild_id=message.guild.id
        )

        try:
            await mod_channel.send(embed=embed, view=view)
            print(f"✅ Sent automod alert to {mod_channel}")
        except discord.Forbidden:
            print(f"❌ No permission to send message in mod channel {mod_channel}")
        except Exception as e:
            print(f"❌ Error sending automod alert: {e}")