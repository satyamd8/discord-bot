import os
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord import app_commands

import requests

import random

load_dotenv()
TOKEN = os.getenv('TOKEN')
WEATHER_API = os.getenv('WEATHER')

class Client(commands.Bot):
    async def on_ready(self):
        print(f'{self.user} has arrived!')

        try:
            guild = discord.Object(id=775417392489824267)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

#log and hi
    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content.startswith('hello'):
            await message.channel.send(f'hi there {message.author}')
#show edits
    async def on_message_edit(self, before, after):
        await before.channel.send(f'{before.author.display_name} `(before): {before.content}`')
        await after.channel.send(f'{after.author.display_name} `(after): {after.content}`')


intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)


GUILD_ID = discord.Object(id=775417392489824267)

#hello command
@client.tree.command(name="hello", description="Say hello", guild=GUILD_ID)
async def sayHello(interaction:discord.Interaction):
    await interaction.response.send_message("Hello")




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



#echo command
@client.tree.command(name="say", description="Echo your input", guild=GUILD_ID)
async def sayEcho(interaction:discord.Interaction, echo: str):
    await interaction.response.send_message(echo)

#roll command
@client.tree.command(name="roll", description="Roll a random number, enter a max number", guild=GUILD_ID)
async def diceRoll(interaction:discord.Interaction, sides: int):
    result = random.randint(0, sides)
    await interaction.response.send_message(f'You rolled: {result}')

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

        embed = discord.Embed(title=f"Weather in {city.title()}", color=discord.Color.blue())
        embed.add_field(name="Description", value=weather_desc, inline=False)
        embed.add_field(name="Temperature", value=f"{temp}°F", inline=True)
        embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
        embed.add_field(name="Wind Speed", value=f"{wind_speed} m/s", inline=True)
        embed.set_footer(text="Powered by OpenWeather")

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ Couldn't find weather for '{city}'. Please check the city name and try again.")

client.run(TOKEN)