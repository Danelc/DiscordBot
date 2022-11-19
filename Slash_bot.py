# from optparse import Option
import feedparser
import discord
from discord import app_commands
from discord.ext import tasks
from NyaaReq import NyaaReq
import logging
import os
import time
import lavaplayer
import json
import random
import datetime
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

DEFAULT_GUILD_ENABLE = discord.Object(id=os.getenv("Guild_id"))
TOKEN = os.getenv("DISCORD_TOKEN")  # The bot token.
trollRoll = 10  # The 1 to trollroll chance to get a troll music when playing for example if equals to 10 the cahnce is 1 in 10 to get a troll, set to 0 to disable
DefaultPresence = 'boku no pico'

LOG = logging.getLogger("discord.bot")

troll_users_links = {
    353219254641885184: "https://www.youtube.com/watch?v=Sxe9qZ-KDHY",  # shauli
    320501259205607425: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # uriel
    134769648234266624: "https://www.youtube.com/watch?v=5EXFilTUiko",  # Dan
    256448898925723650: "https://www.youtube.com/watch?v=-LPlUYbabqk",  # yoram
    319920206296121344: "https://www.youtube.com/watch?v=oItK1u07Qt0",  # doron
}


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents, enable_debug_events=True)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=DEFAULT_GUILD_ENABLE)
        await self.tree.sync(guild=DEFAULT_GUILD_ENABLE)


bot = MyClient(intents=discord.Intents.all())

lavalink = lavaplayer.Lavalink(
    host="localhost",  # Lavalink host
    port=6969,  # Lavalink port
    password="MustAnswerMeTheseQuestionsThree",  # Lavlink password MustAnswerMeTheseQuestionsThree
)


@bot.event
async def on_ready():
    lavalink.set_user_id(bot.user.id)
    lavalink.set_event_loop(bot.loop)
    LOG.info("Logged in as %s", bot.user.name)
    lavalink.connect()
    hour_loop.start()


@bot.tree.command(name="ping", description="Get the latency of the bot")
async def ping(interaction: discord.Interaction):
    start = time.time()
    await interaction.response.send_message(
        "Pong!\nGateway: `%dms`\nLatency: `%dms`"
        % (round(bot.latency * 1000),
           round((time.time() - start) * 1000))
    )


@bot.tree.command(name="help", description="Get list of the commands of the bot")
async def help(interaction: discord.Interaction):
    commands = bot.tree.get_commands(guild=interaction.guild)
    embed = discord.Embed(title="Faggy Help", description="", color=interaction.user.color or discord.Color.random())
    embed.description = "\n".join(f"`/{command.name}`: {command.description}" for command in commands)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="join", description="Join a voice channel")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("You are not in a voice channel!", ephemeral=True)
        return
    await interaction.guild.change_voice_state(
        channel=interaction.user.voice.channel, self_deaf=True, self_mute=False
    )
    await lavalink.wait_for_connection(interaction.guild.id)
    await interaction.response.send_message("Joined the voice channel.shalom lachem")


@bot.tree.command(name="leave", description="Leave the voice channel")
async def leave(interaction: discord.Interaction):
    try:
        await interaction.guild.change_voice_state(channel=None)
        await lavalink.wait_for_remove_connection(interaction.guild.id)
        await interaction.response.send_message("Left the voice channel.bye tamut")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=DefaultPresence))
    except:
        await interaction.response.send_message("IM NOT IN A CHANNEL ARE YOU RETARDED?")


@bot.tree.command(name="search", description="Search for a song")
@app_commands.describe(query="Search for a song")
async def search(interaction: discord.Interaction, *, query: str):
    results = await lavalink.auto_search_tracks(query)
    if not results:
        await interaction.response.send_message("No results found.")
        return
    embed = discord.Embed(title="Search results for `%s`" % query)
    results = results if isinstance(results, list) else results.tracks
    for result in results:
        embed.add_field(
            name=result.title,
            value="[%s](%s)" % (result.author, result.uri),
            inline=False,
        )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="play", description="Play a song")
