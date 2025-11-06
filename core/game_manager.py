import uuid
import discord
import random
import asyncio
import re
from core.storage import Storage
from core.configs import CIV_EMOJI_CONFIG, GAME_OPTIONS, LEADERS_TO_LINK

# Get list of leaders from config
LEADERS = list(CIV_EMOJI_CONFIG.keys())


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
        
        # Create modal for text input
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
        game = self.game_manager.storage.get_by_id(self.game_id)
        if "civ_selections" not in game:
            game["civ_selections"] = {}
        
        game["civ_selections"][str(self.user_id)] = self.selected_civ
        self.game_manager.storage.save()
        
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
        await self.game_manager.check_all_selections_complete(interaction.client, self.game_id)
    
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
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        
        # Add text input
        self.civ_input = discord.ui.TextInput(
            label="Entre l'emoji de ta civilisation",
            placeholder="Exemple: 🎭",
            style=discord.TextStyle.short,
            required=True,
            max_length=10
        )
        self.add_item(self.civ_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse emoji from input
        input_text = self.civ_input.value.strip()
        
        if not input_text:
            await interaction.response.send_message(
                "❌ Aucun emoji entré.",
                ephemeral=True
            )
            return
        
        # Extract emoji from the input
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002500-\U00002BEF"  # chinese char
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U00002600-\U000027BF"  # Miscellaneous Symbols
            "\U0001F650-\U0001F67F"  # Ornamental Dingbats
            "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "]+", 
            flags=re.UNICODE
        )
        
        found_emojis = emoji_pattern.findall(input_text)
        
        # Also check for multi-character emojis
        if "🕵️‍♀️" in input_text:
            found_emojis.append("🕵️‍♀️")
        
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


class BanCollectorView(discord.ui.View):
    """View for text-based emoji ban collection"""
    def __init__(self, game_manager, game_id, user_id, max_bans):
        super().__init__(timeout=600)  # 10 minute timeout
        self.game_manager = game_manager
        self.game_id = game_id
        self.user_id = user_id
        self.max_bans = max_bans
        self.selected_bans = []
        self.waiting_for_input = False
        
    @discord.ui.button(label="📝 Entrer mes bans", style=discord.ButtonStyle.primary, row=0)
    async def enter_bans(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ton interface de ban!", 
                ephemeral=True
            )
            return
        
        # Create modal for text input
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
        game = self.game_manager.storage.get_by_id(self.game_id)
        if "bans" not in game:
            game["bans"] = {}
        
        game["bans"][str(self.user_id)] = self.selected_bans
        self.game_manager.storage.save()
        
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
        await self.game_manager.check_all_bans_complete(interaction.client, self.game_id)
    
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
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        
        # Add text input
        self.ban_input = discord.ui.TextInput(
            label=f"Entre les emojis à bannir (max {parent_view.max_bans})",
            placeholder="Exemple: 🎭 ⚔️ 🦅 🌊",
            style=discord.TextStyle.short,
            required=False,
            max_length=100
        )
        self.add_item(self.ban_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse emojis from input
        input_text = self.ban_input.value.strip()
        
        if not input_text:
            await interaction.response.send_message(
                "❌ Aucun emoji entré. Utilise 🗑️ pour effacer tes bans.",
                ephemeral=True
            )
            return
        
        # Extract all emojis from the input
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002500-\U00002BEF"  # chinese char
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U00002600-\U000027BF"  # Miscellaneous Symbols
            "\U0001F650-\U0001F67F"  # Ornamental Dingbats
            "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "]+", 
            flags=re.UNICODE
        )
        
        found_emojis = emoji_pattern.findall(input_text)
        
        # Also check for multi-character emojis like 🕵️‍♀️
        if "🕵️‍♀️" in input_text:
            found_emojis.append("🕵️‍♀️")
        
        if not found_emojis:
            await interaction.response.send_message(
                "❌ Aucun emoji valide trouvé. Entre uniquement des emojis.",
                ephemeral=True
            )
            return
        
        # Map emojis to civilizations
        selected_civs = []
        not_found = []
        duplicates = []
        
        # Create reverse mapping
        emoji_to_civs = {}
        for civ, emoji in CIV_EMOJI_CONFIG.items():
            if emoji not in emoji_to_civs:
                emoji_to_civs[emoji] = []
            emoji_to_civs[emoji].append(civ)
        
        for emoji in found_emojis:
            if emoji in emoji_to_civs:
                civs = emoji_to_civs[emoji]
                if len(civs) == 1:
                    # Unique emoji
                    if civs[0] not in selected_civs:
                        selected_civs.append(civs[0])
                else:
                    # Duplicate emoji - need clarification
                    duplicates.append((emoji, civs))
            else:
                not_found.append(emoji)
        
        # Handle duplicates
        if duplicates:
            dup_msg = "**⚠️ Ces emojis correspondent à plusieurs civilisations:**\n"
            for emoji, civs in duplicates:
                dup_msg += f"\n{emoji} pourrait être:\n"
                for civ in civs:
                    dup_msg += f"  • {civ}\n"
            dup_msg += "\n**Les civilisations avec emojis uniques ont été ajoutées.**"
            
            # For now, add all civilizations with duplicate emojis
            for emoji, civs in duplicates:
                for civ in civs:
                    if civ not in selected_civs:
                        selected_civs.append(civ)
            
            await interaction.response.send_message(
                dup_msg + f"\n\n✅ {len(selected_civs)} civilisation(s) ajoutée(s) aux bans.",
                ephemeral=True
            )
        else:
            response = f"✅ {len(selected_civs)} civilisation(s) ajoutée(s) aux bans."
            if not_found:
                response += f"\n⚠️ Emojis non reconnus: {' '.join(not_found)}"
            await interaction.response.send_message(response, ephemeral=True)
        
        # Check max bans
        self.parent_view.selected_bans.extend(selected_civs)
        self.parent_view.selected_bans = list(set(self.parent_view.selected_bans))  # Remove duplicates
        
        if len(self.parent_view.selected_bans) > self.parent_view.max_bans:
            overflow = len(self.parent_view.selected_bans) - self.parent_view.max_bans
            self.parent_view.selected_bans = self.parent_view.selected_bans[:self.parent_view.max_bans]
            await interaction.followup.send(
                f"⚠️ Limite de {self.parent_view.max_bans} bans atteinte. {overflow} civilisation(s) ignorée(s).",
                ephemeral=True
            )


