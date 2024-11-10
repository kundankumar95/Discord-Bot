import discord
from discord.ext import commands
import random
import json
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

data_file_path = '/home/kundankarn/discord-football-bot/data.json'

def load_data_from_json():
    try:
        with open(data_file_path, 'r') as file:
            data = json.load(file)
            return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}

def get_user_cards(user_id):
    user_data = None
    for user in data['userA'] + data['userB']:
        if user['user_id'] == str(user_id):
            user_data = user
            break
    if user_data:
        return user_data.get('cards', [])
    else:
        print(f"No data found for user {user_id}")
        return []

data = load_data_from_json()
active_battles = {}

async def send_card_images(user, selected_cards):
    """Send each card as a separate embed."""
    for card in selected_cards:
        embed = discord.Embed(
            title=f"{card.get('name')}",
            description=f"Rating: {card.get('rating')}",
            color=discord.Color.blue()
        )
        image_url = card.get('image_url')
        if image_url:
            embed.set_image(url=image_url)
        await user.send(embed=embed)

async def send_card(user, card_name):
    found_card = None
    for user_data in data.values():
        for player in user_data:
            for card in player["cards"]:
                if card["name"].lower() == card_name.lower():
                    found_card = card
                    break
            if found_card:
                break
        if found_card:
            break

    if not found_card:
        await user.send(f"Sorry, I couldn't find any information for the card '{card_name}'.")
        return

    embed = discord.Embed(
        title=found_card["name"],
        description=f"Rating: {found_card['rating']}\nPrice: {found_card['price']}\nAGR: {found_card['agr']}\nApps: {found_card['APPS']}",
        color=discord.Color.blue()
    )

    image_url = found_card.get("image_url")
    if image_url:
        embed.set_image(url=image_url)

    await user.send(embed=embed)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def battle(ctx: commands.Context, opponent: str):
    try:
        opponent_user = await commands.UserConverter().convert(ctx, opponent)

        userA_id = ctx.author.id
        userB_id = opponent_user.id
        print(f"UserA ID: {userA_id}, UserB ID: {userB_id}")

        userA_cards = get_user_cards(userA_id)
        userB_cards = get_user_cards(userB_id)

        # print(f"UserA cards: {userA_cards}")
        # print(f"UserB cards: {userB_cards}") 


        if len(userA_cards) < 3 or len(userB_cards) < 3:
            await ctx.send("One of the players doesn't have enough cards to battle! Both players need at least 3 cards.")
            return

        bot_selected_A = random.sample(userA_cards, 3)
        bot_selected_B = random.sample(userB_cards, 3)

        battle_data = {
            "userA_id": userA_id,
            "userB_id": userB_id,
            "userA_cards": bot_selected_A,
            "userB_cards": bot_selected_B,
            "status": "pending"
        }
        active_battles[userA_id] = battle_data
        active_battles[userB_id] = battle_data  

        # print(f"Battle data added: {battle_data}")

        active_battles[userA_id] = battle_data

        await ctx.send(f"{ctx.author.mention} challenged {opponent_user.mention} to a battle! Type `!accept` to join.")
        await ctx.author.send(f"Your selected cards: {bot_selected_A}")
        await opponent_user.send(f"Your selected cards: {bot_selected_B}")

    except commands.CommandError as e:
        await ctx.send(f"An error occurred: {e}")
        print(f"Error in battle command: {e}")

@bot.command()
async def accept(ctx):
    """Accept a pending battle and retrieve player card info."""
    user_id = ctx.author.id
    battle_found = False
    battle_data = None

    # print(f"Active Battles: {active_battles}")

    for battle_key, battle in active_battles.items():
        # print(f"Checking battle with UserA ID {battle.get('userA_id')} and UserB ID {battle.get('userB_id')}")
        if battle.get('userB_id') == user_id and battle.get('status') == 'pending':
            battle_found = True
            battle_data = battle
            break

    if battle_found and battle_data:
        # print(f"Battle found for acceptance! UserA ID: {battle_data.get('userA_id')}, UserB ID: {battle_data.get('userB_id')}")

        userA = bot.get_user(battle_data.get("userA_id"))
        userB = bot.get_user(battle_data.get("userB_id"))
        await ctx.send(f"Battle accepted between {userA.mention} and {userB.mention}!")

        await send_card_images(userA, battle_data.get('userA_cards'))
        await send_card_images(userB, battle_data.get('userB_cards'))

        await get_additional_cards(ctx, battle_data)

        del active_battles[battle_key]
    else:
        await ctx.send("No pending battle found.")