@app_commands.describe(query="The song to play")
async def play(interaction: discord.Interaction, *, query: str):
    troll = False
    await interaction.response.defer()  # The auto search in the next line might take more then 3 soconds that are allowed until response and thus the defer
    if random.randint(1, trollRoll) == 1 and not trollRoll == 0:
        troll = True
        if interaction.user.id in troll_users_links:
            tracks = await lavalink.auto_search_tracks(troll_users_links[interaction.user.id])
        else:
            tracks = await lavalink.auto_search_tracks(query)
    else:
        tracks = await lavalink.auto_search_tracks(query)

    if not interaction.guild.voice_client:
        if not interaction.user.voice:
            await interaction.followup.send("You are not in a voice channel!", ephemeral=True)
            return
        await interaction.guild.change_voice_state(channel=interaction.user.voice.channel, self_deaf=True,
                                                   self_mute=False)
        await lavalink.wait_for_connection(interaction.guild.id)

    if not tracks:
        return await interaction.followup.send("No faggy results found.")
    elif isinstance(tracks, lavaplayer.TrackLoadFailed):
        await interaction.followup.send("Error loading track, Try again later.\n```%s```" % tracks.message)
        return
    elif isinstance(tracks, lavaplayer.PlayList):

        # await interaction.response.send_message("Adding playlist, Please wait...")

        await lavalink.add_to_queue(
            interaction.guild.id, tracks.tracks, interaction.user.id
        )
        totalms = 0
        for track in tracks.tracks:  # Adds up all the lengths of all the tracks in the playlist in milliseconds
            totalms = totalms + track.length

        await interaction.followup.send(
            "Playlist {} Added to queue, with {} tracks and a total length of {}".format(
                tracks.name, len(tracks.tracks), length_format(totalms)
            )
        )
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name=tracks.tracks[0].title))
        return

    if troll:
        onepiece = await lavalink.auto_search_tracks(query)
        if isinstance(onepiece, lavaplayer.PlayList):

            totalms = 0
            for track in onepiece.tracks:  # Adds up all the lengths of all the tracks in the playlist in milliseconds
                totalms = totalms + track.length

            await interaction.followup.send(
                "Playlist {} Added to queue, with {} tracks and a total length of {} <:dolanort:571384764389392430>".format(
                    onepiece.name, len(onepiece.tracks), length_format(totalms)
                )
            )
            return
        url = onepiece[0].uri
        lent = length_format(onepiece[0].length) + " <:dolanort:571384764389392430>"
    else:
        url = tracks[0].uri
        lent = length_format(tracks[0].length)
    if await lavalink.queue(interaction.guild.id):
        respon = f"Added to queue: {url} , with a length of {lent}"
    else:
        respon = f"Now playing: {url} , with a length of {lent}"
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=tracks[0].title))

    await interaction.followup.send(respon)
    # if await len(lavalink.queue(interaction.guild.id))==0:#update the presence only if the added song is the only song (if there was something playing there is no need to update the persence)

    await lavalink.play(interaction.guild.id, tracks[0], interaction.user.id)


@bot.tree.command(name="pause", description="Pause the current track")
async def pause(interaction: discord.Interaction):
    if await is_queue(interaction.guild_id):
        await lavalink.pause(interaction.guild.id, True)
        await interaction.response.send_message("Paused the track.")
    else:
        await interaction.response.send_message("Nothing to pause at the moment.",ephemeral=True)


@bot.tree.command(name="resume", description="Resume the track")
async def resume(interaction: discord.Interaction):
    if await is_queue(interaction.guild_id):
        await lavalink.pause(interaction.guild.id, False)
        await interaction.response.send_message("Resumed the track.")
    else:
        await interaction.response.send_message("Nothing to resume at the moment.",ephemeral=True)


@bot.tree.command(name="stop", description="Stop the music!")
async def stop(interaction: discord.Interaction):
    # if len(await lavalink.queue(interaction.guild.id))>0:
    if await is_queue(interaction.guild_id):
        await interaction.response.send_message("Stopped the track.")
        await lavalink.stop(interaction.guild.id)
        return
    else:
        await interaction.response.send_message("No Track is playing to stop stupid.",ephemeral=True)