class VoteView(discord.ui.View):
    def __init__(self, game_manager, game_id, user_id):
        super().__init__(timeout=None)
        self.game_manager = game_manager
        self.game_id = game_id
        self.user_id = user_id
        self.user_votes = {}
        
        # Add first 4 select menus (rows 0-3)
        categories = list(GAME_OPTIONS.keys())
        
        for i, category in enumerate(categories[:4]):
            options = GAME_OPTIONS[category]
            self.add_item(
                OptionSelect(category, options, game_manager, game_id, user_id, self, row=i)
            )
    
    @discord.ui.button(
        label="Page suivante ➡️", 
        style=discord.ButtonStyle.primary, 
        row=4
    )
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Save current page votes temporarily
        game = self.game_manager.storage.get_by_id(self.game_id)
        if "temp_votes" not in game:
            game["temp_votes"] = {}
        if str(self.user_id) not in game["temp_votes"]:
            game["temp_votes"][str(self.user_id)] = {}
        
        game["temp_votes"][str(self.user_id)].update(self.user_votes)
        self.game_manager.storage.save()
        
        # Go to second view
        new_view = VoteView2(self.game_manager, self.game_id, self.user_id)
        # Restore votes from storage if any
        new_view.user_votes = game["temp_votes"][str(self.user_id)].copy()
        
        await interaction.response.edit_message(
            content="🎮 **Votes pour la partie - Page 2/3**\n\nSélectionne tes options ci-dessous, puis clique sur 'Page suivante'.",
            view=new_view
        )


class OptionSelect(discord.ui.Select):
    def __init__(self, category, options, game_manager, game_id, user_id, parent_view, row=0):
        self.category = category
        self.game_manager = game_manager
        self.game_id = game_id
        self.user_id = user_id
        self.parent_view = parent_view

        select_options = [
            discord.SelectOption(label=option, value=option) for option in options[:25]
        ]

        super().__init__(
            placeholder=f"Choisir: {category}",
            options=select_options,
            custom_id=f"vote_{game_id}_{category}_{user_id}",
            row=row
        )

    async def callback(self, interaction: discord.Interaction):
        # Store vote in parent view temporarily (silently)
        self.parent_view.user_votes[self.category] = self.values[0]
        
        # Just acknowledge the interaction without sending a message
        await interaction.response.defer()


