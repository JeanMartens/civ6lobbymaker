"""
Main game manager - orchestrates game flow and phase transitions
"""
import discord
from typing import Optional, Dict, Any, List
from models.game import Game
from core.storage import Storage
from core.configs import CIV_EMOJI_CONFIG, GAME_OPTIONS, LEADERS_TO_LINK
from utils.civilization import get_available_civs, assign_civ_pools
from utils.voting import calculate_weighted_results, format_vote_results
from views.game_views import GameJoinView
from views.ban_views import BanCollectorView
from views.selection_views import CivSelectionView


class GameManager:
    """Manages all game operations and state transitions"""
    
    def __init__(self):
        self.storage = Storage("data/games.json")
    
    def create_game(self, creator_id: int, max_bans: int = 2, civ_pool_size: int = 3, thread_id: Optional[int] = None) -> Dict:
        """Create a new game"""
        game = Game(creator_id, max_bans, civ_pool_size, thread_id)
        game_dict = game.to_dict()
        self.storage.add(game_dict)
        return game_dict
    
    def get_game(self, game_id: str) -> Optional[Dict]:
        """Get game by ID"""
        return self.storage.get_by_id(game_id)
    
    def save(self):
        """Save games to storage"""
        self.storage.save()
    
    def create_join_view(self, game_id: str) -> GameJoinView:
        """Create the join/start view for a game"""
        return GameJoinView(self, game_id)
    
    async def check_voting_complete(self, bot, game_id: str):
        """Check if all players finished voting and start ban phase"""
        game = self.get_game(game_id)
        if not game or game.get("banning_started"):
            return
        
        # Check if all voted
        all_complete = True
        for player_id in game["players"]:
            votes = game.get("votes", {}).get(str(player_id))
            if not votes or len(votes) < len(GAME_OPTIONS):
                all_complete = False
                break
        
        if not all_complete:
            return
        
        # Start ban phase
        game["banning_started"] = True
        self.save()
        
        # Post results to thread
        channel_id = game.get("thread_id") or game.get("results_channel_id")
        if not channel_id:
            return
        
        try:
            channel = await bot.fetch_channel(channel_id)
            
            # Calculate and show results
            weighted_results = calculate_weighted_results(game.get("votes", {}), GAME_OPTIONS)
            game["final_settings"] = weighted_results
            self.save()
            
            results_msg = format_vote_results(weighted_results)
            await channel.send(results_msg)
            await channel.send(
                f"✅ Tous les joueurs ont voté ! Les paramètres ont été tirés.\n"
                f"🚫 La phase de ban commence maintenant ! Chaque joueur peut bannir jusqu'à **{game.get('max_bans', 2)}** civilisations."
            )
            
            # Send ban interface to players
            await self._send_ban_interfaces(bot, game_id, weighted_results, channel)
            
        except Exception as e:
            print(f"Erreur lors du démarrage de la phase de ban: {e}")
    
    async def check_bans_complete(self, bot, game_id: str):
        """Check if all players finished banning and start selection phase"""
        game = self.get_game(game_id)
        if not game or game.get("selection_started"):
            return
        
        # Check if all banned
        all_complete = all(
            str(player_id) in game.get("bans", {})
            for player_id in game["players"]
        )
        
        if not all_complete:
            return
        
        # Start selection phase
        game["selection_started"] = True
        self.save()
        
        # Assign civ pools
        banned_civs = []
        for bans in game.get("bans", {}).values():
            banned_civs.extend(bans)
        banned_civs = list(set(banned_civs))
        
        available = get_available_civs(banned_civs)
        pools = assign_civ_pools(available, len(game["players"]), game.get("civ_pool_size", 3))
        
        if not pools:
            channel_id = game.get("thread_id") or game.get("results_channel_id")
            if channel_id:
                try:
                    channel = await bot.fetch_channel(channel_id)
                    await channel.send("❌ Erreur: Pas assez de civilisations disponibles!")
                except:
                    pass
            return
        
        # Store pools
        game["civ_pools"] = {
            str(game["players"][i]): pools[i]
            for i in range(len(game["players"]))
        }
        self.save()
        
        # Notify in thread
        channel_id = game.get("thread_id") or game.get("results_channel_id")
        if channel_id:
            try:
                channel = await bot.fetch_channel(channel_id)
                await channel.send(
                    f"✅ Tous les joueurs ont terminé leurs bans!\n"
                    f"🎯 La phase de sélection commence ! Chaque joueur va recevoir {game.get('civ_pool_size', 3)} civilisations et doit en choisir une."
                )
            except Exception as e:
                print(f"Erreur lors de la notification: {e}")
        
        # Send selection interfaces
        await self._send_selection_interfaces(bot, game_id, channel if channel_id else None)
    
    async def check_selections_complete(self, bot, game_id: str):
        """Check if all players selected civilizations and show final results"""
        game = self.get_game(game_id)
        if not game:
            return
        
        # Check if all selected
        all_complete = all(
            str(player_id) in game.get("civ_selections", {})
            for player_id in game["players"]
        )
        
        if not all_complete:
            return
        
        # Post final results
        channel_id = game.get("thread_id") or game.get("results_channel_id")
        if channel_id:
            try:
                channel = await bot.fetch_channel(channel_id)
                await self._send_final_results(channel, game_id)
                await channel.send(
                    f"🎊 Tous les joueurs ont choisi leur civilisation ! Les résultats finaux sont ci-dessus."
                )
            except Exception as e:
                print(f"Erreur lors de la création des résultats finaux: {e}")
    
    async def _send_ban_interfaces(self, bot, game_id: str, weighted_results: Dict, channel):
        """Send ban interface to all players"""
        game = self.get_game(game_id)
        if not game:
            return
        
        failed_users = []
        for player_id in game["players"]:
            try:
                user = await bot.fetch_user(player_id)
                await self._send_ban_interface_to_user(
                    user, game_id, player_id, 
                    game.get("max_bans", 2), 
                    weighted_results
                )
            except Exception as e:
                failed_users.append(f"<@{player_id}>")
                print(f"❌ Erreur lors de l'envoi du ban à {player_id}: {e}")
        
        if failed_users and channel:
            await channel.send(
                f"⚠️ Impossible d'envoyer la phase de ban à : {', '.join(failed_users)}"
            )
    
    async def _send_ban_interface_to_user(self, user, game_id: str, user_id: int, max_bans: int, weighted_results: Dict):
        """Send ban interface to a single user"""
        # Settings summary
        settings_summary = "\n".join([
            f"• **{cat}**: {res['selected']}" 
            for cat, res in weighted_results.items()
        ])
        
        # Split civs into chunks
        civ_chunks = []
        current_chunk = []
        current_length = 0
        
        for civ, emoji in CIV_EMOJI_CONFIG.items():
            line = f"{emoji} {civ}\n"
            if current_length + len(line) > 1800:
                civ_chunks.append(current_chunk)
                current_chunk = [line]
                current_length = len(line)
            else:
                current_chunk.append(line)
                current_length += len(line)
        
        if current_chunk:
            civ_chunks.append(current_chunk)
        
        # Send intro
        await user.send(
            f"🚫 **Phase de Ban - Partie {game_id}**\n\n"
            f"📋 **Paramètres de la partie:**\n{settings_summary}\n\n"
            f"Tu peux bannir jusqu'à **{max_bans}** civilisations."
        )
        
        # Send civ lists
        for i, chunk in enumerate(civ_chunks, 1):
            msg = f"**📜 Liste des Civilisations ({i}/{len(civ_chunks)}):**\n"
            msg += "".join(chunk)
            await user.send(msg)
        
        # Send control interface
        ban_view = BanCollectorView(self, game_id, user_id, max_bans)
        await user.send(
            f"**🎯 Comment bannir des civilisations:**\n\n"
            f"1️⃣ **Copie les emojis** des civilisations que tu veux bannir\n"
            f"2️⃣ Clique sur **📝 Entrer mes bans**\n"
            f"3️⃣ **Colle les emojis** dans la fenêtre\n"
            f"4️⃣ Clique sur **✅ Confirmer mes bans** quand tu as fini\n\n"
            f"💡 **Astuce:** Tu peux entrer plusieurs emojis à la fois!",
            view=ban_view
        )
    
    async def _send_selection_interfaces(self, bot, game_id: str, channel):
        """Send selection interface to all players"""
        game = self.get_game(game_id)
        if not game:
            return
        
        failed_users = []
        for player_id in game["players"]:
            try:
                user = await bot.fetch_user(player_id)
                player_civs = game["civ_pools"].get(str(player_id), [])
                
                if not player_civs:
                    print(f"⚠️ Aucune civilisation disponible pour {player_id}")
                    continue
                
                civ_list = "\n".join([
                    f"{CIV_EMOJI_CONFIG[civ]} [{civ}]({LEADERS_TO_LINK[civ]})" 
                    for civ in player_civs
                ])

                embed = discord.Embed(
                    title=f"🎯 Phase de Sélection - Partie {game_id}",
                    description=(
                        f"**Tes civilisations disponibles ({len(player_civs)}):**\n{civ_list}\n\n"
                        f"Choisis UNE civilisation parmi cette liste."
                    ),
                    color=0x3498db
                )

                await user.send(embed=embed)

                selection_view = CivSelectionView(self, game_id, player_id, player_civs)

                instructions = (
                    "**🎯 Comment choisir ta civilisation:**\n\n"
                    "1️⃣ **Copie l'emoji** de la civilisation\n"
                    "2️⃣ Clique sur **📝 Choisir ma civilisation**\n"
                    "3️⃣ **Colle l'emoji** dans la fenêtre\n"
                    "4️⃣ Clique sur **✅ Confirmer**\n\n"
                    "💡 **Astuce:** Choisis parmi ta liste!"
                )

                await user.send(instructions, view=selection_view)
                
            except Exception as e:
                failed_users.append(f"<@{player_id}>")
                print(f"❌ Erreur lors de l'envoi de la sélection à {player_id}: {e}")
        
        if failed_users and channel:
            await channel.send(
                f"⚠️ Impossible d'envoyer la phase de sélection à : {', '.join(failed_users)}"
            )
    
    async def _send_final_results(self, channel, game_id: str):
        """Send final results to thread"""
        game = self.get_game(game_id)
        if not game:
            return
        
        weighted_results = game.get("final_settings", {})
        
        # Settings
        settings_msg = f"# 🎮 Résultats Finaux - Partie {game_id}\n\n"
        settings_msg += "## 🎲 Configuration sélectionnée\n\n"
        
        for category, result_data in weighted_results.items():
            selected = result_data["selected"]
            votes_count = result_data["votes"]
            total_votes = sum(votes_count.values())
            winning_votes = votes_count.get(selected, 0)
            settings_msg += f"**{category}**: {selected} ({winning_votes}/{total_votes} votes)\n"
        
        await channel.send(settings_msg)
        
        # Player selections
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
        
        await channel.send(selections_msg)
        
        # Banned civs
        bans_msg = "## 🚫 Civilisations bannies\n\n"
        
        all_bans = {}
        for player_id, bans in game.get("bans", {}).items():
            for ban in bans:
                if ban not in all_bans:
                    all_bans[ban] = []
                all_bans[ban].append(player_id)
        
        if all_bans:
            sorted_bans = sorted(all_bans.items(), key=lambda x: len(x[1]), reverse=True)
            for civ, banners in sorted_bans[:30]:
                emoji = CIV_EMOJI_CONFIG.get(civ, "")
                bans_msg += f"{emoji} **{civ}** - {len(banners)} ban(s)\n"
            
            if len(sorted_bans) > 30:
                bans_msg += f"\n*Et {len(sorted_bans) - 30} autres civilisations bannies...*\n"
        else:
            bans_msg += "*Aucune civilisation bannie*\n"
        
        await channel.send(bans_msg)
