import discord
from discord import app_commands
from discord.ext import commands
from core.game_manager import GameManager
from core.configs import CIV_EMOJI_CONFIG, GAME_OPTIONS

class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.manager = GameManager()

    @app_commands.command(name="create", description="Créer une partie Civilization VI")
    @app_commands.describe(
        max_bans="Nombre maximum de civilisations à bannir (0 à 10)",
        civ_pool_size="Taille du pool de civilisations disponibles"
    )
    async def create(self, interaction: discord.Interaction, max_bans: int = 2, civ_pool_size: int = 6):
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
        
        game = self.manager.create_game(interaction.user.id, max_bans, civ_pool_size)
        view = self.manager.create_join_view(game["id"])
        await interaction.response.send_message(
            f"🎮 **Partie {game['id']} créée !**\n\n"
            f"**Bans par joueur**: {max_bans}\n"
            f"**Civilisations proposées par joueur**: {civ_pool_size}\n\n"
            f"Les joueurs peuvent rejoindre en cliquant sur le bouton ci-dessous.\n"
            f"Une fois que tout le monde est prêt, clique sur 'Commencer les votes'.",
            view=view
        )

    @app_commands.command(name="progress", description="Voir la progression des votes, bans et sélections")
    async def progress(self, interaction: discord.Interaction, game_id: str):
        game = self.manager.storage.get_by_id(game_id)
        
        if not game:
            await interaction.response.send_message(
                "❌ Partie introuvable !", ephemeral=True
            )
            return
        
        msg = f"## 📊 Progression - Partie {game_id}\n\n"
        
        # Voting progress
        if game.get("voting_started"):
            progress = self.manager.get_voting_progress(game_id)
            
            if progress:
                msg += "### 🗳️ Votes\n"
                completed_count = 0
                for player_id, data in progress.items():
                    user = await self.bot.fetch_user(player_id)
                    status = "✅" if data["completed"] else "⏳"
                    msg += f"{status} **{user.name}**: {data['voted_categories']}/{data['total_categories']} catégories\n"
                    if data["completed"]:
                        completed_count += 1
                
                msg += f"\n**Total votes**: {completed_count}/{len(progress)} joueurs\n\n"
        
        # Ban progress
        if game.get("banning_started"):
            ban_progress = self.manager.get_ban_progress(game_id)
            
            if ban_progress:
                msg += "### 🚫 Bans\n"
                completed_count = 0
                for player_id, data in ban_progress.items():
                    user = await self.bot.fetch_user(player_id)
                    status = "✅" if data["completed"] else "⏳"
                    msg += f"{status} **{user.name}**: {data['bans_count']}/{data['max_bans']} ban(s)\n"
                    if data["completed"]:
                        completed_count += 1
                
                msg += f"\n**Total bans**: {completed_count}/{len(ban_progress)} joueurs\n\n"
        
        # Selection progress
        if game.get("selection_started"):
            selection_progress = self.manager.get_selection_progress(game_id)
            
            if selection_progress:
                msg += "### 🎯 Sélection des civilisations\n"
                completed_count = 0
                for player_id, data in selection_progress.items():
                    user = await self.bot.fetch_user(player_id)
                    status = "✅" if data["completed"] else "⏳"
                    if data["completed"] and data["selection"]:
                        emoji = CIV_EMOJI_CONFIG.get(data["selection"], "")
                        msg += f"{status} **{user.name}**: {emoji} {data['selection']}\n"
                    else:
                        msg += f"{status} **{user.name}**: En attente...\n"
                    if data["completed"]:
                        completed_count += 1
                
                msg += f"\n**Total sélections**: {completed_count}/{len(selection_progress)} joueurs\n"
        
        if not game.get("voting_started"):
            msg += "Les votes n'ont pas encore commencé."
        
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="votes_details", description="Voir les détails complets des votes")
    async def votes_details(self, interaction: discord.Interaction, game_id: str):
        game = self.manager.storage.get_by_id(game_id)
        
        if not game:
            await interaction.response.send_message(
                "❌ Partie introuvable !", ephemeral=True
            )
            return
        
        if not game.get("votes"):
            await interaction.response.send_message(
                "❌ Aucun vote enregistré pour cette partie !", ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Get weighted results
        weighted_results = self.manager.calculate_weighted_results(game_id)
        
        # Build detailed message for each category
        for category in GAME_OPTIONS.keys():
            if category not in weighted_results:
                continue
                
            result_data = weighted_results[category]
            selected = result_data["selected"]
            votes_count = result_data["votes"]
            
            msg = f"## {category}\n"
            msg += f"**✅ Sélectionné**: {selected}\n\n"
            msg += f"**Détail des votes**:\n"
            
            # Sort by vote count (descending)
            sorted_votes = sorted(votes_count.items(), key=lambda x: x[1], reverse=True)
            for option, count in sorted_votes:
                percentage = (count / len(game["votes"])) * 100
                is_winner = "🏆" if option == selected else "  "
                msg += f"{is_winner} **{option}**: {count} vote(s) ({percentage:.0f}%)\n"
            
            msg += "\n"
            
            await interaction.followup.send(msg, ephemeral=True)
        
        # Send individual player votes summary
        player_msg = "## 👥 Votes par joueur\n\n"
        for player_id, votes in game["votes"].items():
            try:
                user = await self.bot.fetch_user(int(player_id))
                player_msg += f"**{user.name}**:\n"
                
                # Show all votes in compact format
                for i, (category, choice) in enumerate(votes.items()):
                    player_msg += f"  • {category}: {choice}\n"
                    
                    # Split into multiple messages if too long
                    if len(player_msg) > 1800:
                        await interaction.followup.send(player_msg, ephemeral=True)
                        player_msg = f"**{user.name}** (suite):\n"
                
                player_msg += "\n"
                
            except Exception as e:
                player_msg += f"**Joueur {player_id}**: {len(votes)} votes\n\n"
        
        if player_msg.strip() != "## 👥 Votes par joueur":
            await interaction.followup.send(player_msg, ephemeral=True)

    @app_commands.command(name="results", description="Afficher les résultats des votes et bans")
    async def results(self, interaction: discord.Interaction, game_id: str):
        game = self.manager.storage.get_by_id(game_id)
        
        if not game:
            await interaction.response.send_message(
                "❌ Partie introuvable !", ephemeral=True
            )
            return
        
        if interaction.user.id != game["creator"]:
            await interaction.response.send_message(
                "❌ Seul le créateur peut afficher les résultats !", ephemeral=True
            )
            return
        
        if not game.get("voting_started"):
            await interaction.response.send_message(
                "❌ Les votes n'ont pas encore commencé !", ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        thread = await self.manager.create_final_results_thread(
            interaction.channel, game_id
        )
        
        if thread:
            await interaction.followup.send(
                f"✅ Les résultats ont été publiés dans {thread.mention}"
            )
        else:
            await interaction.followup.send(
                "❌ Erreur lors de la création du thread de résultats."
            )

    @app_commands.command(name="force_bans", description="[Admin] Forcer le début de la phase de bans")
    @app_commands.default_permissions(administrator=True)
    async def force_bans(self, interaction: discord.Interaction, game_id: str):
        game = self.manager.storage.get_by_id(game_id)
        
        if not game:
            await interaction.response.send_message(
                "❌ Partie introuvable !", ephemeral=True
            )
            return
        
        if game.get("banning_started"):
            await interaction.response.send_message(
                "❌ La phase de bans a déjà commencé !", ephemeral=True
            )
            return
        
        # Mark as banning started
        game["banning_started"] = True
        game["results_channel_id"] = interaction.channel_id
        self.manager.storage.save()
        
        await interaction.response.send_message(
            f"🚫 Phase de bans forcée pour la partie {game_id} !"
        )
        
        # Calculate results
        weighted_results = self.manager.calculate_weighted_results(game_id)
        
        results_msg = "## 🎲 Paramètres sélectionnés pour la partie\n\n"
        for category, result_data in weighted_results.items():
            results_msg += f"**{category}**: {result_data['selected']}\n"
        
        await interaction.channel.send(results_msg)
        
        # Send ban interface to players
        failed_users = []
        for player_id in game["players"]:
            try:
                user = await self.bot.fetch_user(player_id)
                await self.manager.send_ban_interface(
                    user, game_id, player_id, 
                    game.get("max_bans", 2), 
                    weighted_results
                )
            except Exception as e:
                failed_users.append(f"<@{player_id}>")
                print(f"❌ Erreur lors de l'envoi du ban à {player_id}: {e}")
        
        if failed_users:
            await interaction.channel.send(
                f"⚠️ Impossible d'envoyer la phase de ban à: {', '.join(failed_users)}"
            )

    @app_commands.command(name="force_selection", description="[Admin] Forcer le début de la phase de sélection")
    @app_commands.default_permissions(administrator=True)
    async def force_selection(self, interaction: discord.Interaction, game_id: str):
        game = self.manager.storage.get_by_id(game_id)
        
        if not game:
            await interaction.response.send_message(
                "❌ Partie introuvable !", ephemeral=True
            )
            return
        
        if game.get("selection_started"):
            await interaction.response.send_message(
                "❌ La phase de sélection a déjà commencé !", ephemeral=True
            )
            return
        
        # Mark as selection started
        game["selection_started"] = True
        self.manager.storage.save()
        
        await interaction.response.send_message(
            f"🎯 Phase de sélection forcée pour la partie {game_id} !"
        )
        
        # Assign civilization pools
        if not self.manager.assign_civ_pools(game_id):
            await interaction.channel.send(
                "❌ Erreur: Pas assez de civilisations disponibles pour tous les joueurs!"
            )
            return
        
        # Send selection interface to players
        failed_users = []
        for player_id in game["players"]:
            try:
                await self.manager.send_civ_selection_interface(
                    self.bot, game_id, player_id
                )
            except Exception as e:
                failed_users.append(f"<@{player_id}>")
                print(f"❌ Erreur lors de l'envoi de la sélection à {player_id}: {e}")
        
        if failed_users:
            await interaction.channel.send(
                f"⚠️ Impossible d'envoyer la phase de sélection à: {', '.join(failed_users)}"
            )

    @app_commands.command(name="show_civs", description="Afficher toutes les civilisations avec leurs emojis")
    async def show_civs(self, interaction: discord.Interaction, page: int = 1):
        """Show civilizations with their emojis in pages"""
        
        # Calculate pagination
        civs_per_page = 25
        total_civs = len(CIV_EMOJI_CONFIG)
        total_pages = (total_civs + civs_per_page - 1) // civs_per_page
        
        # Validate page number
        if page < 1 or page > total_pages:
            await interaction.response.send_message(
                f"❌ Page invalide. Utilise un nombre entre 1 et {total_pages}.",
                ephemeral=True
            )
            return
        
        # Get civs for this page
        start_idx = (page - 1) * civs_per_page
        end_idx = min(start_idx + civs_per_page, total_civs)
        
        civs_list = list(CIV_EMOJI_CONFIG.items())
        page_civs = civs_list[start_idx:end_idx]
        
        # Build message
        msg = f"## 🗺️ Civilisations (Page {page}/{total_pages})\n\n"
        for civ, emoji in page_civs:
            msg += f"{emoji} **{civ}**\n"
        
        if page < total_pages:
            msg += f"\n*Utilise `/show_civs page:{page+1}` pour voir la page suivante*"
        
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="test_ban", description="[Test] Tester l'interface de ban")
    @app_commands.default_permissions(administrator=True)
    async def test_ban(self, interaction: discord.Interaction):
        """Test command to see the ban interface"""
        
        # Create a fake game for testing
        test_results = {
            "Carte": {"selected": "Continents"},
            "Climat": {"selected": "Classique"},
            "Camps de Barbares": {"selected": "Standard"}
        }
        
        await interaction.response.send_message(
            "📧 Test envoyé en MP ! Vérifie tes messages privés.",
            ephemeral=True
        )
        
        try:
            await self.manager.send_ban_interface(
                interaction.user, 
                "TEST-ID", 
                interaction.user.id, 
                3,  # max bans
                test_results
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erreur lors de l'envoi: {e}",
                ephemeral=True
            )

    @app_commands.command(name="test_selection", description="[Test] Tester l'interface de sélection")
    @app_commands.default_permissions(administrator=True)
    async def test_selection(self, interaction: discord.Interaction):
        """Test command to see the civilization selection interface"""
        
        # Create a fake game for testing
        game_id = "TEST-SEL"
        test_game = {
            "id": game_id,
            "creator": interaction.user.id,
            "players": [interaction.user.id],
            "civ_pool_size": 3,
            "civ_pools": {
                str(interaction.user.id): ["Lincoln (Abraham)", "Alexandre", "Chaka"]
            }
        }
        
        # Temporarily add to storage
        self.manager.storage.data[game_id] = test_game
        self.manager.storage.save()
        
        await interaction.response.send_message(
            "📧 Test envoyé en MP ! Vérifie tes messages privés.",
            ephemeral=True
        )
        
        try:
            await self.manager.send_civ_selection_interface(
                self.bot,
                game_id,
                interaction.user.id
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erreur lors de l'envoi: {e}",
                ephemeral=True
            )

    @app_commands.command(name="check_duplicates", description="Voir les emojis utilisés par plusieurs civilisations")
    async def check_duplicates(self, interaction: discord.Interaction):
        """Show which emojis are used by multiple civilizations"""
        
        # Find duplicates
        emoji_count = {}
        for civ, emoji in CIV_EMOJI_CONFIG.items():
            if emoji not in emoji_count:
                emoji_count[emoji] = []
            emoji_count[emoji].append(civ)
        
        duplicates = {emoji: civs for emoji, civs in emoji_count.items() if len(civs) > 1}
        
        if not duplicates:
            await interaction.response.send_message(
                "✅ Aucun emoji dupliqué ! Chaque civilisation a un emoji unique.",
                ephemeral=True
            )
            return
        
        msg = "## ⚠️ Emojis utilisés par plusieurs civilisations\n\n"
        msg += "*Ces emojis banniront toutes les civilisations associées:*\n\n"
        
        for emoji, civs in duplicates.items():
            msg += f"{emoji} est utilisé par:\n"
            for civ in civs:
                msg += f"  • {civ}\n"
            msg += "\n"
        
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="delete", description="Supprimer une partie existante")
    async def delete(self, interaction: discord.Interaction, game_id: str):
        game = self.manager.storage.get_by_id(game_id)
        if not game:
            await interaction.response.send_message("❌ Partie introuvable !", ephemeral=True)
            return
        if interaction.user.id != game["creator"]:
            await interaction.response.send_message("❌ Seul le créateur peut supprimer la partie !", ephemeral=True)
            return
        self.manager.storage.delete(game_id)
        self.manager.storage.save()
        await interaction.response.send_message(f"🗑️ Partie {game_id} supprimée avec succès.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(GameCommands(bot))