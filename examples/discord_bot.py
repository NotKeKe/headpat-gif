"""A minimal discord.py bot that pets whatever image it is pointed at.

    export DISCORD_TOKEN=...
    uv run --extra discord python examples/discord_bot.py

``petpet()`` returns an ``io.BytesIO`` subclass, so the GIF never has to touch
the disk before it is uploaded.
"""

from __future__ import annotations

import io
import os
import urllib.request

import discord
from discord.ext import commands

from petpet_gif import petpet

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "petpet-gif-example"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read()


@bot.event
async def on_ready() -> None:
    print(f"logged in as {bot.user}")


@bot.command()
async def pet(ctx: commands.Context, *, target: str | None = None) -> None:
    """!pet <image url or attachment> - pat the target on the head."""
    if target and target.startswith("http"):
        payload: bytes | io.BytesIO = fetch(target)
    elif ctx.message.attachments:
        payload = io.BytesIO(await ctx.message.attachments[0].read())
    else:
        await ctx.reply("give me an image url or attach one")
        return

    # duration is the total length of the GIF, speed is the playback rate.
    gif = petpet(payload, duration=2.0, speed=1.5)
    await ctx.reply(file=discord.File(gif, filename="petpet.gif"))


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("set DISCORD_TOKEN first")
    bot.run(token)
