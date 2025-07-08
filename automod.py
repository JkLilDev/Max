import discord
from discord.ext import commands
from discord import SelectOption
import re

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

class ModerationSelect(discord.ui.Select):
    def __init__(self, user, message, mod_message, mod_channel_id):
        options = [
            SelectOption(label="Warn", value="warn", description="Send a warning DM"),
            SelectOption(label="Kick", value="kick", description="Kick user from server"),
            SelectOption(label="Ban", value="ban", description="Ban user from server"),
            SelectOption(label="Ignore", value="ignore", description="Take no action")
        ]
        super().__init__(placeholder="Select an action", options=options)
        self.target_user = user
        self.message = message
        self.mod_message = mod_message
        self.mod_channel_id = mod_channel_id

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
                # Check if the user is still in the guild before sending DM
                if self.target_user.guild: # This ensures it's a member, not just a user object
                    await self.target_user.send(f"You have been warned for inappropriate content in {self.message.guild.name}.")
                else:
                    await mod_channel.send(f"Could not warn {self.target_user.mention}: User not found in guild.")
            elif action == "kick":
                if isinstance(self.target_user, discord.Member): # Ensure it's a Member object
                    await self.target_user.send(f"You have been kicked from {self.message.guild.name} for inappropriate content.")
                    await self.target_user.kick(reason="Inappropriate content")
                else:
                    await mod_channel.send(f"Could not kick {self.target_user.mention}: User is not a guild member.")
            elif action == "ban":
                if isinstance(self.target_user, discord.Member): # Ensure it's a Member object
                    await self.target_user.send(f"You have been banned from {self.message.guild.name} for inappropriate content.")
                    await self.target_user.ban(reason="Inappropriate content")
                else:
                    await mod_channel.send(f"Could not ban {self.target_user.mention}: User is not a guild member.")
            elif action == "ignore":
                pass
        except discord.errors.Forbidden:
            await mod_channel.send(f"Error: Bot lacks permission to {action} {self.target_user.mention} in this guild.")
        except discord.errors.HTTPException as e:
            await mod_channel.send(f"Error performing {action} on {self.target_user.mention}: {str(e)}")

        # Remove dropdown
        await self.mod_message.edit(embed=embed, view=None)
        await interaction.response.defer()

# This function will be called from bot.py
async def handle_automod_message(client, message, mod_channel_id):
    if message.author.bot:
        return False # Indicate that automod didn't handle the message fully

    # Check for sensitive words or links
    content = message.content.lower()
    has_sensitive_word = any(word in content for word in SENSITIVE_WORDS)
    has_link = re.search(LINK_PATTERN, content)

    if has_sensitive_word or has_link:
        # Delete the message
        try:
            await message.delete()
        except discord.errors.Forbidden:
            print(f"Warning: Bot does not have permissions to delete messages in {message.channel.name}")
            return True # Indicate automod handled the message (or tried to)

        # Create embed for mod channel
        embed = discord.Embed(
            title="Auto-Mod Alert",
            description="The following message was flagged and deleted:",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="User", value=message.author.mention, inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        embed.add_field(name="Content", value=f"```\n{message.content}\n```", inline=False)
        embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else None)
        embed.set_footer(text="Choose an action below")

        # Create dropdown view
        view = discord.ui.View(timeout=180) # Timeout for the dropdown
        select = ModerationSelect(message.author, message, None, mod_channel_id)
        view.add_item(select)

        # Send to mod channel
        mod_channel = client.get_channel(mod_channel_id)
        if mod_channel:
            mod_message = await mod_channel.send(embed=embed, view=view)
            select.mod_message = mod_message
        else:
            print(f"Warning: Moderation channel with ID {mod_channel_id} not found.")

        return True # Indicate that automod handled this message
    return False # Indicate that automod did not handle this message
