"""
Discord UI views for game creation and joining
"""
import discord
from views.voting_views import VoteView


class GameJoinView(discord.ui.View):
    """View with join and start buttons for a game"""
    
    def __init__(self, game_manager, game_id):
        super().__init__(timeout=None)
        self.game_manager = game_manager
        self.game_id = game_id
        
        join_button = discord.ui.Button(
            label="Rejoindre la partie", 
            style=discord.ButtonStyle.green
        )
        start_button = discord.ui.Button(
            label="Commencer les votes", 
            style=discord.ButtonStyle.primary
        )
        
        join_button.callback = self.join_callback
        start_button.callback = self.start_callback
        
        self.add_item(join_button)
        self.add_item(start_button)
    
    async def join_callback(self, interaction: discord.Interaction):
        """Handle player joining the game"""
        game = self.game_manager.get_game(self.game_id)
        
        if game["voting_started"]:
            await interaction.response.send_message(
                "Les votes ont déjà commencé !", 
                ephemeral=True
            )
            return

        if interaction.user.id not in game["players"]:
            game["players"].append(interaction.user.id)
            self.game_manager.save()
            
            # Send join message to thread
            thread_id = game.get("thread_id")
            if thread_id:
                try:
                    thread = await interaction.client.fetch_channel(thread_id)
                    await thread.send(f"{interaction.user.mention} a rejoint la partie !")
                    await interaction.response.send_message(
                        f"Tu as rejoint la partie ! Suis la conversation dans le thread.", 
                        ephemeral=True
                    )
                except:
                    await interaction.response.send_message(
                        f"{interaction.user.mention} a rejoint la partie !", 
                        ephemeral=False
                    )
            else:
                await interaction.response.send_message(
                    f"{interaction.user.mention} a rejoint la partie !", 
                    ephemeral=False
                )
        else:
            await interaction.response.send_message(
                "Tu es déjà dans la partie.", 
                ephemeral=True
            )
    
    async def start_callback(self, interaction: discord.Interaction):
        """Handle starting the voting phase"""
        game = self.game_manager.get_game(self.game_id)
        
        if interaction.user.id != game["creator"]:
            await interaction.response.send_message(
                "Seul le créateur peut commencer les votes !", 
                ephemeral=True
            )
            return

        if len(game["players"]) == 0:
            await interaction.response.send_message(
                "Aucun joueur n'a rejoint la partie !", 
                ephemeral=True
            )
            return

        game["voting_started"] = True
        game["results_channel_id"] = game.get("thread_id") or interaction.channel_id
        self.game_manager.save()

        # Disable buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        # Send start message to thread
        thread_id = game.get("thread_id")
        if thread_id:
            try:
                thread = await interaction.client.fetch_channel(thread_id)
                await interaction.response.send_message(
                    "Les votes démarrent...", 
                    ephemeral=True
                )
                await thread.send(
                    "🗳️ Les votes ont commencé ! Chaque joueur va recevoir un message privé."
                )
            except:
                await interaction.response.send_message(
                    "🗳️ Les votes ont commencé ! Chaque joueur va recevoir un message privé."
                )
        else:
            await interaction.response.send_message(
                "🗳️ Les votes ont commencé ! Chaque joueur va recevoir un message privé."
            )

        # Send voting DMs to players
        failed_users = []
        for player_id in game["players"]:
            try:
                user = await interaction.client.fetch_user(player_id)
                vote_view = VoteView(self.game_manager, self.game_id, player_id)
                await user.send(
                    f"🎮 **Votes pour la partie {self.game_id} - Page 1/3**\n\n"
                    f"Sélectionne toutes tes options ci-dessous, puis clique sur 'Page suivante' pour continuer.",
                    view=vote_view,
                )
                print(f"✅ Message envoyé à {user.name} ({player_id})")
            except discord.Forbidden:
                failed_users.append(f"<@{player_id}>")
                print(f"❌ {player_id} a bloqué les MPs du bot")
            except Exception as e:
                failed_users.append(f"<@{player_id}>")
                print(f"❌ Erreur lors de l'envoi du message à {player_id}: {e}")
        
        if failed_users:
            target_channel = thread if thread_id else interaction.channel
            await target_channel.send(
                f"⚠️ Impossible d'envoyer les MPs à : {', '.join(failed_users)}\n"
                f"Ils doivent activer les MPs depuis les membres du serveur dans leurs paramètres de confidentialité."
            )