async def get_additional_cards(ctx, battle):
    userA_id = battle['userA_id']
    userB_id = battle['userB_id']

    userA_initial_cards = battle['userA_cards']
    userB_initial_cards = battle['userB_cards']

    userA = bot.get_user(userA_id)
    userB = bot.get_user(userB_id)

    await userA.send("Select two additional cards to complete your hand of five.")
    await userB.send("Select two additional cards to complete your hand of five.")

    def check_a(m):
        return m.author.id == userA_id

    def check_b(m):
        return m.author.id == userB_id

    try:
        userA_available_cards = [card['name'] for card in userA_initial_cards]
        await userA.send(f"Available cards: {', '.join(userA_available_cards)}")
        userA_msg1 = await bot.wait_for('message', check=check_a, timeout=1000.0)
        card_name1 = userA_msg1.content.strip()

        
        await send_card(userA, card_name1)
        
        userA_msg2 = await bot.wait_for('message', check=check_a, timeout=1000.0)
        card_name2 = userA_msg2.content.strip()  

        await send_card(userA, card_name2)

        
        userB_available_cards = [card['name'] for card in userB_initial_cards]
        await userB.send(f"Available cards: {', '.join(userB_available_cards)}")
        userB_msg1 = await bot.wait_for('message', check=check_b, timeout=1000.0)
        card_name1_b = userB_msg1.content.strip()

        await send_card(userB, card_name1_b)

        userB_msg2 = await bot.wait_for('message', check=check_b, timeout=1000.0)
        card_name2_b = userB_msg2.content.strip()

        await send_card(userB, card_name2_b)

# working proper ------------------------------------------------------------------------------------------------------------------------------------------
        await ctx.send(f"Both players have selected their cards. Let the battle begin!")
        await start_battle(ctx, battle, userA_initial_cards, userB_initial_cards, card_name1, card_name2, card_name1_b, card_name2_b)

    except asyncio.TimeoutError:
        await ctx.send("A user took too long to select additional cards.")

async def start_battle(ctx, battle, userA_initial_cards, userB_initial_cards, card_name1, card_name2, card_name1_b, card_name2_b):
    await ctx.send(f"Both players have selected their cards. Let the battle begin!")

    def get_card_by_name(card_name, user_cards):
        for card in user_cards:
            if card['name'] == card_name:
                return card
        return None

    if isinstance(userA_initial_cards[0], str): 
        userA_initial_cards = [get_card_by_name(card_name, battle['userA'][0]['cards']) for card_name in userA_initial_cards]
    
    if isinstance(userB_initial_cards[0], str): 
        userB_initial_cards = [get_card_by_name(card_name, battle['userB'][0]['cards']) for card_name in userB_initial_cards]

    
    selected_card_a1 = get_card_by_name(card_name1, userA_initial_cards)
    selected_card_a2 = get_card_by_name(card_name2, userA_initial_cards)
    selected_card_b1 = get_card_by_name(card_name1_b, userB_initial_cards)
    selected_card_b2 = get_card_by_name(card_name2_b, userB_initial_cards)

    userA_hand = userA_initial_cards + [selected_card_a1, selected_card_a2]
    userB_hand = userB_initial_cards + [selected_card_b1, selected_card_b2]

    # print("-"*125)
    # print(userA_hand, type(userA_hand))
    # print("-" * 100)
    # print(userB_hand, type(userB_hand))
    # print("-"*125)

    await start_battle_rounds(ctx, userA_hand, userB_hand, battle)


