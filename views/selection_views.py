"""
Discord UI views for civilization selection phase
"""
import discord
from core.configs import CIV_EMOJI_CONFIG
from utils.civilization import parse_emoji_from_text


class CivSelectionView(discord.ui.View):
    """View for civilization selection"""
    
    def __init__(self, game_manager, game_id, user_id, available_civs):
        super().__init__(timeout=600)  # 10 minute timeout
        self.game_manager = game_manager
        self.game_id = game_id
        self.user_id = user_id
        self.available_civs = available_civs
        self.selected_civ = None
        
    @discord.ui.button(label="📝 Choisir ma civilisation", style=discord.ButtonStyle.primary, row=0)
    async def select_civ(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ton interface de sélection!", 
                ephemeral=True
            )
            return
        
        modal = CivSelectionModal(self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="👀 Voir ma sélection", style=discord.ButtonStyle.secondary, row=0)
    async def view_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ton interface de sélection!", 
                ephemeral=True
            )
            return
        
        if not self.selected_civ:
            await interaction.response.send_message(
                "Tu n'as pas encore sélectionné de civilisation.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"**Ta sélection actuelle:**\n{CIV_EMOJI_CONFIG[self.selected_civ]} {self.selected_civ}",
                ephemeral=True
            )
    
    @discord.ui.button(label="✅ Confirmer mon choix", style=discord.ButtonStyle.success, row=1)
    async def confirm_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ton interface de sélection!", 
                ephemeral=True
            )
            return
        
        if not self.selected_civ:
            await interaction.response.send_message(
                "❌ Tu dois d'abord choisir une civilisation!",
                ephemeral=True
            )
            return
        
        # Save selection
        game = self.game_manager.get_game(self.game_id)
        if "civ_selections" not in game:
            game["civ_selections"] = {}
        
        game["civ_selections"][str(self.user_id)] = self.selected_civ
        self.game_manager.save()
        
        # Send confirmation
        await interaction.response.send_message(
            f"✅ **Tu as choisi:**\n{CIV_EMOJI_CONFIG[self.selected_civ]} {self.selected_civ}\n\n"
            f"Ton choix a été enregistré!",
            ephemeral=True
        )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        # Check if all players have finished selecting
        await self.game_manager.check_selections_complete(interaction.client, self.game_id)
    
    @discord.ui.button(label="❓ Aide", style=discord.ButtonStyle.secondary, row=1)
    async def show_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        help_msg = (
            "**📖 Comment choisir ta civilisation:**\n\n"
            "1. Clique sur **📝 Choisir ma civilisation**\n"
            "2. Entre l'emoji de la civilisation que tu veux jouer\n"
            "3. Clique sur **✅ Confirmer** pour valider ton choix\n\n"
            "**💡 Astuce:** Copie l'emoji directement depuis la liste ci-dessus!\n"
            "**⚠️ Note:** Tu ne peux choisir qu'une seule civilisation parmi celles proposées."
        )
        await interaction.response.send_message(help_msg, ephemeral=True)


class CivSelectionModal(discord.ui.Modal, title="Choisir ma civilisation"):
    """Modal for entering civilization emoji"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        
        self.civ_input = discord.ui.TextInput(
            label="Entre l'emoji de ta civilisation",
            placeholder="Exemple: 🎭",
            style=discord.TextStyle.short,
            required=True,
            max_length=10
        )
        self.add_item(self.civ_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        input_text = self.civ_input.value.strip()
        
        if not input_text:
            await interaction.response.send_message(
                "❌ Aucun emoji entré.",
                ephemeral=True
            )
            return
        
        # Parse emoji
        found_emojis = parse_emoji_from_text(input_text)
        
        if not found_emojis:
            await interaction.response.send_message(
                "❌ Aucun emoji valide trouvé.",
                ephemeral=True
            )
            return
        
        # Get the first emoji
        emoji = found_emojis[0]
        
        # Find matching civilization in available civs
        matching_civ = None
        for civ in self.parent_view.available_civs:
            if CIV_EMOJI_CONFIG.get(civ) == emoji:
                matching_civ = civ
                break
        
        if not matching_civ:
            await interaction.response.send_message(
                f"❌ {emoji} ne correspond à aucune de tes civilisations disponibles.\n"
                f"Vérifie la liste et réessaie.",
                ephemeral=True
            )
            return
        
        # Set the selection
        self.parent_view.selected_civ = matching_civ
        await interaction.response.send_message(
            f"✅ Civilisation sélectionnée: {emoji} {matching_civ}\n"
            f"Clique sur **✅ Confirmer** pour valider ton choix.",
            ephemeral=True
        )
