import discord
from discord import app_commands
from discord.ext import commands
import io

class AuditBot(commands.Bot):
    def __init__(self):
        # Using all intents is often safer for complex audit log tasks
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        await self.tree.sync()

bot = AuditBot()

def get_perm_diff(before_perms, after_perms):
    """Compares two permission objects and returns a string of changes."""
    added = [name.replace('_', ' ').title() for name, value in after_perms if value and not getattr(before_perms, name)]
    removed = [name.replace('_', ' ').title() for name, value in before_perms if value and not getattr(before_perms, name)]
    
    diffs = []
    if added: diffs.append(f"+ Added: {', '.join(added)}")
    if removed: diffs.append(f"- Removed: {', '.join(removed)}")
    return " | ".join(diffs) if diffs else "No bitwise changes"

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

@bot.tree.command(name="export", description="Export audit logs with bitwise permission breakdown.")
@app_commands.describe(
    server_id="The ID of the server to export logs from (optional).", 
    limit="Number of logs to fetch (defaults to 100).",
    verbose="Set to True to include permission breakdowns and reasons."
)
@app_commands.default_permissions(view_audit_log=True)
async def export_logs(interaction: discord.Interaction, server_id: str = None, limit: int = 100, verbose: bool = False):
    
    await interaction.response.defer(ephemeral=True)
    
    # --- Server Resolution Logic ---
    if server_id:
        try:
            target_guild = interaction.client.get_guild(int(server_id))
        except ValueError:
            await interaction.followup.send("Invalid Server ID format.")
            return
    else:
        target_guild = interaction.guild

    if not target_guild:
        await interaction.followup.send("Server not found.")
        return

    # Permission check for the requesting user
    target_member = await target_guild.fetch_member(interaction.user.id)
    if not target_member or not target_member.guild_permissions.view_audit_log:
        await interaction.followup.send("Access Denied: Missing permissions in target server.")
        return

    log_data = f"{'Verbose ' if verbose else ''}Audit Log Export: {target_guild.name}\n"
    log_data += "=" * 60 + "\n\n"
    
    try:
        async for entry in target_guild.audit_logs(limit=limit):
            timestamp = entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
            action_name = entry.action.name
            target = entry.target if entry.target else "N/A"
            
            line = f"[{timestamp}] {entry.user} -> {action_name} (Target: {target})"
            
            if verbose:
                # Handle the specific "Permissions Updated" frustration
                if entry.action == discord.AuditLogAction.role_update and hasattr(entry.after, 'permissions'):
                    perm_detail = get_perm_diff(entry.before.permissions, entry.after.permissions)
                    line += f"\n    └─ PERMISSION CHANGES: {perm_detail}"
                
                # Standard verbose info
                if entry.reason:
                    line += f"\n    └─ Reason: {entry.reason}"
                if entry.extra:
                    line += f"\n    └─ Extra: {entry.extra}"
            
            log_data += line + "\n"
            
        # File Generation
        file_bytes = io.BytesIO(log_data.encode('utf-8'))
        filename = f"{'verbose_' if verbose else ''}logs_{target_guild.id}.txt"
        
        await interaction.followup.send(
            f"Exported {limit} entries for **{target_guild.name}**.", 
            file=discord.File(fp=file_bytes, filename=filename)
        )
        
    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to view audit logs there.")
    except Exception as e:
        await interaction.followup.send(f"Error: {e}")

bot.run("YOur token heree")