@bot.tree.command(name="skip", description="Skip the current track")
async def skip(interaction: discord.Interaction):
    if await is_queue(interaction.guild_id):
        queue = await lavalink.queue(interaction.guild.id)
        # if queue:
        await interaction.response.send_message("Skipped the track: " + queue[0].title + ".")
        await lavalink.skip(interaction.guild.id)
        # if queue:
        #     await bot.change_presence(
        #         activity=discord.Activity(type=discord.ActivityType.listening, name=queue[0].title))
        # return
        # else:
        #     await interaction.response.send_message("Theres nothing to skip stupid")
    else:
        await interaction.response.send_message("Theres nothing to skip stupid",ephemeral=True)


@bot.tree.command(name="queue", description="Get the queue")
@app_commands.describe(amount="The amount of tracks you want to see. Default is 10.")
async def queue(interaction: discord.Interaction, amount: int = 10):
    if await is_queue(interaction.guild_id):
        queue = await lavalink.queue(interaction.guild.id)
        totalms = 0
        for track in queue:
            totalms = totalms + track.length
        lis = queue.copy()
        await interaction.response.defer(ephemeral=True)
        tracks = [f"**{i + 1}.** {t.title} ({await bot.fetch_user(int(t.requester))})" for (i, t) in
                enumerate(lis[:amount])]
        await interaction.followup.send(
            "\n".join(tracks) + "\n**Total Track amount: " + str(
                len(queue)) + " , and a total playtime of " + length_format(
                totalms) + ".**", ephemeral=True)
    else:
        return await interaction.response.send_message("No tracks in queue.")


@bot.tree.command(name="volume", description="Set the volume of the player")
@app_commands.describe(volume="Set the volume to a number between 0 and 1000. Deafult is 100")
async def volume(interaction: discord.Interaction, volume: int = 100):
    if volume>1000 or volume <0:
        return await interaction.response.send_message("the volume has to be between 0 and 1000")
    if await is_queue(interaction.guild_id):
        await lavalink.volume(interaction.guild.id, volume)
        if volume == 69:
            await interaction.response.send_message(f"Set the volume to NICE.")
        else:
            await interaction.response.send_message(f"Set the volume to {volume}%.")
    else:
        await interaction.response.send_message("There is nothing playing at the moment")


@bot.tree.command(name="seek", description="Seek to a specific time")
@app_commands.describe(position="The time to seek to in hh:mm:ss format")
async def seek(interaction: discord.Interaction, position: str):
    if await is_queue(interaction.guild_id):
        await lavalink.seek(interaction.guild.id, format_millisecs(position))
        track = await lavalink.queue(interaction.guild.id)
        await interaction.response.send_message(f"Seeked to {position} in {track[0].title}.")
    else:
        await interaction.response.send_message(f"Not playing anything.",ephemeral=True)


@bot.tree.command(name="shuffle", description="Shuffle the queue")
async def shuffle(interaction: discord.Interaction):
    if await is_queue(interaction.guild_id):
        await lavalink.shuffle(interaction.guild.id)
        await interaction.response.send_message("Shuffled the queue.")
    else:
        await interaction.response.send_message("Not playing anything.")


@bot.tree.command(name="remove", description="Remove a track from the queue")
@app_commands.describe(position="The track position in the queue. Leave empty to remove the last track in the queue.")
async def remove(interaction: discord.Interaction, position: int = 0):
    if is_queue(interaction.guild_id):
        queue = await lavalink.queue(interaction.guild.id)
        if position <= len(queue):
            if position == 0:
                position = len(queue)
            re_title = queue[position - 1].title
            await lavalink.remove(interaction.guild.id, position - 1)
            await interaction.response.send_message(f"Removed {re_title} from the queue. bad song BAD")
        else:
            await interaction.response.send_message(f"No track with that position.")
    else:
        await interaction.response.send_message(f"There is nothing to remove.")


@bot.tree.command(name="repeat", description="Repeat the current track/queue")
@app_commands.describe(status="Should we repeat?", queue="should we repeat the whole queue?")
async def repeat(interaction: discord.Interaction, status: bool, queue: bool = False):
    if queue:
        typ = "Queue"
        if status:
            verb = "Start"
        else:
            verb = "Stop"
        await lavalink.queue_repeat(interaction.guild.id, status)
    else:
        typ = "Track"
        if status:
            verb = "Start"
        else:
            verb = "Stop"
        await lavalink.repeat(interaction.guild.id, status)
    await interaction.response.send_message(f"{verb}ing to repeat the {typ}.")


