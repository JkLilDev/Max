import discord
import json
import os

# Set your mod channel ID here (replace with your actual channel ID)
MOD_CHANNEL_ID = 1387165662975103139

# Load configuration
def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("config.json not found! Creating default config...")
        # Create default config if it doesn't exist
        default_config = {
            "sensitive_words": ["badword", "anotherbadword"],
            "sensitive_links": ["discord.gg/", "bit.ly/", "t.me/"]
        }
        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=2)
        return default_config

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
        except Exception:
            pass  # User may have DMs off

    async def take_action(self, interaction: discord.Interaction, action: str):
        # Get the user and guild
        guild = interaction.guild
        user = guild.get_member(self.user_id)
        
        if not user:
            await interaction.response.send_message("User not found in server.", ephemeral=True)
            return

        # Remove dropdown and update embed
        self.clear_items()
        embed = interaction.message.embeds[0]
        
        # Update footer with action taken
        embed.set_footer(
            text=f"{action} by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        
        # Update embed color based on action
        if action == "Ban":
            embed.color = discord.Color.dark_red()
        elif action == "Kick":
            embed.color = discord.Color.orange()
        elif action == "Warn":
            embed.color = discord.Color.yellow()
        elif action == "Ignore":
            embed.color = discord.Color.light_grey()
        
        await interaction.message.edit(embed=embed, view=None)
        
        # Take action
        if action == "Warn":
            await self.send_dm(user, f"You have been warned in **{guild.name}** for breaking the server rules.")
            await interaction.response.send_message(f"✅ Warned {user.mention}.", ephemeral=True)
            
        elif action == "Kick":
            await self.send_dm(user, f"You have been kicked from **{guild.name}** for breaking the server rules.")
            try:
                await guild.kick(user, reason=f"AutoMod violation - Actioned by {interaction.user}")
                await interaction.response.send_message(f"✅ Kicked {user.mention}.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Failed to kick user - insufficient permissions.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to kick user: {str(e)}", ephemeral=True)
                
        elif action == "Ban":
            await self.send_dm(user, f"You have been banned from **{guild.name}** for breaking the server rules.")
            try:
                await guild.ban(user, reason=f"AutoMod violation - Actioned by {interaction.user}")
                await interaction.response.send_message(f"✅ Banned {user.mention}.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Failed to ban user - insufficient permissions.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to ban user: {str(e)}", ephemeral=True)
                
        elif action == "Ignore":
            await interaction.response.send_message("✅ Alert ignored.", ephemeral=True)

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
    client.add_view(PersistentAutoModView(0, "", 0, 0))  # Dummy view for persistence
    print("✅ Persistent AutoMod views setup complete")

async def check_message(message: discord.Message, client):
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
    
    content = message.content.lower()
    
    # Check for sensitive words or links
    triggered = False
    triggered_content = ""
    
    # Check sensitive words
    for word in config.get("sensitive_words", []):
        if word.lower() in content:
            triggered = True
            triggered_content = word
            break
    
    # Check sensitive links if no word was triggered
    if not triggered:
        for link in config.get("sensitive_links", []):
            if link.lower() in content:
                triggered = True
                triggered_content = link
                break
    
    if triggered:
        # Try to delete the message
        try:
            await message.delete()
        except discord.Forbidden:
            print(f"No permission to delete message in {message.channel}")
        except discord.NotFound:
            print("Message already deleted")
        except Exception as e:
            print(f"Error deleting message: {e}")

        # Get mod channel
        mod_channel = message.guild.get_channel(MOD_CHANNEL_ID)
        if not mod_channel:
            print(f"Mod channel with ID {MOD_CHANNEL_ID} not found")
            return

        # Create embed
        embed = discord.Embed(
            title="🚨 Auto-Mod Alert",
            color=discord.Color.red(),
            timestamp=message.created_at
        )
        embed.add_field(name="User", value=f"{message.author.mention} ({message.author})", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="User ID", value=message.author.id, inline=True)
        embed.add_field(name="Triggered By", value=f"```{triggered_content}```", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(message.author.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Joined Server", value=f"<t:{int(message.author.joined_at.timestamp())}:R>" if message.author.joined_at else "Unknown", inline=True)
        embed.add_field(name="Message Content", value=f"```{discord.utils.escape_markdown(message.content)[:1000]}```", inline=False)
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
        except discord.Forbidden:
            print(f"No permission to send message in mod channel {mod_channel}")
        except Exception as e:
            print(f"Error sending automod alert: {e}")