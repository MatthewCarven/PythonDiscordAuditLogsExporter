import discord
from discord import app_commands
from discord.ext import commands
import io

# Set up the bot and its intents
class AuditBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        # Replace the numbers below with your actual Server ID
        self.testing_server_id = 1392865518246957206 

    async def setup_hook(self):
        # Syncing to a specific server makes the command show up instantly
        testing_guild = discord.Object(id=self.testing_server_id)
        self.tree.copy_global_to(guild=testing_guild)
        await self.tree.sync(guild=testing_guild)

bot = AuditBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

# Create the /export command
@bot.tree.command(name="export", description="Export audit logs from this server, or a specific server by ID.")
@app_commands.describe(server_id="The ID of the server to export logs from (optional)", limit="Number of logs to fetch")
@app_commands.default_permissions(view_audit_log=True)
async def export_logs(interaction: discord.Interaction, server_id: str = None, limit: int = 100):
    
    # Defer the response to give the bot time to fetch the logs
    await interaction.response.defer(ephemeral=True)
    
    # Determine which server we are targeting
    if server_id:
        try:
            # We use interaction.client to get the bot instance and find the guild
            target_guild = interaction.client.get_guild(int(server_id))
        except ValueError:
            await interaction.followup.send("That doesn't look like a valid Server ID (it should be numbers only).")
            return
    else:
        target_guild = interaction.guild

    # Check if the bot is actually in the target server
    if target_guild is None:
        await interaction.followup.send("I couldn't find that server. Make sure I am invited to it!")
        return

    # Check if the bot has permission in the target server
    if not target_guild.me.guild_permissions.view_audit_log:
        await interaction.followup.send(f"I need the 'View Audit Log' permission in **{target_guild.name}** to do this!")
        return

    log_data = f"Audit Log Export for: {target_guild.name}\n"
    log_data += "=" * 40 + "\n\n"
    
    try:
        # Fetch the logs from the target_guild instead of interaction.guild
        async for entry in target_guild.audit_logs(limit=limit):
            timestamp = entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
            
            # Grabbing the action name, handling cases where target might be None
            action_name = entry.action.name if entry.action else "Unknown Action"
            target_name = entry.target if entry.target else "None/Unknown"
            
            log_data += f"[{timestamp}] User: {entry.user} | Action: {action_name} | Target: {target_name}\n"
            
        file_bytes = io.BytesIO(log_data.encode('utf-8'))
        discord_file = discord.File(fp=file_bytes, filename=f"audit_logs_{target_guild.id}.txt")
        
        await interaction.followup.send(f"Here are the last {limit} audit log entries for **{target_guild.name}**:", file=discord_file)
        
    except discord.Forbidden:
        await interaction.followup.send("Discord blocked the request. I might not have the right permissions or roles.")
    except Exception as e:
        await interaction.followup.send(f"An unexpected error occurred: {e}")







# Run the bot (Replace this with your actual token)
bot.run("")