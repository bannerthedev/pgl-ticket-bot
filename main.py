# requirements: pip install -U discord.py
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = "MTUwMTc0NTMzNjI0OTQ4NzQxMQ.G6JXKe.haqCOmS7eyrCtxvMFX5mwXxb9WB5UW7M88c0fM"
GUILD_ID = 1501721254338494668  # Guild ID where command registers
STAFF_ROLE_IDS = [1501782548437663884]  # list of role IDs that can see/manage tickets

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
ticket_counter = 1

# Build the embed and buttons for the menu
def menu_embed():
    e = discord.Embed(title="PGL Manager", color=discord.Color.blurple())
    e.description = (
        "Open the ticket type that fits your issue best.\n"
        "Read the Terms of Service before opening any ticket.\n"
        "Before opening a ticket, read https://discord.com/channels/1501721254338494668/1501724072206405713.\n\n"
        "**Appeal**\nUse this for punishments, bans, or appeal reviews.\n\n"
        "**PGL Support**\nUse this for PGL support requests and reports.\n\n"
        "**Management**\nUse this for staff reports, leadership issues, or other serious management-only topics."
    )
    return e

class TicketMenuView(discord.ui.View):
    def __init__(self, category_id: int | None):
        super().__init__(timeout=None)
        self.category_id = category_id

    @discord.ui.button(label="PGL Support", style=discord.ButtonStyle.primary, custom_id="ticket_support")
    async def support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(interaction, "PGL Support", self.category_id)

    @discord.ui.button(label="Appeal", style=discord.ButtonStyle.danger, custom_id="ticket_appeal")
    async def appeal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(interaction, "Appeal", self.category_id)

    @discord.ui.button(label="Management", style=discord.ButtonStyle.secondary, custom_id="ticket_management")
    async def management(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(interaction, "Management", self.category_id)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        # permission check: admin or staff role or ticket owner (owner id stored in channel.topic)
        member = interaction.user
        if member.guild_permissions.administrator or any(r.id in STAFF_ROLE_IDS for r in member.roles):
            await interaction.response.send_message("Closing ticket...", ephemeral=True)
            await interaction.channel.delete(reason="Ticket closed")
            return

        topic = interaction.channel.topic or ""
        if topic.startswith("ticket_owner:"):
            owner_id = int(topic.split(":")[1].split("|")[0])
            if owner_id == interaction.user.id:
                await interaction.response.send_message("Closing ticket...", ephemeral=True)
                await interaction.channel.delete(reason="Ticket closed by owner")
                return

        await interaction.response.send_message("Only staff or the ticket owner can close this ticket.", ephemeral=True)

async def create_ticket_channel(interaction: discord.Interaction, type_label: str, category_id: int | None):
    global ticket_counter
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    # build channel name
    safe_name = ''.join(ch for ch in interaction.user.name.lower() if ch.isalnum())[:8]
    channel_name = f"ticket-{ticket_counter}-{safe_name}"
    ticket_counter += 1

    # overwrites: deny everyone, allow member and staff roles
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False)
    }
    overwrites[interaction.user] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    for rid in STAFF_ROLE_IDS:
        role = guild.get_role(rid)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    category = guild.get_channel(category_id) if category_id else None
    try:
        new_ch = await guild.create_text_channel(
            name=channel_name,
            topic=f"ticket_owner:{interaction.user.id} | type:{type_label}",
            overwrites=overwrites,
            category=category,
            reason=f"Ticket opened ({type_label}) by {interaction.user}"
        )

        embed = discord.Embed(title=f"{type_label} Ticket", description="Please state your issue and wait for a staff member to claim your ticket and help you with your ticket.", color=discord.Color.green())
        await new_ch.send(content=interaction.user.mention, embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"Ticket created: {new_ch.mention}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send("Failed to create ticket channel. Check bot permissions.", ephemeral=True)

# Slash command to post the ticket menu (admin-only)
@tree.command(name="create_ticket", description="Post the ticket menu in a channel", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(channel="Channel to post the ticket menu in", category="Optional category to place ticket channels under")
@app_commands.checks.has_permissions(administrator=True)
async def create_ticket(interaction: discord.Interaction, channel: discord.TextChannel, category: discord.CategoryChannel | None = None):
    view = TicketMenuView(category.id if category else None)
    try:
        await channel.send(embed=menu_embed(), view=view)
        await interaction.response.send_message(f"Ticket menu posted in {channel.mention}.", ephemeral=True)
    except Exception:
        await interaction.response.send_message("Failed to post menu. Check bot permissions.", ephemeral=True)

# Error handler for permission fails
@create_ticket.error
async def create_ticket_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You need Administrator permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred.", ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)
