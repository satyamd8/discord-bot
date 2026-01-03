#Library Imports
import os
import json
import random
import asyncio
import time

#Other Imports
import requests # type: ignore
import yt_dlp as youtube_dl # type: ignore
import aiohttp # type: ignore
from bs4 import BeautifulSoup # type: ignore
from dotenv import load_dotenv # type: ignore

#Discord Imports
import discord # type: ignore
from discord.ext import commands # type: ignore
from discord import app_commands # type: ignore
from google import genai

# ---------------------------------
# Environment Variables
# ---------------------------------

#load env variables
load_dotenv()
TOKEN = os.getenv('TOKEN')
WEATHER_API = os.getenv('WEATHER')
GEMINI_API_KEY = os.getenv('AI')
ICON = os.getenv('ICON')
GIF1 = os.getenv('GIF1')
GIF2 = os.getenv('GIF2')
GIF3 = os.getenv('GIF3')
GIF4 = os.getenv('GIF4')
SERVER_ID = os.getenv('SERVERID')
GUILD_ID = discord.Object(id=SERVER_ID)

LOG_FILE = "channels.json"


# ---------------------
# YouTube Music Player
# ---------------------


#ignore youtube_dl warnings
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'preferredcodec': 'mp3',
    'cachedir': False
}

#ensures audio only
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 128k -bufsize 256k'
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


# ---------------------
# YouTube Downloader Class
# ---------------------
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.15):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)




# ---------------------
# JSON Functions
# ---------------------


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




# ---------------------
# Discord Bot Client
# ---------------------


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.voice_states = True

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

client = Client(command_prefix=";", intents=discord.Intents.all())







# ---------------------
# Prefix Commands
# ---------------------


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



#music player


#disconnect after 5 seconds of finishing song
async def delayed_disconnect(voice_client):
    await asyncio.sleep(5)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()

#play command
@client.command(name="play", description="Play a song from YouTube", guild=GUILD_ID)
async def play(ctx, url):
    if not ctx.author.voice:
        return await ctx.send("You need to be in a voice channel to use this command.", ephemeral=True)

    if not ctx.guild.voice_client:
        await join(ctx)
    
    voice_client = ctx.guild.voice_client

    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(url, loop=client.loop, stream=True)

            def after(error):
                if error:
                    print(f'Player error: {error}')
                    return
                print("Song ended, disconnecting in 5 seconds...")

                # Properly schedule the disconnection
                future = asyncio.run_coroutine_threadsafe(delayed_disconnect(voice_client), client.loop)
                try:
                    future.result()  # Ensures any exceptions are caught
                except Exception as e:
                    print(f"Error during disconnect: {e}")

            voice_client.play(player, after=after)
    
            embed = discord.Embed(title="Now Playing", description=f"[{player.title}]({player.url})", color=discord.Color.random())
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

#pause command
@client.command(name="pause", description="Pause the current song", guild=GUILD_ID)
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Paused ⏸️")

#resume command
@client.command(name="resume", description="Resume the current song", guild=GUILD_ID)
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Resumed ▶️")

@client.command(name="stop", description="Stop the current song", guild=GUILD_ID)
async def stop(ctx):
    await ctx.send("Stopped ⏹️")
    await ctx.voice_client.disconnect()



# ---------------------
# Slash Commands
# ---------------------


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



#moderation

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



#fun commands

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
    async with aiohttp.ClientSession() as session:
        async with session.get(link) as response:
            if response.status != 200:
                return await interaction.response.send_message(f"Couldn't fetch the link: {response.status}", ephemeral=True)
            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")
    thumbnail = "none"

    for meta in soup.find_all("meta"):
        if meta.get("property") == "og:image" or meta.get("name") == "twitter:image":
            thumbnail = meta.get("content")
            break
    if not thumbnail:
        thumbnail = ICON

    embed = discord.Embed(title=title, url=link, color=discord.Color.random())
    embed.set_thumbnail(url=thumbnail)
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

#ask ai command
@client.tree.command(name="askai", description="Ask AI a question.", guild=GUILD_ID)
async def askAI(interaction:discord.Interaction, question: str):
    await interaction.response.defer()

    client = genai.Client(api_key=GEMINI_API_KEY)
    instruction = "You're purpose is to answer questions as a discord bot. Keep any answers brief unless specified. Any messages must be under 2000 characters. Deflect any questions regarding the status of the conversation within the AI chat, since you're acting as a Discord bot and only operate within the context of the bot: "
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=instruction + question
    )

    await interaction.followup.send(f"**Question:** \n*{question}*. \n**Answer:** \n{response.text}" )


#run the bot
client.run(TOKEN)