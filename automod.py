import discord
from discord import SelectOption
import re
import uuid  # For generating unique custom_id

# Sensitive words (English and Hindi)
SENSITIVE_WORDS_ENGLISH = [
    'damn', 'hell', 'fuck', 'shit', 'bitch', 'asshole', 'cunt', 'bastard',
    'idiot', 'moron', 'stupid', 'retard', 'douche', 'jerk', 'faggot', 'nigger'
    # Add more English words as needed
]

SENSITIVE_WORDS_HINDI = [
    'kutta', 'kutiya', 'harami', 'chutiya', 'bhenchod', 'madarchod', 
    'gandu', 'bakwas', 'bewakoof', 'chut', 'lund', 'gaand', 'bhosda',
    'saala', 'kamchor', 'pagal'
    # Add more Hindi words as needed
]

# Combine both lists
SENSITIVE_WORDS = SENSITIVE_WORDS_ENGLISH + SENSITIVE_WORDS_HINDI

# Comprehensive link pattern
LINK_PATTERN = r'(?i)(?:https?://|www\.|bit\.ly|tinyurl\.com|t\.co|goo\.gl)[^\s]*'

class ModerationView(discord.ui.View):
    def __init__(self, user, message, mod_message, mod_channel_id):
        super().__init__(timeout=None)  # No timeout for persistent view
        self.add_item(ModerationSelect(user, message, mod_message, mod_channel_id, self))

class ModerationSelect(discord.ui.Select):
    def __init__(self, user, message, mod_message, mod_channel_id, view):
        options = [
            SelectOption(label="Warn", value="warn", description="Send a warning DM"),
            SelectOption(label="Kick", value="kick", description="Kick user from server"),
            SelectOption(label="Ban", value="ban", description="Ban user from server"),
            SelectOption(label="Ignore", value="ignore", description="Take no action")
        ]
        # Generate a unique custom_id for persistence
        super().__init__(
            placeholder="Select an action",
            options=options,
            custom_id=f"mod_select_{str(uuid.uuid4())}"
        )
        self.target_user = user
        self.message = message
        self.mod_message = mod_message
        self.mod_channel_id = mod_channel_id
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        action = self.values[0]
        moderator = interaction.user
        mod_channel = interaction.client.get_channel(self.mod_channel_id)

        # Update embed
        embed = self.mod_message.embeds[0]
        embed.set_footer(
            text=f"{action.capitalize()} by {moderator.display_name}",
            icon_url=moderator.avatar.url if moderator.avatar else None
        )

        # Perform action
        try:
            if action == "warn":
                await self.target_user.send(f"You have been warned for inappropriate content in {self.message.guild.name}.")
            elif action == "kick":
                await self.target_user.send(f"You have been kicked from {self.message.guild.name} for inappropriate content.")
                await self.target_user.kick(reason="Inappropriate content")
            elif action == "ban":
                await self.target_user.send(f"You have been banned from {self.message.guild.name} for inappropriate content.")
                await self.target_user.ban(reason="Inappropriate content")
            elif action == "ignore":
                pass
        except discord.errors.Forbidden:
            await mod_channel.send(f"Error: Bot lacks permission to {action} {self.target_user.mention}")
        except discord.errors.HTTPException as e:
            await mod_channel.send(f"Error performing {action} on {self.target_user.mention}: {str(e)}")

        # Remove dropdown by clearing the view
        self.view.clear_items()
        await self.mod_message.edit(embed=embed, view=None)
        await interaction.response.defer()

async def setup(client, mod_channel_id):
    @client.event
    async def on_message(message):
        if message.author.bot:
            return

        # Check for sensitive words or links
        content = message.content.lower()
        has_sensitive_word = any(word in content for word in SENSITIVE_WORDS)
        has_link = re.search(LINK_PATTERN, content)

        if has_sensitive_word or has_link:
            # Delete the message
            try:
                await message.delete()
            except discord.errors.Forbidden:
                return

            # Create embed for mod channel
            embed = discord.Embed(
                title="Auto-Mod Alert",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="User", value=message.author.mention, inline=False)
            embed.add_field(name="Channel", value=message.channel.mention, inline=False)
            embed.add_field(name="Content", value=message.content, inline=False)
            embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else None)
            embed.set_footer(text="Choose an action below")

            # Create persistent view
            view = ModerationView(message.author, message, None, mod_channel_id)

            # Send to mod channel
            mod_channel = client.get_channel(mod_channel_id)
            if mod_channel:
                mod_message = await mod_channel.send(embed=embed, view=view)
                view.children[0].mod_message = mod_message  # Update select with message reference

        # Call existing on_message handlers
        for listener in client._listeners.get('on_message', []):
            if listener != on_message:  # Avoid recursive call
                await listener(message)