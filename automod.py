import discord
from discord.ext import commands

SENSITIVE_WORDS = ["badword", "anotherbadword"]  # Add your sensitive words here
SENSITIVE_LINKS = ["discord.gg/", "bit.ly/", "t.me/"]  # Add patterns to detect

MOD_CHANNEL_ID = 1387165662975103139  # Change to your mod channel ID

class AutoModView(discord.ui.View):
    def __init__(self, user, message, mod_channel, client):
        super().__init__(timeout=None)
        self.user = user
        self.message = message
        self.mod_channel = mod_channel
        self.client = client

    async def send_dm(self, user, content):
        try:
            await user.send(content)
        except Exception:
            pass  # User might have DMs off

    async def take_action(self, interaction, action):
        # Remove dropdown
        self.clear_items()
        # Set footer
        embed = interaction.message.embeds[0]
        embed.set_footer(
            text=f"{action} by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.message.edit(embed=embed, view=None)
        # Take action
        if action == "Warn":
            await self.send_dm(self.user, "You have been warned for breaking the server rules.")
            await interaction.response.send_message("User has been warned.", ephemeral=True)
        elif action == "Kick":
            await self.send_dm(self.user, "You have been kicked for breaking the server rules.")
            await self.user.kick(reason="AutoMod violation")
            await interaction.response.send_message("User has been kicked.", ephemeral=True)
        elif action == "Ban":
            await self.send_dm(self.user, "You have been banned for breaking the server rules.")
            await self.user.ban(reason="AutoMod violation")
            await interaction.response.send_message("User has been banned.", ephemeral=True)
        elif action == "Ignore":
            await interaction.response.send_message("Ignored.", ephemeral=True)

    @discord.ui.select(
        placeholder="Choose an action...",
        options=[
            discord.SelectOption(label="Warn", description="Warn the user via DM", emoji="⚠️"),
            discord.SelectOption(label="Kick", description="Kick the user", emoji="👢"),
            discord.SelectOption(label="Ban", description="Ban the user", emoji="🔨"),
            discord.SelectOption(label="Ignore", description="Remove this menu", emoji="🚫"),
        ],
        custom_id="automod_dropdown"
    )
    async def select_callback(self, select, interaction: discord.Interaction):
        action = select.values[0]
        await self.take_action(interaction, action)

async def check_message(message: discord.Message, client):
    if message.author.bot:
        return

    # Detect sensitive words/links (case-insensitive)
    lower_content = message.content.lower()
    detected = any(word in lower_content for word in SENSITIVE_WORDS) or any(link in lower_content for link in SENSITIVE_LINKS)
    if not detected:
        return

    # Delete offending message
    await message.delete()

    # Prepare embed
    embed = discord.Embed(
        title="Auto-Mod Alert",
        color=discord.Color.red()
    )
    embed.add_field(name="User", value=message.author.mention, inline=True)
    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="Content", value=discord.utils.escape_markdown(message.content), inline=False)
    embed.set_thumbnail(url=message.author.display_avatar.url)
    embed.set_footer(text="Choose an action below.")

    # Send to mod channel with dropdown
    mod_channel = message.guild.get_channel(MOD_CHANNEL_ID)
    view = AutoModView(message.author, message, mod_channel, client)
    await mod_channel.send(embed=embed, view=view)