@bot.tree.command(name="filter", description="Add Filters to the current queue. Leave filter empty to disable")
@app_commands.describe(rotation="rotations per second", tremolo="tremelo frequency")
async def filter(interaction: discord.Interaction, rotation: float = 0.0, tremolo: float = 0.0):
    filters = lavaplayer.Filters()

    if rotation > 0:
        filters.rotation(rotation)

    if tremolo > 0:
        filters.tremolo(tremolo, 0.7)

    await lavalink.filters(interaction.guild.id, filters)
    await interaction.response.send_message("Filter applied.")


def to_format(words: str):
    return words.strip().title()


def multiple_list(lst: list):
    expand_list = []
    for i in lst:
        m = i.split('|')
        if len(m) == 2:
            value = m[0].strip()
            amount = m[1].strip()
            if amount.isnumeric() and int(amount) > 0:
                expand_list += [value] * int(amount)
                continue
        expand_list.append(i)
    return expand_list


@bot.tree.command(name="roulette", description="get a shitty choice right here!")
@app_commands.describe(choices="list the options with a comma inbetween each choice and | to add multiple of a choice")
async def roulette(interaction: discord.Interaction, choices: str):
    if ',' in choices:
        opt = choices.split(",")
        opt = list(map(to_format, filter(None, opt)))
        opt = multiple_list(opt)
        if len(opt) > 1:
            congratz = opt[random.randint(0, len(opt) - 1)]
            percent = (opt.count(congratz) / len(opt)) * 100
            embed = discord.Embed(
                title=congratz,
                description=f"with a chance of {percent}%",
                color=interaction.user.color or discord.Color.random()
            )
            await interaction.response.send_message(f"Ccongraawrasffisakgfjpgasdtulations! The Chosen option is:",
                                                    embed=embed)
            return
    await interaction.response.send_message("I kinda didn't find any commas in your choices, and thus fuck you.")


@bot.tree.command(name="nyaa", description="Search for an Anime on Nyaa.si")
@app_commands.describe(query="Enter a search query for an anime torrent",
                       trusted="Show Trusted only results. True by default",
                       amount="The maximum amount of results to show. Default is 10")
async def nyaa(interaction: discord.Interaction, *, query: str, trusted: bool = True, amount: int = 10):
    nya = NyaaReq()
    if trusted:
        trus = 2
    else:
        trus = 0
    result = nya.get(query=query, category="1_2", criteria=trus)
    lis = [f"**{i + 1}.** [{t['name']}]({t['url']})" for (i, t) in enumerate(result[:amount])]
    embed = discord.Embed()
    embed.title = "Nyaa Results for < " + query + " >"
    if len(lis) > 0:
        embed.description = "\n".join(lis)
    else:
        embed.description = "There are no results for your stupid search, you stupid."
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="feed",
                  description="Manage the anime release feed if used wtihout argument will show the current feed entries")
@app_commands.describe(action="The available actions are: Show/Add/Remove/Update",
                       entry="If you change an entry in the feed what do you want to add/remove")
async def feed(interaction: discord.Interaction, action: str = "Show", entry: str = "null"):
    str_title = "title"
    str_episode = "episode"
    if action.lower() == "show":
        LIS = [f"**{i + 1}.** {t.get(str_title).title()} - Episode {t.get(str_episode)}" for (i, t) in
               enumerate(json_read("Data"))]
        await interaction.response.send_message("\n".join(LIS))
    elif action.lower() == "add":
        if not entry == "null":
            data = json_read("Data")
            data.append({"title": entry.lower(), "episode": 0})
            json_write(data, "Data")
            await interaction.response.send_message(f"Added {entry} to the feed successfully")
    elif action.lower() == "remove":
        data = json_read("Data")
        for thing in data:
            if entry.lower() in thing.get("title"):
                data.remove(thing)
                json_write(data, "Data")
                return await interaction.response.send_message(f"Removed {entry} from the feed successfully")
        await interaction.response.send_message(f"Fuck you we didn't find that trash in the feed")
    elif action.lower() == "update":

        embed = await feed_update() or discord.Embed(title="Nothing new, sowwy.")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(
            "The only options are Show/Add/Remove/Update! are you stupid or something?")