async def start_battle_rounds(ctx, userA_hand, userB_hand, battle):
    # print("*"*125)
    # print(userA_hand, type(userA_hand))
    # print("*" * 100)
    # print(userB_hand, type(userB_hand))
    # print("*"*125)
    userA = bot.get_user(battle['userA_id'])
    userB = bot.get_user(battle['userB_id'])

    for round_num in range(1, 6):
        await ctx.send(f"Round {round_num} begins!")

        cards_message_a = "\n".join([f"{card['name']} - {card['rating']} rating, {card['APPS']} apps, {card['agr']} agr, {card.get('SV', 'N/A')} SV, {card.get('G/A', 'N/A')} G/A, {card.get('TW', 'N/A')} TW" for card in userA_hand if card is not None])

        cards_message_b = "\n".join([f"{card['name']} - {card['rating']} rating, {card['APPS']} apps, {card['agr']} agr, {card.get('SV', 'N/A')} SV, {card.get('G/A', 'N/A')} G/A, {card.get('TW', 'N/A')} TW" for card in userB_hand if card is not None])
        
        await userA.send(f"Choose a card and a stat (Rating, APPS, AGR, SV, G/A, TW):\n{cards_message_a}")
        await userB.send(f"Choose a card (same stat will be used for comparison for User B):\n{cards_message_b}")


        valid_stats = ['rating', 'apps', 'agr', 'sv', 'g/a', 'tw']
        def check_a(m):
            if m.author.id == userA.id:
                parts = m.content.split()
                
                if len(parts) >= 2:  
                    stat_name = parts[-1].lower()
                    card_name = ' '.join(parts[:-1]).lower() 
                    
                    if any(card['name'].lower() == card_name for card in userA_hand) and stat_name in valid_stats:
                        return True
                    else:
                        m.channel.send("Invalid input! Please enter the card name followed by the stat (e.g., 'Alexander Isak rating').")
            return False

        
        def check_b(m):
            if m.author.id == userB.id:
                card_name = m.content.strip().lower() 
                if any(card['name'].lower() == card_name for card in userB_hand):
                    return True
                else:
                    m.channel.send("Invalid input! Please enter the card name (e.g., 'Bruno Guimaraes').")
            return False


        try:
            message_a = await bot.wait_for('message', check=check_a, timeout=100.0)
            message_b = await bot.wait_for('message', check=check_b, timeout=100.0)
            message_a_content = message_a.content.strip().split()

            if len(message_a_content) < 2:
                await ctx.send("Please provide both the card name and stat.")
                return

            if len(message_a_content) == 2:
                card_a, stat_a = message_a_content
            elif len(message_a_content) == 3:
                card_a = f"{message_a_content[0]} {message_a_content[1]}" 
                stat_a = message_a_content[2]
            else:
                await ctx.send("Invalid input. Please enter either two or three words.")
                return
            card_b = message_b.content.strip()

            selected_card_a = next(card for card in userA_hand if card['name'] == card_a)
            selected_card_b = next(card for card in userB_hand if card['name'] == card_b)

            stat_value_a = selected_card_a[stat_a]  
            stat_value_b = selected_card_b[stat_a] 

            userA_score = 0
            userB_score = 0
            if stat_value_a > stat_value_b:
                round_winner = "User A"
                userA_score += 1  
                userB_hand.remove(selected_card_b)
            else:
                round_winner = "User B"
                userB_score += 1  
                userA_hand.remove(selected_card_a)


            await ctx.send(f"Round {round_num} winner: {round_winner}")

        except asyncio.TimeoutError:
            await ctx.send("A user took too long to select a card.")
            return

    await determine_final_winner(ctx, battle)


    
async def determine_final_winner(ctx, userA_score, userB_score, userA, userB):
    if userA_score > userB_score:
        final_winner = userA
    elif userB_score > userA_score:
        final_winner = userB
    else:
        final_winner = "Draw"
    
    await ctx.send(f"The final winner is: {final_winner}")

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
