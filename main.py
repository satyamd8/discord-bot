import os
import json
import random
import requests
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord import app_commands

import aiohttp


#load env variables
load_dotenv()
TOKEN = os.getenv('TOKEN')
WEATHER_API = os.getenv('WEATHER')
ICON = os.getenv('ICON')
GIF1 = os.getenv('GIF1')
GIF2 = os.getenv('GIF2')
GIF3 = os.getenv('GIF3')
GIF4 = os.getenv('GIF4')

LOG_FILE = "channels.json"





#load json file (for channel ids)
def load_channels():
    try:
        with open(LOG_FILE, "r") as f:
            return {str(k): v for k, v in json.load(f).items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

log_channels = load_channels()

def save_channels():
    with open(LOG_FILE, "w") as f:
        json.dump(log_channels, f)





#bot client
class Client(commands.Bot):
#init
    async def on_ready(self):
        print(f'{self.user} has arrived!')

        try:
            guild = discord.Object(id=775208915930447883)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

#log and hi
    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content.startswith('hello'):
            await message.channel.send(f'hi there {message.author.mention}')
        elif "dumb" in message.content:
            await message.channel.send(GIF1)
        elif "mars" in message.content.lower():
            await message.channel.send(GIF4)

        await self.process_commands(message)


#show edits
    async def on_message_edit(self, before, after):
        log = log_channels.get(str(before.guild.id))

        if self.user:
            return

        if not log:
            print("A log channel hasn't been set for this server yet")
            return
        
        log_channel = before.guild.get_channel(log)
        if not log_channel:
            print("Log channel is unavailable or deleted")
            return
        
        time_before = before.created_at.strftime("**%I:%M:%S %p** (%m-%d-%Y)")
        time_after = after.edited_at.strftime("**%I:%M:%S %p** (%m-%d-%Y)")

        embed=discord.Embed(description=before.author.mention, color=discord.Color.random())
        embed.add_field(name="Before: ", value= f'{before.content} \n{time_before}', inline=False)
        embed.add_field(name="After: ", value= f'{after.content} \n{time_after}', inline=False)
        embed.set_author(name=before.author.display_name, icon_url=before.author.avatar.url)
        await log_channel.send(embed=embed)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.voice_states = True
client = Client(command_prefix=";", intents=discord.Intents.all())


GUILD_ID = discord.Object(id=775208915930447883)







# MOD COMMANDS


#hello command
@client.tree.command(name="hello", description="Say hello", guild=GUILD_ID)
async def sayHello(interaction:discord.Interaction):
    await interaction.response.send_message("Hello")

#set channel
@client.tree.command(name="set", description="Set channel for logs", guild=GUILD_ID)
async def setChannel(interaction:discord.Interaction, channel: discord.TextChannel):
    log_channels[str(interaction.guild_id)] = channel.id
    save_channels()
    await interaction.response.send_message(f'Logs channel set to {channel.mention}')





#kick and ban
@client.tree.command(name="kick", description="Kick someone from the server", guild=GUILD_ID)
@commands.has_permissions(kick_members=True)
async def kick(interaction:discord.Interaction, member: discord.Member, reason: str="nothing"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f'{member.display_name} was kicked for {reason}')

@client.tree.command(name="ban", description="Ban someone from the server", guild=GUILD_ID)
@commands.has_permissions(ban_members=True)
async def ban(interaction:discord.Interaction, member: discord.Member, reason: str="nothing"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f'{member.display_name} was banned for {reason}')

@kick.error
@ban.error
async def missingPermissions(interaction:discord.Interaction, error):
    if isinstance(error, commands.MissingPermissions):
        await interaction.response.send_message("You don't have the right permissions")


@client.command()
async def ping(ctx):
    await ctx.send("Pong!")

#join and leave
@client.command(name="join", description="Join a voice channel", guild=GUILD_ID)
async def join(ctx):
    channel = ctx.author.voice.channel
    if channel:
        await channel.connect()
    else:
        await ctx.send("You need to be in a voice channel to use this command.", ephemeral=True)

@client.command(name="leave", description="Leave a voice channel", guild=GUILD_ID)
async def leave(ctx):
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.disconnect()
    else:
        await ctx.send("I'm not in a voice channel", ephemeral=True)





# FUN COMMANDS

#echo command
@client.tree.command(name="say", description="Echo your input", guild=GUILD_ID)
async def sayEcho(interaction:discord.Interaction, echo: str):
    await interaction.response.send_message(echo)

#idiot command
@client.tree.command(name="idiot", description="Use when someone says something so stupid", guild=GUILD_ID)
async def sayEcho(interaction:discord.Interaction):
    await interaction.response.send_message(GIF2)

#wow command
@client.tree.command(name="wow", description="Use when you can't believe someone said that", guild=GUILD_ID)
async def sayEcho(interaction:discord.Interaction):
    await interaction.response.send_message(GIF3)

#embed command
@client.tree.command(name="embed", description="Embed a link", guild=GUILD_ID)
async def embed(interaction:discord.Interaction, title: str, link: str):
    embed = discord.Embed(title=title, url=link, color=discord.Color.random())
    embed.set_thumbnail(url=ICON)
    await interaction.response.send_message(embed=embed)

#roll command
@client.tree.command(name="roll", description="Roll a random number, enter a max number", guild=GUILD_ID)
async def diceRoll(interaction:discord.Interaction, sides: int):
    result = random.randint(0, sides)
    await interaction.response.send_message(f'You rolled: {result}')


phrases = [
    "Yes",
    "No",
    "Ask again",
    "Without a doubt",
    "Not a chance LMAO",
    "Most likely",
    "Probably not",
    "Concentrate and ask again",
    "My sources are telling me no",
    "Leaning towards yes"
]

#8ball command
@client.tree.command(name="8ball", description="Ask the magic 8-ball a yes/no question, any question", guild=GUILD_ID)
async def ball(interaction:discord.Interaction, question: str):
    answer = random.choice(phrases)

    embed = discord.Embed(
        title="🎱 The Magic 8-Ball",
        description=f"**{interaction.user.mention} asked:**\n*\"{question}\"*",
        color=discord.Color.purple()
    )
    embed.add_field(name="🔮 Answer:", value=f"**{answer}**", inline=False)
    embed.set_footer(text="Ask again later... or not 🤷‍♂️")
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.response.send_message(embed=embed)

#rock, paper, scissors

tools = ["Rock", "Paper", "Scissors"]
win_conditions = {
    "Rock": "Scissors",
    "Paper": "Rock",
    "Scissors": "Paper"
}
rps_emoji = {
    "Rock":"🪨",
    "Paper":"📄",
    "Scissors":"✂️"
}

@client.tree.command(name="rps", description="Play Rock, Paper, Scissors with the bot.", guild=GUILD_ID)
async def rps(interaction:discord.Interaction, choice: str):
    choice = choice.capitalize()
    answer = random.choice(tools)

    if choice not in tools:
        await interaction.response.send_message("Please select either **Rock, Paper, or Scissors**")
    
    if choice == answer:
        result = "It's a tie!"
    elif win_conditions[choice] == answer:
        result = "You win! 🎉"
    else:
        result = "You lose! 💩"

    embed = discord.Embed(title="🪨📄✂️ Rock, Paper, Scissors✂️📄🪨", color=discord.Color.dark_gold())

    embed.add_field(name="Your Choice:", value=f'{choice} {rps_emoji[choice]}', inline=True)
    embed.add_field(name="Bot's Choice:", value=f'{answer} {rps_emoji[answer]}', inline=True)
    embed.add_field(name="Result:", value=f'**{result}**', inline=False)

    await interaction.response.send_message(embed=embed)

#meme command
@client.tree.command(name="meme", description="Get a random meme", guild=GUILD_ID)
async def randomMeme(interaction:discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with interaction.channel.typing():
            async with session.get("https://meme-api.com/gimme") as response:
                data = await response.json()
                await interaction.response.send_message(data['url'])

#weather command
@client.tree.command(name="weather", description="Get the weather from a city", guild=GUILD_ID)
async def getWeather(interaction:discord.Interaction, city: str):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': city,
        'appid': WEATHER_API,
        'units': 'imperial'
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        weather_desc = data['weather'][0]['description'].title()
        temp = data['main']['temp']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']

        embed = discord.Embed(title=f"Weather in **{city.title()}**", color=discord.Color.blue())
        embed.add_field(name="Description", value=weather_desc, inline=False)
        embed.add_field(name="Temperature", value=f"{temp}°F", inline=True)
        embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
        embed.add_field(name="Wind Speed", value=f"{wind_speed} mph", inline=True)
        embed.set_footer(text="Powered by OpenWeather API")

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"Couldn't find weather for '{city}'. Please check the city name and try again.")

client.run(TOKEN)