async def feed_update():
    rss_feed = feedparser.parse("https://subsplease.org/rss/?t&r=1080")
    data = json_read("Data")
    result: list = []
    for entry in rss_feed.entries:
        for comp in data:
            if comp.get("title") in entry.get("title").lower():
                index = entry.get("title").rfind('- ')
                stri = entry.get("title")[index + 2:]
                rss_episode = stri[:stri.find(' ')]
                if int(comp.get("episode")) < int(rss_episode):
                    result.append(entry)
                    comp["episode"] = int(rss_episode)
                    json_write(data, "Data")
                break
    if len(result) > 0:
        list_links = [f"**{i + 1}.** [{t.get('title')}]({t.get('link')})" for (i, t) in enumerate(result)]
        embed = discord.Embed(
            title="A new Anime has been released!",

            description="\n".join(list_links),
        )
        return embed


@bot.tree.command(name="birthday", description="get a list of birthdays")
async def birthday(interaction: discord.Interaction):
    data = json_read("BirthDay")
    lis = [
        f"**{i + 1}.** {bot.get_user(t.get('id'))} - {t.get('date').split(' ')[0]} which is {relative_time_format(datetime.strptime(t.get('date').split(' ')[0], '%Y-%m-%d'))}"
        for (i, t) in enumerate(data)]
    embed = discord.Embed(title=f"Who needs bookface when you have {bot.user.display_name}:",
                          description="\n".join(lis))
    # embed.add_field(f"**{i + 1}.** {bot.get_user(t.get('id'))} - {t.get('date')}"for (i, t) in enumerate(data))
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="spor", description="3 2 1 countdown.")
async def spor(interaction: discord.Interaction):
    if not await is_queue(interaction.guild_id):
        tracks = await lavalink.auto_search_tracks("https://www.youtube.com/watch?v=kOrZEjLrno0")
        if not interaction.guild.voice_client:
            if not interaction.user.voice:
                await interaction.followup.send("You are not in a voice channel!", ephemeral=True)
                return
            await interaction.guild.change_voice_state(channel=interaction.user.voice.channel, self_deaf=True,
                                                    self_mute=False)
            await lavalink.wait_for_connection(interaction.guild.id)
        await interaction.response.send_message("Good luck watching Boku No Pico!")
        await lavalink.play(interaction.guild.id, tracks[0], interaction.user.id)
        await lavalink.seek(interaction.guild_id, 1000)
    else:
        await interaction.response.send_message("There is something else playing at the moment.")


async def is_queue(Guild_id:int):
    try:
        if len(await lavalink.queue(Guild_id))>0:
            return True
    except:
        return False
    return False

async def birth_update():
    birth_list = []
    data = json_read("BirthDay")
    for entry in data:
        date = datetime.strptime(entry.get("date").split(" ")[0], '%Y-%m-%d')
        if date <= datetime.now():
            birth_list.append(entry.get("id"))
            try:
                entry["date"] = str(date.replace(year=datetime.now().year + 1))
            except ValueError:
                entry["date"] = str(date.replace(year=datetime.now().year + 1, day=28))
            json_write(data, "BirthDay")
    if len(birth_list) == 0:
        return
    lis = []
    for user_id in birth_list:
        lis.append(f"Congratz <@{user_id}>!")
        # embed.add_field(f"Congratz {bot.get_user(id)}!")
    return discord.Embed(title="Happy BirthDay!", description="\n".join(lis))


def relative_time_format(date: datetime) -> str:
    date_tuple = (date.year, date.month, date.day, date.hour, date.minute, date.second)
    # Convert to unix time.
    return f'<t:{int(time.mktime(datetime(*date_tuple).timetuple()))}:R>'


def json_read(path):
    f = open(f"{path}.json", "r")
    data = json.load(f)
    f.close()
    return data


def json_write(data, path):
    f = open(f"{path}.json", "w")
    data_json = json.dumps(data)
    f.write(data_json)
    f.close()


def length_format(milli: int):
    secs = int(milli / 1000)
    minutes = int(secs / 60)
    secs = secs % 60
    hour = int(minutes / 60)
    minutes = minutes % 60
    stri = ''
    if hour > 0:
        stri = str(hour) + ":"
    if minutes > 9:
        stri = stri + str(minutes)
    else:
        stri = stri + "0" + str(minutes)
    if secs > 9:
        stri = stri + ":" + str(secs)
    else:
        stri = stri + ":0" + str(secs)
    #  stri=stri+str(minutes)+":"+str(secs)
    return stri