class VoteView2(discord.ui.View):
    def __init__(self, game_manager, game_id, user_id):
        super().__init__(timeout=None)
        self.game_manager = game_manager
        self.game_id = game_id
        self.user_id = user_id
        self.user_votes = {}
        
        # Add remaining categories (5-11) - only 4 select menus per page
        categories = list(GAME_OPTIONS.keys())
        
        for i, category in enumerate(categories[4:8]):
            options = GAME_OPTIONS[category]
            self.add_item(
                OptionSelect(category, options, game_manager, game_id, user_id, self, row=i)
            )
    
    @discord.ui.button(
        label="⬅️ Retour", 
        style=discord.ButtonStyle.secondary, 
        row=4
    )
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Save current page votes temporarily
        game = self.game_manager.storage.get_by_id(self.game_id)
        if "temp_votes" not in game:
            game["temp_votes"] = {}
        if str(self.user_id) not in game["temp_votes"]:
            game["temp_votes"][str(self.user_id)] = {}
        
        game["temp_votes"][str(self.user_id)].update(self.user_votes)
        self.game_manager.storage.save()
        
        # Go back to first view
        new_view = VoteView(self.game_manager, self.game_id, self.user_id)
        # Restore previous votes
        new_view.user_votes = game["temp_votes"][str(self.user_id)].copy()
        
        await interaction.response.edit_message(
            content="🎮 **Votes pour la partie - Page 1/3**\n\nSélectionne tes options ci-dessous, puis clique sur 'Page suivante'.",
            view=new_view
        )
    
    @discord.ui.button(
        label="Page suivante ➡️", 
        style=discord.ButtonStyle.primary, 
        row=4
    )
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Save current page votes temporarily
        game = self.game_manager.storage.get_by_id(self.game_id)
        if "temp_votes" not in game:
            game["temp_votes"] = {}
        if str(self.user_id) not in game["temp_votes"]:
            game["temp_votes"][str(self.user_id)] = {}
        
        game["temp_votes"][str(self.user_id)].update(self.user_votes)
        self.game_manager.storage.save()
        
        # Go to third view
        new_view = VoteView3(self.game_manager, self.game_id, self.user_id)
        # Restore votes from storage if any
        new_view.user_votes = game["temp_votes"][str(self.user_id)].copy()
        
        await interaction.response.edit_message(
            content="🎮 **Votes pour la partie - Page 3/3**\n\nSélectionne tes dernières options ci-dessous, puis clique sur 'Valider'.",
            view=new_view
        )


class VoteView3(discord.ui.View):
    def __init__(self, game_manager, game_id, user_id):
        super().__init__(timeout=None)
        self.game_manager = game_manager
        self.game_id = game_id
        self.user_id = user_id
        self.user_votes = {}
        
        # Add final categories (9-11)
        categories = list(GAME_OPTIONS.keys())
        
        for i, category in enumerate(categories[8:]):
            options = GAME_OPTIONS[category]
            self.add_item(
                OptionSelect(category, options, game_manager, game_id, user_id, self, row=i)
            )
    
    @discord.ui.button(
        label="⬅️ Retour", 
        style=discord.ButtonStyle.secondary, 
        row=4
    )
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Save current page votes temporarily
        game = self.game_manager.storage.get_by_id(self.game_id)
        if "temp_votes" not in game:
            game["temp_votes"] = {}
        if str(self.user_id) not in game["temp_votes"]:
            game["temp_votes"][str(self.user_id)] = {}
        
        game["temp_votes"][str(self.user_id)].update(self.user_votes)
        self.game_manager.storage.save()
        
        # Go back to second view
        new_view = VoteView2(self.game_manager, self.game_id, self.user_id)
        # Restore previous votes
        new_view.user_votes = game["temp_votes"][str(self.user_id)].copy()
        
        await interaction.response.edit_message(
            content="🎮 **Votes pour la partie - Page 2/3**\n\nSélectionne tes options ci-dessous.",
            view=new_view
        )
    
    @discord.ui.button(
        label="✅ Valider tous mes choix", 
        style=discord.ButtonStyle.success, 
        row=4
    )
    async def submit_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get votes from all previous views
        game = self.game_manager.storage.get_by_id(self.game_id)
        previous_votes = game.get("temp_votes", {}).get(str(self.user_id), {})
        
        # Merge with current view votes
        all_votes = {**previous_votes, **self.user_votes}
        
        # Check if all categories have been voted on
        missing = []
        for category in GAME_OPTIONS.keys():
            if category not in all_votes:
                missing.append(category)
        
        if missing:
            await interaction.response.send_message(
                f"❌ Il te manque encore ces catégories:\n" + "\n".join(f"- {cat}" for cat in missing),
                ephemeral=True
            )
            return
        
        # Save all votes permanently
        if "votes" not in game:
            game["votes"] = {}
        game["votes"][str(self.user_id)] = all_votes
        
        # Clean up temp votes
        if "temp_votes" in game and str(self.user_id) in game["temp_votes"]:
            del game["temp_votes"][str(self.user_id)]
        
        self.game_manager.storage.save()
        
        await interaction.response.send_message(
            "🎉 Tous tes votes ont été enregistrés avec succès !", 
            ephemeral=True
        )
        
        # Disable all components
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        # Check if all players have finished voting
        await self.game_manager.check_all_votes_complete(interaction.client, self.game_id)


