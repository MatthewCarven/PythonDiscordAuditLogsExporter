import discord
from discord import app_commands
from discord.ext import commands
import io

# Set up the bot and its intents
class AuditBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        # Syncing without a guild parameter makes the commands Global
        await self.tree.sync()

bot = AuditBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

# Create the /export command
@bot.tree.command(name="export", description="Export audit logs from this server, or a specific server by ID.")
@app_commands.describe(
    server_id="The ID of the server to export logs from (optional).", 
    limit="Number of logs to fetch (defaults to 100).",
    verbose="Set to True to include reasons and extra context (defaults to False)."
)
@app_commands.default_permissions(view_audit_log=True)
async def export_logs(interaction: discord.Interaction, server_id: str = None, limit: int = 100, verbose: bool = False):
    
    await interaction.response.defer(ephemeral=True)
    
    # Determine the target server
    if server_id:
        try:
            target_guild = interaction.client.get_guild(int(server_id))
        except ValueError:
            await interaction.followup.send("That doesn't look like a valid Server ID.")
            return

        if target_guild:
            try:
                target_member = await target_guild.fetch_member(interaction.user.id)
            except discord.NotFound:
                await interaction.followup.send("Access Denied: You must be a member of that server to export its logs.")
                return
            except discord.HTTPException:
                await interaction.followup.send("An error occurred while verifying your permissions.")
                return
                
            if not target_member.guild_permissions.view_audit_log:
                await interaction.followup.send(f"Access Denied: You lack the 'View Audit Log' permission in **{target_guild.name}**.")
                return
    else:
        target_guild = interaction.guild

    if target_guild is None:
        await interaction.followup.send("I couldn't find that server. Make sure I am invited to it!")
        return

    # Set up the header based on verbosity
    mode_text = "Verbose " if verbose else ""
    log_data = f"{mode_text}Audit Log Export for: {target_guild.name}\n"
    log_data += "=" * 50 + "\n\n"
    
    try:
        async for entry in target_guild.audit_logs(limit=limit):
            timestamp = entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
            action_name = entry.action.name if entry.action else "Unknown Action"
            target_name = entry.target if entry.target else "None/Unknown"
            
            # Base logging format
            line = f"[{timestamp}] User: {entry.user} | Action: {action_name} | Target: {target_name}"
            
            # If the user toggled verbose to True, append the extra details
            if verbose:
                if entry.reason:
                    line += f" | Reason: {entry.reason}"
                if entry.extra:
                    line += f" | Extra Info: {entry.extra}"
            
            log_data += line + "\n"
            
        file_bytes = io.BytesIO(log_data.encode('utf-8'))
        
        # Adjust the filename so you know which type of log it is
        filename_prefix = "verbose_audit_logs" if verbose else "audit_logs"
        discord_file = discord.File(fp=file_bytes, filename=f"{filename_prefix}_{target_guild.id}.txt")
        
        await interaction.followup.send(f"Here are the last {limit} {mode_text.lower()}audit log entries for **{target_guild.name}**:", file=discord_file)
        
    except discord.Forbidden:
        await interaction.followup.send("Discord blocked the request. I might not have the right permissions or roles.")
    except Exception as e:
        await interaction.followup.send(f"An unexpected error occurred: {e}")







# Run the bot (Replace this with your actual token)
bot.run("YOu bot token goes here")