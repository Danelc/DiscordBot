from bs4 import ResultSet
import feedparser
import discord
from discord import Embed, PublicUserFlags, app_commands
from NyaaReq import NyaaReq
import logging
import os
import time
import lavaplayer
import json
import random
from dotenv import load_dotenv,find_dotenv
#import subprocess

#subprocess.call(['java', '-jar', 'lavalink.jar'])
load_dotenv(find_dotenv())

DEFAULT_GUILD_ENABLE = discord.Object(id=os.getenv("Guild_id"))
TOKEN = os.getenv("DISCORD_TOKEN")

LOG = logging.getLogger("discord.bot")


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
    embed=await FeedUpdate()
    if embed:
        await bot.get_channel(os.getenv("BotText_id")).send(embed=embed)

@bot.tree.command(name="ping", description="Get the latency of the bot")
async def ping(interaction: discord.Interaction):
    start = time.time()
    await interaction.response.send_message("Pong!\nGateway: `%dms`\nLatency: `%dms`"% (round(bot.latency * 1000), round((time.time() - start) * 1000)))
    # await interaction.edit_original_message(
    #     content="Gateway: `%dms`\nLatency: `%dms`"
    #     % (round(bot.latency * 1000), round((time.time() - start) * 1000))
    # )

@bot.tree.command(name="help", description="Get the help of the bot")
async def help(interaction: discord.Interaction):
    commands = bot.tree.get_commands(guild=interaction.guild)
    embed = discord.Embed(title="Faggy Help", description="", color=interaction.user.color or discord.Color.random())
    embed.description = "\n".join(f"`/{command.name}`: {command.description}" for command in commands)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="join", description="Join a voice channel")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("You are not in a voice channel!",ephemeral=True)
        return
    await interaction.guild.change_voice_state(
        channel=interaction.user.voice.channel, self_deaf=True, self_mute=False
    )
    await lavalink.wait_for_connection(interaction.guild.id)
    await interaction.response.send_message("Joined the voice channel.shalom lachem")

@bot.tree.command(name="leave", description="Leave the voice channel")
async def leave(interaction: discord.Interaction):
    await interaction.guild.change_voice_state(channel=None)
    await lavalink.wait_for_remove_connection(interaction.guild.id)
    await interaction.response.send_message("Left the voice channel.bye tamut")

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
    if not interaction.guild.voice_client:
        if not interaction.user.voice:
            await interaction.response.send_message("You are not in a voice channel!",ephemeral=True)
            return
        await interaction.guild.change_voice_state(channel=interaction.user.voice.channel, self_deaf=True, self_mute=False)
        await lavalink.wait_for_connection(interaction.guild.id)
    await interaction.response.defer(thinking=True)
    tracks = await lavalink.auto_search_tracks(query)
    if not tracks:
        return await interaction.followup.send("No results found.")
    elif isinstance(tracks, lavaplayer.TrackLoadFailed):
        await interaction.followup.send("Error loading track, Try again later.\n```%s```" % tracks.message)
        return
    elif isinstance(tracks, lavaplayer.PlayList):
        
        #await interaction.response.send_message("Adding playlist, Please wait...")

        await lavalink.add_to_queue(
            interaction.guild.id, tracks.tracks, interaction.user.id
        )
        
        await interaction.followup.send(
            "Playlist {} Added to queue, track amount: {}".format(
                 tracks.name,len(tracks.tracks)
            )
        )
        return
    if not await lavalink.queue(interaction.guild.id):
        respon = f"Now playing: {tracks[0].uri}"
        #await interaction.response.send_message(f"Now playing: {tracks[0].title}")
    else:
        respon =f"Added to queue: {tracks[0].uri}"
        #await interaction.response.send_message(f"Added to queue: {tracks[0].title}")
    await interaction.followup.send(respon)
    await lavalink.play(interaction.guild.id, tracks[0], interaction.user.id)
    

@bot.tree.command(name="pause", description="Pause the current track")
async def pause(interaction: discord.Interaction):
    await lavalink.pause(interaction.guild.id, True)
    await interaction.response.send_message("Paused the track.")

@bot.tree.command(name="resume", description="Resume the track")
async def resume(interaction: discord.Interaction):
    await lavalink.pause(interaction.guild.id, False)
    await interaction.response.send_message("Resumed the track.")