def format_millisecs(time_obj: str):
    time_obj = time_obj.split(":")
    time_obj.reverse()
    milisecs = int(time_obj[0]) * 1000
    if len(time_obj) > 1:
        milisecs += int(time_obj[1]) * 60000
    if len(time_obj) > 2:
        milisecs += int(time_obj[2]) * 3600000
    return milisecs


@lavalink.listen(lavaplayer.TrackEndEvent)
async def track_end_event(event: lavaplayer.TrackEndEvent):
    queue_list = await lavalink.queue(event.guild_id)
    if len(queue_list) == 0:
        await bot.get_guild(event.guild_id).change_voice_state(channel=None)
        await lavalink.wait_for_remove_connection(event.guild_id)
        await bot.get_channel(int(os.getenv("BotText_id"))).send(
            "Finished the Playlist and thus my job here is complete! Sionara!")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=DefaultPresence))
    else:
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name=queue_list[0].title))


leave_users_links = {
    353219254641885184: "https://www.youtube.com/watch?v=wxqg6oWx0io",  # shauli
    900987845978763265: "https://www.youtube.com/watch?v=C3YgN8sdZr0",  # uri
    256448898925723650: "https://www.youtube.com/watch?v=SX0kCJiueeA",  # yoram
}


@bot.event
async def on_voice_state_update(member,before,after): # this was all yorams idea dont blame me!
    if member.id in leave_users_links:
        if before.channel is not None and after.channel is None:
            if not await is_queue(DEFAULT_GUILD_ENABLE.id):
                tracks = await lavalink.auto_search_tracks(leave_users_links[member.id])
                await bot.get_guild(DEFAULT_GUILD_ENABLE.id).change_voice_state(channel=before.channel, self_deaf=True,
                                                            self_mute=False)
                await lavalink.wait_for_connection(DEFAULT_GUILD_ENABLE.id)
                await lavalink.play(DEFAULT_GUILD_ENABLE.id, tracks[0], member.id)
        if await is_queue(DEFAULT_GUILD_ENABLE.id)and after.channel is not None:
            bot_channel=None
            guild= bot.get_guild(DEFAULT_GUILD_ENABLE.id)
            for channel in  guild.channels:
                if isinstance(channel,discord.VoiceChannel):
                    for connected_member in channel.members:
                        if connected_member==bot.user:
                            bot_channel=channel
                            break
                    if bot_channel is not None:
                        break
            if after.channel == bot_channel and (await lavalink.queue(DEFAULT_GUILD_ENABLE.id))[0].uri==leave_users_links[member.id]:
                await lavalink.stop(DEFAULT_GUILD_ENABLE.id)

@tasks.loop(hours=1)
async def hour_loop():
    mods = bot.get_guild(DEFAULT_GUILD_ENABLE.id).get_role(758753784297291778).members
    microed = mods[random.randint(0, len(mods) - 1)]
    microsplit = str(microed).split('#')[0]
    default_presence = f'for {microsplit}\'s micro penis'
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=default_presence))
    embed = await birth_update()
    if embed:
        await bot.get_channel(int(os.getenv("AnimeText_id"))).send(embed=embed)
    LOG.info('updated feed')
    embed = await feed_update()
    if embed:
        await bot.get_channel(int(os.getenv("AnimeText_id"))).send(embed=embed)


@bot.event
async def on_socket_raw_receive(msg):
    data = json.loads(msg)

    if not data or not data["t"]:
        return
    if data["t"] == "VOICE_SERVER_UPDATE":
        guild_id = int(data["d"]["guild_id"])
        endpoint = data["d"]["endpoint"]
        token = data["d"]["token"]

        await lavalink.raw_voice_server_update(guild_id, endpoint, token)

    elif data["t"] == "VOICE_STATE_UPDATE":
        if not data["d"]["channel_id"]:
            channel_id = None
        else:
            channel_id = int(data["d"]["channel_id"])

        guild_id = int(data["d"]["guild_id"])
        user_id = int(data["d"]["user_id"])
        session_id = data["d"]["session_id"]

        await lavalink.raw_voice_state_update(
            guild_id,
            user_id,
            session_id,
            channel_id,
        )


bot.run(TOKEN)
