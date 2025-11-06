"""
Discord UI views for voting phase
"""
import discord
from core.configs import GAME_OPTIONS


class VoteView(discord.ui.View):
    """First page of voting interface"""
    
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
        game = self.game_manager.get_game(self.game_id)
        if "temp_votes" not in game:
            game["temp_votes"] = {}
        if str(self.user_id) not in game["temp_votes"]:
            game["temp_votes"][str(self.user_id)] = {}
        
        game["temp_votes"][str(self.user_id)].update(self.user_votes)
        self.game_manager.save()
        
        # Go to second view
        new_view = VoteView2(self.game_manager, self.game_id, self.user_id)
        new_view.user_votes = game["temp_votes"][str(self.user_id)].copy()
        
        await interaction.response.edit_message(
            content="🎮 **Votes pour la partie - Page 2/3**\n\nSélectionne tes options ci-dessous, puis clique sur 'Page suivante'.",
            view=new_view
        )


class VoteView2(discord.ui.View):
    """Second page of voting interface"""
    
    def __init__(self, game_manager, game_id, user_id):
        super().__init__(timeout=None)
        self.game_manager = game_manager
        self.game_id = game_id
        self.user_id = user_id
        self.user_votes = {}
        
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
        game = self.game_manager.get_game(self.game_id)
        if "temp_votes" not in game:
            game["temp_votes"] = {}
        if str(self.user_id) not in game["temp_votes"]:
            game["temp_votes"][str(self.user_id)] = {}
        
        game["temp_votes"][str(self.user_id)].update(self.user_votes)
        self.game_manager.save()
        
        new_view = VoteView(self.game_manager, self.game_id, self.user_id)
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
        game = self.game_manager.get_game(self.game_id)
        if "temp_votes" not in game:
            game["temp_votes"] = {}
        if str(self.user_id) not in game["temp_votes"]:
            game["temp_votes"][str(self.user_id)] = {}
        
        game["temp_votes"][str(self.user_id)].update(self.user_votes)
        self.game_manager.save()
        
        new_view = VoteView3(self.game_manager, self.game_id, self.user_id)
        new_view.user_votes = game["temp_votes"][str(self.user_id)].copy()
        
        await interaction.response.edit_message(
            content="🎮 **Votes pour la partie - Page 3/3**\n\nSélectionne tes dernières options ci-dessous, puis clique sur 'Valider'.",
            view=new_view
        )


class VoteView3(discord.ui.View):
    """Third page of voting interface"""
    
    def __init__(self, game_manager, game_id, user_id):
        super().__init__(timeout=None)
        self.game_manager = game_manager
        self.game_id = game_id
        self.user_id = user_id
        self.user_votes = {}
        
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
        game = self.game_manager.get_game(self.game_id)
        if "temp_votes" not in game:
            game["temp_votes"] = {}
        if str(self.user_id) not in game["temp_votes"]:
            game["temp_votes"][str(self.user_id)] = {}
        
        game["temp_votes"][str(self.user_id)].update(self.user_votes)
        self.game_manager.save()
        
        new_view = VoteView2(self.game_manager, self.game_id, self.user_id)
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
        game = self.game_manager.get_game(self.game_id)
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
        
        self.game_manager.save()
        
        await interaction.response.send_message(
            "🎉 Tous tes votes ont été enregistrés avec succès !", 
            ephemeral=True
        )
        
        # Disable all components
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        # Check if all players have finished voting
        await self.game_manager.check_voting_complete(interaction.client, self.game_id)


class OptionSelect(discord.ui.Select):
    """Select menu for a single voting category"""
    
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
