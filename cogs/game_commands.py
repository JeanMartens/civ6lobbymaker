"""
Discord slash commands for game management
"""
import discord
from discord import app_commands
from discord.ext import commands
from core.game_manager import GameManager
from core.configs import CIV_EMOJI_CONFIG, GAME_OPTIONS
from utils.voting import format_vote_details


class GameCommands(commands.Cog):
    """Game management commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.manager = GameManager()

    @app_commands.command(name="create", description="Créer une partie Civilization VI")
    @app_commands.describe(
        max_bans="Nombre maximum de civilisations à bannir (0 à 10)",
        civ_pool_size="Taille du pool de civilisations disponibles"
    )
    async def create(self, interaction: discord.Interaction, max_bans: int = 2, civ_pool_size: int = 6):
        """Create a new game"""
        if max_bans < 0 or max_bans > 10:
            await interaction.response.send_message(
                "❌ Le nombre de bans doit être entre 0 et 10.", ephemeral=True
            )
            return
        
        if civ_pool_size < 1 or civ_pool_size > 10:
            await interaction.response.send_message(
                "❌ Le nombre de civilisations proposées doit être entre 1 et 10.", ephemeral=True
            )
            return
        
        # Create game first
        game = self.manager.create_game(interaction.user.id, max_bans, civ_pool_size, None)
        
        # Create initial message with view
        view = self.manager.create_join_view(game["id"])
        
        await interaction.response.send_message(
            content=(
                f"🎮 **Partie {game['id']} créée !**\n\n"
                f"**Bans par joueur**: {max_bans}\n"
                f"**Civilisations proposées par joueur**: {civ_pool_size}\n\n"
                f"Les joueurs peuvent rejoindre en cliquant sur le bouton ci-dessous.\n"
                f"Une fois que tout le monde est prêt, clique sur 'Commencer les votes'."
            ),
            view=view
        )
        
        # Get message and create thread
        initial_msg = await interaction.original_response()
        
        try:
            thread = await initial_msg.create_thread(
                name=f"Partie {game['id']} - {interaction.user.name}",
                auto_archive_duration=1440
            )
            
            # Update game with thread_id
            game["thread_id"] = thread.id
            self.manager.save()
            
            # Edit message to include thread
            await initial_msg.edit(
                content=(
                    f"🎮 **Partie {game['id']} créée !**\n\n"
                    f"**Bans par joueur**: {max_bans}\n"
                    f"**Civilisations proposées par joueur**: {civ_pool_size}\n\n"
                    f"Les joueurs peuvent rejoindre en cliquant sur le bouton ci-dessous.\n"
                    f"Une fois que tout le monde est prêt, clique sur 'Commencer les votes'.\n\n"
                    f"📝 Toutes les discussions se feront dans {thread.mention}"
                ),
                view=view
            )
            
            # Welcome message in thread
            await thread.send(
                f"🎉 Bienvenue dans la partie {game['id']} !\n\n"
                f"Créateur: {interaction.user.mention}\n"
                f"**Bans par joueur**: {max_bans}\n"
                f"**Civilisations proposées**: {civ_pool_size}\n\n"
                f"Les joueurs peuvent rejoindre en cliquant sur le bouton dans le message ci-dessus."
            )
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la création du thread: {e}")

    @app_commands.command(name="progress", description="Voir la progression des votes, bans et sélections")
    async def progress(self, interaction: discord.Interaction, game_id: str):
        """Show game progress"""
        game = self.manager.get_game(game_id)
        
        if not game:
            await interaction.response.send_message("❌ Partie introuvable !", ephemeral=True)
            return
        
        msg = f"## 📊 Progression - Partie {game_id}\n\n"
        
        # Voting progress
        if game.get("voting_started"):
            msg += "### 🗳️ Votes\n"
            completed = 0
            for player_id in game["players"]:
                user = await self.bot.fetch_user(player_id)
                votes = game.get("votes", {}).get(str(player_id), {})
                status = "✅" if len(votes) == len(GAME_OPTIONS) else "⏳"
                msg += f"{status} **{user.name}**: {len(votes)}/{len(GAME_OPTIONS)} catégories\n"
                if len(votes) == len(GAME_OPTIONS):
                    completed += 1
            msg += f"\n**Total**: {completed}/{len(game['players'])} joueurs\n\n"
        
        # Ban progress
        if game.get("banning_started"):
            msg += "### 🚫 Bans\n"
            completed = 0
            for player_id in game["players"]:
                user = await self.bot.fetch_user(player_id)
                bans = game.get("bans", {}).get(str(player_id), [])
                status = "✅" if str(player_id) in game.get("bans", {}) else "⏳"
                msg += f"{status} **{user.name}**: {len(bans)}/{game.get('max_bans', 2)} ban(s)\n"
                if str(player_id) in game.get("bans", {}):
                    completed += 1
            msg += f"\n**Total**: {completed}/{len(game['players'])} joueurs\n\n"
        
        # Selection progress
        if game.get("selection_started"):
            msg += "### 🎯 Sélection des civilisations\n"
            completed = 0
            for player_id in game["players"]:
                user = await self.bot.fetch_user(player_id)
                civ = game.get("civ_selections", {}).get(str(player_id))
                status = "✅" if civ else "⏳"
                if civ:
                    emoji = CIV_EMOJI_CONFIG.get(civ, "")
                    msg += f"{status} **{user.name}**: {emoji} {civ}\n"
                    completed += 1
                else:
                    msg += f"{status} **{user.name}**: En attente...\n"
            msg += f"\n**Total**: {completed}/{len(game['players'])} joueurs\n"
        
        if not game.get("voting_started"):
            msg += "Les votes n'ont pas encore commencé."
        
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="votes_details", description="Voir les détails complets des votes")
    async def votes_details(self, interaction: discord.Interaction, game_id: str):
        """Show detailed voting results"""
        game = self.manager.get_game(game_id)
        
        if not game:
            await interaction.response.send_message("❌ Partie introuvable !", ephemeral=True)
            return
        
        if not game.get("votes"):
            await interaction.response.send_message("❌ Aucun vote enregistré !", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        weighted_results = game.get("final_settings", {})
        
        # Send details for each category
        for category in GAME_OPTIONS.keys():
            if category not in weighted_results:
                continue
            
            msg = format_vote_details(category, weighted_results[category], len(game["votes"]))
            await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="results", description="Afficher les résultats des votes et bans")
    async def results(self, interaction: discord.Interaction, game_id: str):
        """Display final results"""
        game = self.manager.get_game(game_id)
        
        if not game:
            await interaction.response.send_message("❌ Partie introuvable !", ephemeral=True)
            return
        
        if interaction.user.id != game["creator"]:
            await interaction.response.send_message("❌ Seul le créateur peut afficher les résultats !", ephemeral=True)
            return
        
        if not game.get("voting_started"):
            await interaction.response.send_message("❌ Les votes n'ont pas encore commencé !", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        channel_id = game.get("thread_id") or interaction.channel_id
        try:
            channel = await self.bot.fetch_channel(channel_id)
            await self.manager._send_final_results(channel, game_id)
            await interaction.followup.send("✅ Les résultats ont été publiés dans le thread.")
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur: {e}")

    @app_commands.command(name="delete", description="Supprimer une partie existante")
    async def delete(self, interaction: discord.Interaction, game_id: str):
        """Delete a game"""
        game = self.manager.get_game(game_id)
        
        if not game:
            await interaction.response.send_message("❌ Partie introuvable !", ephemeral=True)
            return
        
        if interaction.user.id != game["creator"]:
            await interaction.response.send_message("❌ Seul le créateur peut supprimer la partie !", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Notify in thread
        thread_id = game.get("thread_id")
        if thread_id:
            try:
                thread = await self.bot.fetch_channel(thread_id)
                
                player_mentions = [f"<@{pid}>" for pid in game.get("players", [])]
                
                if player_mentions:
                    await thread.send(
                        f"🗑️ **Cette partie a été supprimée par le créateur.**\n\n"
                        f"Joueurs concernés: {', '.join(player_mentions)}\n\n"
                        f"Ce thread va être archivé."
                    )
                else:
                    await thread.send(
                        f"🗑️ **Cette partie a été supprimée par le créateur.**\n\n"
                        f"Ce thread va être archivé."
                    )
                
                # Archive thread
                await thread.edit(archived=True, locked=True)
                
            except Exception as e:
                print(f"⚠️ Erreur lors de la fermeture du thread: {e}")
        
        # Delete game
        self.manager.storage.delete(game_id)
        self.manager.save()
        
        await interaction.followup.send(
            f"🗑️ Partie {game_id} supprimée avec succès.",
            ephemeral=True
        )

    @app_commands.command(name="show_civs", description="Afficher toutes les civilisations avec leurs emojis")
    async def show_civs(self, interaction: discord.Interaction, page: int = 1):
        """Show civilizations list"""
        civs_per_page = 25
        total_civs = len(CIV_EMOJI_CONFIG)
        total_pages = (total_civs + civs_per_page - 1) // civs_per_page
        
        if page < 1 or page > total_pages:
            await interaction.response.send_message(
                f"❌ Page invalide. Utilise 1-{total_pages}.",
                ephemeral=True
            )
            return
        
        start_idx = (page - 1) * civs_per_page
        end_idx = min(start_idx + civs_per_page, total_civs)
        
        civs_list = list(CIV_EMOJI_CONFIG.items())
        page_civs = civs_list[start_idx:end_idx]
        
        msg = f"## 🗺️ Civilisations (Page {page}/{total_pages})\n\n"
        for civ, emoji in page_civs:
            msg += f"{emoji} **{civ}**\n"
        
        if page < total_pages:
            msg += f"\n*Utilise `/show_civs page:{page+1}` pour la suite*"
        
        await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot):
    await bot.add_cog(GameCommands(bot))