@bot.tree.command(name="stop", description="Stop the music!")
async def stop(interaction: discord.Interaction):
    if not await lavalink.queue(interaction.guild.id):
        await lavalink.stop(interaction.guild.id)
        return await interaction.response.send_message("Stopped the track.")
    await interaction.response.send_message("No Track is playing to stop stupid.")


@bot.tree.command(name="skip", description="Skip the current track")
async def skip(interaction: discord.Interaction):
    await lavalink.skip(interaction.guild.id)
    await interaction.response.send_message("Skipped the track.")

@bot.tree.command(name="queue", description="Get the queue")
@app_commands.describe(amount="The amount of tracks you want to see. Default is 20.")
async def queue(interaction: discord.Interaction,amount:int=20):
    queue = await lavalink.queue(interaction.guild.id)
    lis= queue.copy()
    if not lis:
        return await interaction.response.send_message("No tracks in queue.")
    #while len(lis)>amount:
    #    lis.pop()
    tracks = [f"**{i + 1}.** {t.title}" for (i, t) in enumerate(lis[:amount])]
    await interaction.response.send_message("\n".join(tracks),ephemeral=True)

@bot.tree.command(name="volume", description="Set the volume of the player")
@app_commands.describe(volume="Set the volume to a number between 0 and 100")
async def volume(interaction: discord.Interaction, volume: int):
    await lavalink.volume(interaction.guild.id, volume)
    if volume == 69:
        await interaction.response.send_message(f"Set the volume to NICE.")
    else:
        await interaction.response.send_message(f"Set the volume to {volume}%.")

@bot.tree.command(name="seek", description="Seek to a specific time")
@app_commands.describe(position="The time to seek to in hh:mm:ss format")
async def seek(interaction: discord.Interaction, position: str):
    stri = position.split(":")
    stri.reverse()
    milisecs = int(stri[0])*1000
    if len(stri)>1:
        milisecs += int(stri[1])*60000
    if len(stri)>2:
        milisecs += int(stri[2])*3600000
    #print(f"milisecs seeked {milisecs}")
    #milisecs = int(stri[0]*60000+stri[1]*1000)
    await lavalink.seek(interaction.guild.id, milisecs)
    track =await lavalink.queue(interaction.guild.id)
    await interaction.response.send_message(f"Seeked to {position} in "+track[0].title+".")

@bot.tree.command(name="shuffle", description="Shuffle the queue")
async def shuffle(interaction: discord.Interaction):
    await lavalink.shuffle(interaction.guild.id)
    await interaction.response.send_message("Shuffled the queue.")

@bot.tree.command(name="remove", description="Remove a track from the queue")
async def shuffle(interaction: discord.Interaction,position:int):
    try:
        queue=lavalink.queue(interaction.guild.id)
        if position <= len(queue):
            ReTitle = queue[position].title
            await lavalink.remove(interaction.guild.id,position)
            await interaction.response.send_message(f"Removed {ReTitle} from the queue. bad song BAD")
        else:
            await interaction.response.send_message(f"No track with that position.")
    except:
        await interaction.response.send_message(f"There is no queue.")


@bot.tree.command(name="repeat", description="Repeat the current track/queue")
@app_commands.describe(status="Should we repeat?", queue="should we repeat the whole queue?")
async def repeat(interaction: discord.Interaction, status: bool, queue: bool = False):
    if queue:
        typ="Queue"
        if status:
            verb = "Start" 
        else:
            verb= "Stop"
        await lavalink.queue_repeat(interaction.guild.id, status)
    else:
        typ="Track"
        if status:
            verb = "Start" 
        else:
            verb= "Stop"
        await lavalink.repeat(interaction.guild.id, status)
    await interaction.response.send_message(f"{verb}ing to repeat the {typ}.")

@bot.tree.command(name="filter", description="Add Filters to the current queue. Leave filter empty to disable")
@app_commands.describe(rotation="rotations per second", tremolo="tremelo frequency")
async def _filter(interaction: discord.Interaction, rotation:float=0.0,tremolo:float=0.0):
    filters = lavaplayer.Filters()

    if rotation>0:
        filters.rotation(rotation)
 
    if tremolo>0:
        filters.tremolo(tremolo,0.7)

    await lavalink.filters(interaction.guild.id, filters)
    await interaction.response.send_message("Filter applied.")