class GameManager:
    def __init__(self):
        self.storage = Storage("data/games.json")

    def create_game(self, creator_id, max_bans=2, civ_pool_size=3):
        game_id = str(uuid.uuid4())[:8]
        game = {
            "id": game_id,
            "creator": creator_id,
            "players": [],
            "votes": {},
            "bans": {},
            "civ_selections": {},
            "civ_pools": {},
            "max_bans": max_bans,
            "civ_pool_size": civ_pool_size,
            "voting_started": False,
            "banning_started": False,
            "selection_started": False,
            "results_channel_id": None,
        }
        self.storage.add(game)
        return game

    def create_join_view(self, game_id):
        view = discord.ui.View(timeout=None)
        join_button = discord.ui.Button(
            label="Rejoindre la partie", style=discord.ButtonStyle.green
        )
        start_button = discord.ui.Button(
            label="Commencer les votes", style=discord.ButtonStyle.primary
        )

        async def join_callback(inter):
            game = self.storage.get_by_id(game_id)
            if game["voting_started"]:
                await inter.response.send_message(
                    "Les votes ont déjà commencé !", ephemeral=True
                )
                return

            if inter.user.id not in game["players"]:
                game["players"].append(inter.user.id)
                self.storage.save()
                await inter.response.send_message(
                    f"{inter.user.mention} a rejoint la partie !", ephemeral=False
                )
            else:
                await inter.response.send_message(
                    "Tu es déjà dans la partie.", ephemeral=True
                )

        async def start_callback(inter):
            game = self.storage.get_by_id(game_id)
            if inter.user.id != game["creator"]:
                await inter.response.send_message(
                    "Seul le créateur peut commencer les votes !", ephemeral=True
                )
                return

            if len(game["players"]) == 0:
                await inter.response.send_message(
                    "Aucun joueur n'a rejoint la partie !", ephemeral=True
                )
                return

            game["voting_started"] = True
            game["results_channel_id"] = inter.channel_id
            self.storage.save()

            join_button.disabled = True
            start_button.disabled = True
            await inter.message.edit(view=view)

            await inter.response.send_message(
                "🗳️ Les votes ont commencé ! Chaque joueur va recevoir un message privé."
            )

            failed_users = []
            for player_id in game["players"]:
                try:
                    user = await inter.client.fetch_user(player_id)
                    vote_view = VoteView(self, game_id, player_id)
                    await user.send(
                        f"🎮 **Votes pour la partie {game_id} - Page 1/3**\n\n"
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
                await inter.channel.send(
                    f"⚠️ Impossible d'envoyer les MPs à : {', '.join(failed_users)}\n"
                    f"Ils doivent activer les MPs depuis les membres du serveur dans leurs paramètres de confidentialité."
                )

        join_button.callback = join_callback
        start_button.callback = start_callback
        view.add_item(join_button)
        view.add_item(start_button)
        return view

    async def send_ban_interface(self, user, game_id, user_id, max_bans, weighted_results):
        """Send the text-based emoji ban interface to a user"""
        
        # Create settings summary
        settings_summary = "\n".join([f"• **{cat}**: {res['selected']}" 
                                     for cat, res in weighted_results.items()])
        
        # Split civilizations into multiple messages (Discord 2000 char limit)
        civ_chunks = []
        current_chunk = []
        current_length = 0
        
        for civ, emoji in CIV_EMOJI_CONFIG.items():
            line = f"{emoji} {civ}\n"
            if current_length + len(line) > 1800:  # Leave margin for headers
                civ_chunks.append(current_chunk)
                current_chunk = [line]
                current_length = len(line)
            else:
                current_chunk.append(line)
                current_length += len(line)
        
        if current_chunk:
            civ_chunks.append(current_chunk)
        
        # Send introduction
        await user.send(
            f"🚫 **Phase de Ban - Partie {game_id}**\n\n"
            f"📋 **Paramètres de la partie:**\n{settings_summary}\n\n"
            f"Tu peux bannir jusqu'à **{max_bans}** civilisations."
        )
        
        # Send civilization lists
        for i, chunk in enumerate(civ_chunks, 1):
            msg = f"**📜 Liste des Civilisations ({i}/{len(civ_chunks)}):**\n"
            msg += "".join(chunk)
            await user.send(msg)
        
        # Send control interface
        ban_view = BanCollectorView(self, game_id, user_id, max_bans)
        await user.send(
            f"**🎯 Comment bannir des civilisations:**\n\n"
            f"1️⃣ **Copie les emojis** des civilisations que tu veux bannir depuis les listes ci-dessus\n"
            f"2️⃣ Clique sur **📝 Entrer mes bans**\n"
            f"3️⃣ **Colle les emojis** dans la fenêtre (exemple: `🎭 ⚔️ 🦅`)\n"
            f"4️⃣ Clique sur **✅ Confirmer mes bans** quand tu as fini\n\n"
            f"💡 **Astuce:** Tu peux entrer plusieurs emojis à la fois, séparés par des espaces!",
            view=ban_view
        )

    async def send_civ_selection_interface(self, bot, game_id, user_id):
        """Send civilization selection interface to a player"""
        game = self.storage.get_by_id(game_id)
        if not game:
            return
        
        try:
            user = await bot.fetch_user(user_id)
            player_civs = game["civ_pools"].get(str(user_id), [])
            
            if not player_civs:
                print(f"⚠️ Aucune civilisation disponible pour {user_id}")
                return
            
            civ_list = "\n".join([f"{CIV_EMOJI_CONFIG[civ]} [{civ}]({LEADERS_TO_LINK[civ]})" for civ in player_civs])

            embed = discord.Embed(
                title=f"🎯 Phase de Sélection - Partie {game_id}",
                description=(
                    f"**Tes civilisations disponibles ({len(player_civs)}):**\n{civ_list}\n\n"
                    f"Choisis UNE civilisation parmi cette liste en utilisant les boutons ci-dessous."
                ),
                color=0x3498db
            )

            await user.send(embed=embed)

            selection_view = CivSelectionView(self, game_id, user_id, player_civs)

            instructions = (
                "**🎯 Comment choisir ta civilisation:**\n\n"
                "1️⃣ **Copie l'emoji** de la civilisation que tu veux jouer\n"
                "2️⃣ Clique sur **📝 Choisir ma civilisation**\n"
                "3️⃣ **Colle l'emoji** dans la fenêtre\n"
                "4️⃣ Clique sur **✅ Confirmer** pour valider ton choix\n\n"
                "💡 **Astuce:** Assure-toi de choisir l'une des civilisations de ta liste!"
            )

            await user.send(instructions, view=selection_view)

            
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi de la sélection à {user_id}: {e}")

    def assign_civ_pools(self, game_id):
        """Assign random unique civilization pools to each player"""
        game = self.storage.get_by_id(game_id)
        if not game:
            return False
        
        # Get available civilizations (not banned)
        available_civs = self.get_available_civs_list(game_id)
        
        # Check if we have enough civs
        civ_pool_size = game.get("civ_pool_size", 3)
        total_needed = len(game["players"]) * civ_pool_size
        
        if len(available_civs) < total_needed:
            print(f"⚠️ Pas assez de civilisations disponibles: {len(available_civs)} < {total_needed}")
            return False
        
        # Shuffle and assign
        random.shuffle(available_civs)
        game["civ_pools"] = {}
        
        for i, player_id in enumerate(game["players"]):
            start_idx = i * civ_pool_size
            end_idx = start_idx + civ_pool_size
            game["civ_pools"][str(player_id)] = available_civs[start_idx:end_idx]
        
        self.storage.save()
        return True

    def get_voting_progress(self, game_id):
        game = self.storage.get_by_id(game_id)
        if not game or not game.get("voting_started"):
            return None
        
        total_players = len(game["players"])
        votes_data = game.get("votes", {})
        
        progress = {}
        for player_id in game["players"]:
            player_votes = votes_data.get(str(player_id), {})
            completed = len(player_votes) == len(GAME_OPTIONS)
            progress[player_id] = {
                "voted_categories": len(player_votes),
                "total_categories": len(GAME_OPTIONS),
                "completed": completed
            }
        
        return progress

    def get_ban_progress(self, game_id):
        game = self.storage.get_by_id(game_id)
        if not game or not game.get("banning_started"):
            return None
        
        bans_data = game.get("bans", {})
        max_bans = game.get("max_bans", 2)
        
        progress = {}
        for player_id in game["players"]:
            player_bans = bans_data.get(str(player_id), [])
            progress[player_id] = {
                "bans_count": len(player_bans),
                "max_bans": max_bans,
                "completed": str(player_id) in bans_data
            }
        
        return progress

    def get_selection_progress(self, game_id):
        game = self.storage.get_by_id(game_id)
        if not game or not game.get("selection_started"):
            return None
        
        selections = game.get("civ_selections", {})
        
        progress = {}
        for player_id in game["players"]:
            progress[player_id] = {
                "completed": str(player_id) in selections,
                "selection": selections.get(str(player_id))
            }
        
        return progress

    async def check_all_votes_complete(self, bot, game_id):
        game = self.storage.get_by_id(game_id)
        if not game:
            return
        
        progress = self.get_voting_progress(game_id)
        if not progress:
            return
        
        all_complete = all(p["completed"] for p in progress.values())
        
        if all_complete and not game.get("banning_started"):
            # Start ban phase
            game["banning_started"] = True
            self.storage.save()
            
            # Send settings to players and start ban phase
            channel_id = game.get("results_channel_id")
            if channel_id:
                try:
                    channel = await bot.fetch_channel(channel_id)
                    
                    # Calculate and show results first
                    weighted_results = self.calculate_weighted_results(game_id)
                    
                    results_msg = "## 🎲 Paramètres sélectionnés pour la partie\n\n"
                    for category, result_data in weighted_results.items():
                        results_msg += f"**{category}**: {result_data['selected']}\n"
                    
                    await channel.send(results_msg)
                    await channel.send(
                        f"✅ Tous les joueurs ont voté ! Les paramètres ont été tirés.\n"
                        f"🚫 La phase de ban commence maintenant ! Chaque joueur peut bannir jusqu'à **{game.get('max_bans', 2)}** civilisations."
                    )
                    
                    # Send ban interface to players
                    failed_users = []
                    for player_id in game["players"]:
                        try:
                            user = await bot.fetch_user(player_id)
                            await self.send_ban_interface(
                                user, game_id, player_id, 
                                game.get("max_bans", 2), 
                                weighted_results
                            )
                        except Exception as e:
                            failed_users.append(f"<@{player_id}>")
                            print(f"❌ Erreur lors de l'envoi du ban à {player_id}: {e}")
                    
                    if failed_users:
                        await channel.send(
                            f"⚠️ Impossible d'envoyer la phase de ban à : {', '.join(failed_users)}"
                        )
                        
                except Exception as e:
                    print(f"Erreur lors du démarrage de la phase de ban: {e}")

    async def check_all_bans_complete(self, bot, game_id):
        game = self.storage.get_by_id(game_id)
        if not game:
            return
        
        ban_progress = self.get_ban_progress(game_id)
        if not ban_progress:
            return
        
        all_complete = all(p["completed"] for p in ban_progress.values())
        
        if all_complete and not game.get("selection_started"):
            # Start civilization selection phase
            game["selection_started"] = True
            self.storage.save()
            
            # Assign civilization pools
            if not self.assign_civ_pools(game_id):
                channel_id = game.get("results_channel_id")
                if channel_id:
                    try:
                        channel = await bot.fetch_channel(channel_id)
                        await channel.send(
                            "❌ Erreur: Pas assez de civilisations disponibles pour tous les joueurs!"
                        )
                    except:
                        pass
                return
            
            # Notify in channel
            channel_id = game.get("results_channel_id")
            if channel_id:
                try:
                    channel = await bot.fetch_channel(channel_id)
                    await channel.send(
                        f"✅ Tous les joueurs ont terminé leurs bans!\n"
                        f"🎯 La phase de sélection commence ! Chaque joueur va recevoir {game.get('civ_pool_size', 3)} civilisations et doit en choisir une."
                    )
                except Exception as e:
                    print(f"Erreur lors de la notification: {e}")
            
            # Send selection interface to all players
            failed_users = []
            for player_id in game["players"]:
                try:
                    await self.send_civ_selection_interface(bot, game_id, player_id)
                except Exception as e:
                    failed_users.append(f"<@{player_id}>")
                    print(f"❌ Erreur lors de l'envoi de la sélection à {player_id}: {e}")
            
            if failed_users and channel_id:
                try:
                    channel = await bot.fetch_channel(channel_id)
                    await channel.send(
                        f"⚠️ Impossible d'envoyer la phase de sélection à : {', '.join(failed_users)}"
                    )
                except:
                    pass

    async def check_all_selections_complete(self, bot, game_id):
        game = self.storage.get_by_id(game_id)
        if not game:
            return
        
        selection_progress = self.get_selection_progress(game_id)
        if not selection_progress:
            return
        
        all_complete = all(p["completed"] for p in selection_progress.values())
        
        if all_complete:
            # Create final results thread with selections
            channel_id = game.get("results_channel_id")
            if channel_id:
                try:
                    channel = await bot.fetch_channel(channel_id)
                    thread = await self.create_final_results_thread(channel, game_id)
                    if thread:
                        await channel.send(
                            f"🎊 Tous les joueurs ont choisi leur civilisation ! Les résultats finaux sont dans {thread.mention}"
                        )
                except Exception as e:
                    print(f"Erreur lors de la création du thread final: {e}")

    def calculate_weighted_results(self, game_id, force_recalculate=False):
        game = self.storage.get_by_id(game_id)
        if not game:
            return None
        
        # Return stored results if they exist (unless force_recalculate is True)
        if not force_recalculate and "final_settings" in game:
            return game["final_settings"]
        
        final_settings = {}
        
        for category in GAME_OPTIONS.keys():
            votes_count = {}
            
            # Count votes for this category
            for player_id, votes in game["votes"].items():
                if category in votes:
                    choice = votes[category]
                    votes_count[choice] = votes_count.get(choice, 0) + 1
            
            # Weighted random selection
            if votes_count:
                choices = list(votes_count.keys())
                weights = list(votes_count.values())
                selected = random.choices(choices, weights=weights, k=1)[0]
                final_settings[category] = {
                    "selected": selected,
                    "votes": votes_count
                }
        
        # Store the results permanently in the game data
        game["final_settings"] = final_settings
        self.storage.save()
        
        return final_settings

    def get_available_civs_list(self, game_id):
        """Get list of civilizations that weren't banned (just the names)"""
        game = self.storage.get_by_id(game_id)
        if not game:
            return []
        
        # Collect all banned civs
        all_bans = []
        for player_bans in game.get("bans", {}).values():
            all_bans.extend(player_bans)
        
        # Get unique bans
        banned_civs = list(set(all_bans))
        
        # Return available civ names only
        available = [civ for civ in LEADERS if civ not in banned_civs]
        return available

    def get_available_civs(self, game_id):
        """Get list of civilizations that weren't banned (with emojis)"""
        game = self.storage.get_by_id(game_id)
        if not game:
            return []
        
        # Collect all banned civs
        all_bans = []
        for player_bans in game.get("bans", {}).values():
            all_bans.extend(player_bans)
        
        # Get unique bans
        banned_civs = list(set(all_bans))
        
        # Return available civs with their emojis
        available = [(CIV_EMOJI_CONFIG.get(civ, ""), civ) for civ in LEADERS if civ not in banned_civs]
        return available

    async def create_final_results_thread(self, channel, game_id):
        game = self.storage.get_by_id(game_id)
        if not game:
            return None

        thread = await channel.create_thread(
            name=f"Résultats Finaux - Partie {game_id}",
            type=discord.ChannelType.public_thread,
            auto_archive_duration=1440,
        )

        # Calculate weighted random results
        weighted_results = self.calculate_weighted_results(game_id)
        
        # First message: Game settings
        settings_msg = f"# 🎮 Résultats Finaux - Partie {game_id}\n\n"
        settings_msg += "## 🎲 Configuration sélectionnée\n\n"
        
        for category, result_data in weighted_results.items():
            selected = result_data["selected"]
            votes_count = result_data["votes"]
            total_votes = sum(votes_count.values())
            winning_votes = votes_count.get(selected, 0)
            settings_msg += f"**{category}**: {selected} ({winning_votes}/{total_votes} votes)\n"
        
        await thread.send(settings_msg)
        
        # Second message: Player selections
        selections_msg = "## 👑 Civilisations choisies par les joueurs\n\n"
        
        civ_selections = game.get("civ_selections", {})
        if civ_selections:
            for player_id, civ in civ_selections.items():
                try:
                    user = await channel.guild.get_member(int(player_id)) or await channel.guild.fetch_member(int(player_id))
                    emoji = CIV_EMOJI_CONFIG.get(civ, "")
                    selections_msg += f"{emoji} **{user.name}**: {civ}\n"
                except:
                    emoji = CIV_EMOJI_CONFIG.get(civ, "")
                    selections_msg += f"{emoji} **Joueur {player_id}**: {civ}\n"
        else:
            selections_msg += "*Aucune sélection effectuée*\n"
        
        await thread.send(selections_msg)
        
        # Third message: Banned civilizations
        bans_msg = "## 🚫 Civilisations bannies\n\n"
        
        all_bans = {}
        for player_id, bans in game.get("bans", {}).items():
            for ban in bans:
                if ban not in all_bans:
                    all_bans[ban] = []
                all_bans[ban].append(player_id)
        
        if all_bans:
            # Sort by number of bans (most banned first)
            sorted_bans = sorted(all_bans.items(), key=lambda x: len(x[1]), reverse=True)
            for civ, banners in sorted_bans[:30]:  # Limit display
                emoji = CIV_EMOJI_CONFIG.get(civ, "")
                bans_msg += f"{emoji} **{civ}** - {len(banners)} ban(s)\n"
            
            if len(sorted_bans) > 30:
                bans_msg += f"\n*Et {len(sorted_bans) - 30} autres civilisations bannies...*\n"
        else:
            bans_msg += "*Aucune civilisation bannie*\n"
        
        await thread.send(bans_msg)
        
        # Fourth message: Available civilizations (that weren't chosen)
        available_civs = self.get_available_civs(game_id)
        chosen_civs = set(civ_selections.values())
        remaining_civs = [(emoji, civ) for emoji, civ in available_civs if civ not in chosen_civs]
        
        if remaining_civs:
            # Split into chunks
            avail_chunks = []
            current_msg = f"## ✅ Civilisations disponibles non choisies ({len(remaining_civs)})\n\n"
            
            for emoji, civ in remaining_civs:
                line = f"{emoji} {civ}\n"
                if len(current_msg) + len(line) > 1900:
                    avail_chunks.append(current_msg)
                    current_msg = line
                else:
                    current_msg += line
            
            if current_msg and current_msg != f"## ✅ Civilisations disponibles non choisies ({len(remaining_civs)})\n\n":
                avail_chunks.append(current_msg)
            
            for msg in avail_chunks[:2]:  # Limit to 2 messages
                await thread.send(msg)
            
            if len(avail_chunks) > 2:
                await thread.send(f"*... et d'autres civilisations disponibles*")
        
        return thread

    async def create_results_thread(self, channel, game_id):
        """Legacy method for compatibility"""
        return await self.create_final_results_thread(channel, game_id)