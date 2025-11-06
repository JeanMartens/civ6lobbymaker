"""
Discord UI views for ban phase
"""
import discord
from core.configs import CIV_EMOJI_CONFIG
from utils.civilization import parse_emoji_from_text, emojis_to_civs


class BanCollectorView(discord.ui.View):
    """View for text-based emoji ban collection"""
    
    def __init__(self, game_manager, game_id, user_id, max_bans):
        super().__init__(timeout=600)  # 10 minute timeout
        self.game_manager = game_manager
        self.game_id = game_id
        self.user_id = user_id
        self.max_bans = max_bans
        self.selected_bans = []
        
    @discord.ui.button(label="📝 Entrer mes bans", style=discord.ButtonStyle.primary, row=0)
    async def enter_bans(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ton interface de ban!", 
                ephemeral=True
            )
            return
        
        modal = BanInputModal(self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="👀 Voir mes bans actuels", style=discord.ButtonStyle.secondary, row=0)
    async def view_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ton interface de ban!", 
                ephemeral=True
            )
            return
        
        if not self.selected_bans:
            await interaction.response.send_message(
                "Tu n'as encore sélectionné aucune civilisation.",
                ephemeral=True
            )
        else:
            ban_list = "\n".join([f"{CIV_EMOJI_CONFIG[civ]} {civ}" for civ in self.selected_bans])
            await interaction.response.send_message(
                f"**Tes bans actuels ({len(self.selected_bans)}/{self.max_bans}):**\n{ban_list}",
                ephemeral=True
            )
    
    @discord.ui.button(label="🗑️ Effacer mes bans", style=discord.ButtonStyle.secondary, row=0)
    async def clear_bans(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ton interface de ban!", 
                ephemeral=True
            )
            return
        
        self.selected_bans = []
        await interaction.response.send_message(
            "✅ Tes bans ont été effacés!",
            ephemeral=True
        )
    
    @discord.ui.button(label="✅ Confirmer mes bans", style=discord.ButtonStyle.success, row=1)
    async def confirm_bans(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ton interface de ban!", 
                ephemeral=True
            )
            return
        
        # Save bans
        game = self.game_manager.get_game(self.game_id)
        if "bans" not in game:
            game["bans"] = {}
        
        game["bans"][str(self.user_id)] = self.selected_bans
        self.game_manager.save()
        
        # Send confirmation
        if self.selected_bans:
            ban_list = "\n".join([f"{CIV_EMOJI_CONFIG[civ]} {civ}" for civ in self.selected_bans[:10]])
            if len(self.selected_bans) > 10:
                ban_list += f"\n*... et {len(self.selected_bans) - 10} autres*"
            response_msg = f"🚫 **Tes bans ont été enregistrés ({len(self.selected_bans)} civilisation(s)):**\n{ban_list}"
        else:
            response_msg = "✅ Tu as choisi de ne bannir aucune civilisation!"
        
        await interaction.response.send_message(response_msg, ephemeral=True)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        # Check if all players have finished banning
        await self.game_manager.check_bans_complete(interaction.client, self.game_id)
    
    @discord.ui.button(label="❓ Aide", style=discord.ButtonStyle.secondary, row=1)
    async def show_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        help_msg = (
            "**📖 Comment utiliser le système de ban:**\n\n"
            "1. Clique sur **📝 Entrer mes bans**\n"
            "2. Entre les emojis des civilisations à bannir\n"
            "   Exemple: `🎭 ⚔️ 🦅` (pour bannir Lincoln, Alexandre et Chaka)\n"
            "3. Tu peux entrer plusieurs emojis séparés par des espaces\n"
            f"4. Tu peux bannir jusqu'à **{self.max_bans}** civilisations\n"
            "5. Clique sur **✅ Confirmer** quand tu as fini\n\n"
            "**💡 Astuce:** Copie les emojis directement depuis la liste des civilisations!\n"
            f"**💡 Astuce:** Tu peux bannir autant de civilisation que tu le souhaites en deçà de la limite qui est de {self.max_bans}"
        )
        await interaction.response.send_message(help_msg, ephemeral=True)


class BanInputModal(discord.ui.Modal, title="Entrer les bans"):
    """Modal for entering ban emojis"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        
        self.ban_input = discord.ui.TextInput(
            label=f"Entre les emojis à bannir (max {parent_view.max_bans})",
            placeholder="Exemple: 🎭 ⚔️ 🦅 🌊",
            style=discord.TextStyle.short,
            required=False,
            max_length=100
        )
        self.add_item(self.ban_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        input_text = self.ban_input.value.strip()
        
        if not input_text:
            await interaction.response.send_message(
                "❌ Aucun emoji entré. Utilise 🗑️ pour effacer tes bans.",
                ephemeral=True
            )
            return
        
        # Parse emojis
        found_emojis = parse_emoji_from_text(input_text)
        
        if not found_emojis:
            await interaction.response.send_message(
                "❌ Aucun emoji valide trouvé. Entre uniquement des emojis.",
                ephemeral=True
            )
            return
        
        # Convert to civilizations
        selected_civs, not_found, duplicates = emojis_to_civs(found_emojis)
        
        # Handle duplicates
        if duplicates:
            dup_msg = "**⚠️ Ces emojis correspondent à plusieurs civilisations:**\n"
            for emoji, civs in duplicates:
                dup_msg += f"\n{emoji} pourrait être:\n"
                for civ in civs:
                    dup_msg += f"  • {civ}\n"
            dup_msg += "\n**Les civilisations avec emojis uniques ont été ajoutées.**"
            
            await interaction.response.send_message(
                dup_msg + f"\n\n✅ {len(selected_civs)} civilisation(s) ajoutée(s) aux bans.",
                ephemeral=True
            )
        else:
            response = f"✅ {len(selected_civs)} civilisation(s) ajoutée(s) aux bans."
            if not_found:
                response += f"\n⚠️ Emojis non reconnus: {' '.join(not_found)}"
            await interaction.response.send_message(response, ephemeral=True)
        
        # Add to bans
        self.parent_view.selected_bans.extend(selected_civs)
        self.parent_view.selected_bans = list(set(self.parent_view.selected_bans))  # Remove duplicates
        
        # Check max bans
        if len(self.parent_view.selected_bans) > self.parent_view.max_bans:
            overflow = len(self.parent_view.selected_bans) - self.parent_view.max_bans
            self.parent_view.selected_bans = self.parent_view.selected_bans[:self.parent_view.max_bans]
            await interaction.followup.send(
                f"⚠️ Limite de {self.parent_view.max_bans} bans atteinte. {overflow} civilisation(s) ignorée(s).",
                ephemeral=True
            )
