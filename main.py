import os
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord import app_commands

import random

load_dotenv()
TOKEN = os.getenv('TOKEN')

class Client(commands.Bot):
    async def on_ready(self):
        print(f'{self.user} has arrived!')

        try:
            guild = discord.Object(id=775417392489824267)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content.startswith('hello'):
            await message.channel.send(f'hi there {message.author}')

    async def on_message_edit(self, before, after):
        await before.channel.send(f'{before.author.display_name} `(before): {before.content}`')
        await after.channel.send(f'{after.author.display_name} `(after): {after.content}`')


intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)


GUILD_ID = discord.Object(id=775417392489824267)

@client.tree.command(name="hello", description="Say hello", guild=GUILD_ID)
async def sayHello(interaction:discord.Interaction):
    await interaction.response.send_message("Hello")

@client.tree.command(name="say", description="Echo your input", guild=GUILD_ID)
async def sayEcho(interaction:discord.Interaction, echo: str):
    await interaction.response.send_message(echo)

@client.tree.command(name="roll", description="Roll a random number, enter a max number", guild=GUILD_ID)
async def diceRoll(interaction:discord.Interaction, sides: int):
    result = random.randint(0, sides)
    await interaction.response.send_message(f'You rolled: {result}')

client.run(TOKEN)