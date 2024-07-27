from nextcord.ext.commands import Bot
from nextcord import Intents, Embed
from nextcord.ext.commands import Context
import os
from tts import TextToSpeech
from db_connector import Server, User, QuotaTracker
from voice_list import *

BOT_PREFIX = "tts!"
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

bot = Bot(
    command_prefix=BOT_PREFIX,
    intents=Intents.all(),
    owner_id=343517933256835072,
    help_command=None,
)


@bot.event
async def on_ready():
    print("i woke up")


# make ping command usable only by admins
@bot.command()
async def ping(ctx: Context):
    await ctx.reply("pong")


# admin only command
@bot.command()
async def check_quota(ctx: Context):

    if not ctx.author.id == bot.owner_id:
        await ctx.reply("You do not have permission to use this command")
        return

    msg = await ctx.reply("Checking quota")

    used_characters: int = await QuotaTracker.get_quota_usage()

    await msg.edit(content=f"Characters used: {used_characters}")


@bot.command()
async def help(ctx: Context):
    embed = Embed(title="Text To Speech Bot", color=0x00FF00)
    embed.description = (
        "Prefix: `tts!`\n"
        + "All commands:\n\n"
        + "`tts!help` - Shows this message\n"
        + "`tts!ping` - Tests if the bot is online and responsive\n\n"
        + "`tts!get languages` - Shows the supported language codes\n"
        + "`tts!get voices <language_code>` - Shows the supported voices for a language\n\n"
        + "`tts!set user voice <voice>` - Sets the voice of user for that server only, first priority when generating audio\n"
        + "`tts!set user speed <speed>` - Sets the speed of user for that server only, first priority when generating audio\n\n"
        + "`tts!set server voice <voice>` - Sets the default voice of the server, second priority when generating audio(requires admin permissions)\n\n"
        + "`tts!set default voice <voice>` - Sets the default voice for the user, lowest priority when generating audio\n"
        + "`tts!set default speed <speed>` - Sets the default speed for the user, lowest priority when generating audio"
    )
    await ctx.reply(embed=embed)


@bot.group()
async def get(ctx: Context):
    if ctx.invoked_subcommand is None:
        await ctx.reply(
            "Please specify a sub command.\nAvailable sub commands:\n\n"
            + "`languages`\n"
            + "`voices`"
        )


@get.command(name="languages")
async def get_languages(ctx: Context):
    embed = Embed(title="Supported Languages", color=0x00FF00)
    msg = ""
    for language in language_list:
        msg += f"{language['discord_emoji']}{language['country']}|{language['language']} - `{language['language_code']}`\n"
        embed.description = msg
    embed.set_footer(
        text="Use tts!get voices <language_code> to see the supported voices for a language"
    )
    await ctx.reply(embed=embed)


@get.command(name="voices")
async def get_voices(ctx: Context, language_code: str = None):

    if language_code is None:
        await ctx.reply(
            "Please provide a language code. Use tts!get languages to see the supported language codes."
        )
        return

    if language_code not in language_voice_tree:
        await ctx.reply(
            "Invalid language code. Use tts!get languages to see the supported language codes."
        )
        return

    em = Embed(title="Supported Voices for " + language_code, color=0x00FF00)
    msg = ""

    for voice in language_voice_tree[language_code]:
        msg += f"{voice}\n"

    em.description = msg
    await ctx.reply(embed=em)


@bot.group()
async def set(ctx: Context):
    if ctx.invoked_subcommand is None:
        await ctx.reply(
            "Please specify a sub command.\nAvailable sub commands:\n\n"
            + "`user`\n"
            + "`server`\n"
            + "`default`"
        )


@set.group(name="default")
async def set_default(ctx: Context):
    if ctx.invoked_subcommand is None:
        await ctx.reply(
            "Please specify a sub command.\nAvailable sub commands:\n\n"
            + "`voice`\n"
            + "`speed`"
        )


@set_default.command(name="voice")
async def set_default_voice(ctx: Context, default_voice: str):

    lang = get_language_code_of_voice(default_voice)

    if lang not in language_voice_tree:
        await ctx.reply(
            "Invalid voice. Use tts!get voices <language_code> to see the supported voices for a language"
        )
        return
    # if the voice is not in voice tree than it is invalid

    operation = await User.modify_user(
        user_id=ctx.author.id, default_voice=default_voice, default_lang=lang
    )
    if operation:
        await ctx.reply(f"Default voice set to `{default_voice}`")
    else:
        await ctx.reply("Failed to set default voice")


@set_default.command(name="speed")
async def set_default_speed(ctx: Context, default_speed: float):

    if not 0.25 <= default_speed <= 4:
        await ctx.reply("Invalid speed. Speed must be between 0.25 and 4")
        return

    operation = await User.modify_user(
        user_id=ctx.author.id, default_speed=default_speed
    )
    if operation:
        await ctx.reply(f"Default speed set to `{default_speed}`")
    else:
        await ctx.reply("Failed to set default speed")


@set.group(name="server")
async def set_server(ctx: Context):
    if ctx.invoked_subcommand is None:
        await ctx.reply(
            "Please specify a sub command.\nAvailable sub commands:\n\n" + "`voice`"
        )


@set_server.command(name="voice")
async def set_server_voice(ctx: Context, server_voice: str):

    is_permitted = False

    if ctx.author.guild_permissions.administrator:
        is_permitted = True

    elif ctx.author.id == bot.owner_id:
        is_permitted = True

    if not is_permitted:
        await ctx.reply("You do not have permission to use this command")
        return

    lang = get_language_code_of_voice(server_voice)

    if lang not in language_voice_tree:
        await ctx.reply(
            "Invalid voice. Use tts!get voices <language_code> to see the supported voices for a language"
        )
        return

    operation = await Server.modify_server(
        server_id=ctx.guild.id, voice=server_voice, lang=lang
    )
    if operation:
        await ctx.reply(f"Server voice set to `{server_voice}`")
    else:
        await ctx.reply("Failed to set server voice")


@set.group(name="user")
async def set_user(ctx: Context):
    if ctx.invoked_subcommand is None:
        await ctx.reply(
            "Please specify a sub command.\nAvailable sub commands:\n\n"
            + "`voice`\n"
            + "`speed`"
        )


@set_user.command(name="voice")  # implement this
async def set_user_voice(ctx: Context, user_voice: str):

    lang = get_language_code_of_voice(user_voice)

    if lang not in language_voice_tree:
        await ctx.reply(
            "Invalid voice. Use tts!get voices <language_code> to see the supported voices for a language"
        )
        return

    operation = await User.modify_user(
        user_id=ctx.author.id,
        server_voice=user_voice,
        server_lang=lang,
        server_id=ctx.guild.id,
    )
    if operation:
        await ctx.reply(f"User voice set to `{user_voice}`")
    else:
        await ctx.reply("Failed to set user voice")


@set_user.command(name="speed")  # implement this
async def set_user_speed(ctx: Context, user_speed: float):

    if not 0.25 <= user_speed <= 4:
        await ctx.reply("Invalid speed. Speed must be between 0.25 and 4")
        return

    operation = await User.modify_user(
        user_id=ctx.author.id, server_speed=user_speed, server_id=ctx.guild.id
    )

    if operation:
        await ctx.reply(f"User speed set to `{user_speed}`")
    else:
        await ctx.reply("Failed to set user speed")


bot.add_cog(TextToSpeech(bot))

bot.run(TOKEN)