@bot.tree.command(name="roulette", description="get a shity choice right here!")
@app_commands.describe(choices="list the options with a comma inbetween each choice")
async def seek(interaction: discord.Interaction, choices:str):
    if ',' in choices:
        opt=choices.split(",")
        opt = list(filter(None,opt))
        if len(opt)>1:
            embed=discord.Embed(
                title=opt[random.randint(0,len(opt)-1)].strip().title(),
                description="",
                color=interaction.user.color or discord.Color.random()
                )
            await interaction.response.send_message("Ccongraawrasffisakgfjpgasdtulations! The Chosen option is:", embed=embed)
            return
    await interaction.response.send_message("I kinda didnt find any commas in your choices, and thus fuck you.")

@bot.tree.command(name="nyaa", description="Search for an Anime on Nyaa.si")
@app_commands.describe(query="Enter a search query for an anime torrent",trusted="Show Trusted only results. True by default",amount="The maximum amount of results to show. Default is 10")
async def search(interaction: discord.Interaction, *, query: str,trusted:bool=True,amount:int = 10):
    nya = NyaaReq()
    if trusted:
        trus = 2
    else:
        trus = 0
    result = nya.get(query=query,category="1_2",criteria=trus)
    #while len (result)>amount:
    #    result.pop()
    lis = [f"**{i + 1}.** [{t['name']}]({t['url']})" for (i, t) in enumerate(result[:amount])]
    # for (i, t) in enumerate(result):
    #     print(t)
    embed = discord.Embed()
    embed.title="Nyaa Results for < "+query+" >"
    if len(lis)>0:
        embed.description="\n".join(lis)
    else:
        embed.description="There are no results for your stupid search, you stupid."
    await interaction.response.send_message(embed=embed)
    # for (i,t) in enumerate(lis):
    #     if i >0:
    #         await interaction.followup.send("\n"+t)

@bot.tree.command(name="feed", description="Manage the anime release feed")
@app_commands.describe(action="Show/Add/Remove",entry="What to add/remove")
async def feed(interaction: discord.Interaction, *, action: str="Show",entry:str="null"):
    strTitle="title"
    strLink = "link"
    strEpisode="episode"
    if action.lower()=="show":
        LIS = [f"**{i + 1}.** {t.get(strTitle).title()} - {t.get(strEpisode)}" for (i, t) in enumerate(json_read())]
        await interaction.response.send_message("\n".join(LIS))
    elif action.lower()=="add":
        if not entry=="null":
            data=json_read()
            data.append({"title":entry.lower(),"episode":0})
            json_write(data)
            await interaction.response.send_message(f"Added {entry} to the feed succesfully")
    elif action.lower()=="remove":
        data=json_read()
        for thing in data:
            if entry.lower() in thing.get("title"):
                data.remove(thing)
                json_write(data)
                return await interaction.response.send_message(f"Removed {entry} from the feed succesfully")
        await interaction.response.send_message(f"Fuck you we didnt find that trash in the feed") 
    elif action.lower()=="update":
        
        embed=await FeedUpdate() or discord.Embed(title="Nothing new, sowwy.")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("The only options are Show/Add/Remove! are you stupid or something?")
async def FeedUpdate():
    RssFeed = feedparser.parse("https://subsplease.org/rss/?t&r=1080")
    data=json_read()
    result:list=[]
    for entry in RssFeed.entries:
        for comp in data:
            if comp.get("title") in entry.get("title").lower():
                index=entry.get("title").rfind('- ')
                stri=entry.get("title")[index+2:]
                RssEpisode=stri[:stri.find(' ')]
                if int(comp.get("episode"))<int(RssEpisode):
                    result.append(entry)
                    comp["episode"]=int(RssEpisode)
                    json_write(data)
                break
    if len(result)>0:
        strTitle='title'
        strLink='link'
        LIS = [f"**{i + 1}.** [{t.get(strTitle)}]({t.get(strLink)})" for (i, t) in enumerate(result)]
        embed=discord.Embed(
            title="A new Anime has been released!",
            description="\n".join(LIS),
            )
        return(embed) 

def json_read():
    f=open("Data.json")
    data = json.load(f)
    f.close()
    return data
def json_write(data):
    f=open("Data.json","w")
    dataJson=json.dumps(data)
    f.write(dataJson)
    f.close()


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