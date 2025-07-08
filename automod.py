import discord

# List your sensitive words/links here (lowercase for case-insensitive match)
SENSITIVE_WORDS = ["badword", "anotherbadword"]
SENSITIVE_LINKS = ["discord.gg/", "bit.ly/", "t.me/"]

# Set your mod channel ID here (replace with your actual channel ID)
MOD_CHANNEL_ID = 1387165662975103139

class AutoModView(discord.ui.View):
    def __init__(self, user, message, moderator, client):
        super().__init__(timeout=None)
        self.user = user
        self.msg_content = message.content
        self.channel = message.channel
        self.client = client
        self.guild = message.guild
        self.message = message
        self.moderator = moderator

    async def send_dm(self, text):
        try:
            await self.user.send(text)
        except Exception:
            pass  # User may have DMs off

    async def take_action(self, interaction, action):
        # Remove dropdown
        self.clear_items()
        embed = interaction.message.embeds[0]
        embed.set_footer(
            text=f"{action} by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.message.edit(embed=embed, view=None)
        # Take action
        if action == "Warn":
            await self.send_dm("You have been warned for breaking the server rules.")
            await interaction.response.send_message("Warned user.", ephemeral=True)
        elif action == "Kick":
            await self.send_dm("You have been kicked for breaking the server rules.")
            try:
                await self.guild.kick(self.user, reason="AutoMod violation")
            except Exception:
                pass
            await interaction.response.send_message("Kicked user.", ephemeral=True)
        elif action == "Ban":
            await self.send_dm("You have been banned for breaking the server rules.")
            try:
                await self.guild.ban(self.user, reason="AutoMod violation")
            except Exception:
                pass
            await interaction.response.send_message("Banned user.", ephemeral=True)
        elif action == "Ignore":
            await interaction.response.send_message("Ignored.", ephemeral=True)

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
        custom_id="automod_dropdown"
    )
    async def select_callback(self, select, interaction: discord.Interaction):
        action = select.values[0]
        await self.take_action(interaction, action)

async def check_message(message: discord.Message, client):
    if message.author.bot:
        return

    content = message.content.lower()
    if any(word in content for word in SENSITIVE_WORDS) or any(link in content for link in SENSITIVE_LINKS):
        try:
            await message.delete()
        except Exception:
            pass  # might not have perms

        mod_channel = message.guild.get_channel(MOD_CHANNEL_ID)
        if not mod_channel:
            return

        embed = discord.Embed(
            title="Auto-Mod Alert",
            color=discord.Color.red()
        )
        embed.add_field(name="User", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content", value=discord.utils.escape_markdown(message.content), inline=False)
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text="Choose an action below.")

        view = AutoModView(message.author, message, None, client)
        await mod_channel.send(embed=embed, view=view)