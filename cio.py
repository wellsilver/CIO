# D:\Wells\rusting\democraticbot quickstart
import discord
import time
import datetime
import threading
import asyncio
import sqlite3
import psycopg2
import enum
import requests
from discordwebhook import Discord as Discordhook

f=open("keys.txt")
keys = f.readlines()
f.close()
discordhk = Discordhook(url=keys[2])
con = psycopg2.connect(keys[0])
con.autocommit=True

global onlinec
onlinec:list[tuple[int,int,str,str,discord.channel.TextChannel]] = []

global db
db = con.cursor()

ssugoing = False
ssulog = []
ssumaxp = 0

def embed(desc:str,title:str) -> discord.Embed:
  return discord.Embed(title=title, description=desc, color=0x336EFF)

intents = discord.Intents.default()
intents.members = True
cli = discord.Client(intents=intents)
ctr = discord.app_commands.CommandTree(cli)

def checkpast():
  while True:
    time.sleep(60)
    db.execute("select * from \"Staff\"")
    a = db.fetchall()
    for i in a:
      if i[5] == None:
        continue
      if i[5] < int(time.time()):
        discordhk.post(content=f"<@{i[0]}> Your loa has expired!!")
        db.execute(f'update "Staff" set loa=null, laston={int(time.time())} where "ID"={i[0]}')

thread = threading.Thread(target=checkpast)
thread.start()

def strfdelta(tdelta, fmt):
  d = {"days": tdelta.days}
  d["hours"], rem = divmod(tdelta.seconds, 3600)
  d["minutes"], d["seconds"] = divmod(rem, 60)
  d["hours"] += tdelta.days*24
  return fmt.format(**d)

@cli.event
async def on_ready():
  await ctr.sync()

class stat_enum(enum.Enum):
  leaderboard=0
  onlinern=1
  lastssu=2
  loa=3

@ctr.command(name="stats",description="get status stuff")
async def stat(ctx:discord.Interaction,what:stat_enum,who:discord.Member=None):
  if what == stat_enum.leaderboard:
    await ontime(ctx,who)
  elif what == stat_enum.onlinern:
    await online(ctx)
  elif what == stat_enum.lastssu:
    db.execute("select * from ssu order by start desc limit 1")
    v = db.fetchone()
    await ctx.response.send_message(embed=embed(f"Started: <t:{v[0]}:R>\nHost: <@{v[1]}>\nMap: {v[2]}\nAccount: {v[3]}\nmax player count: {v[5]}",None))
  elif what == stat_enum.loa:
    if who == None:
      await ctx.response.send_message(embed=embed(f"Select someone to check their LOA!","stats"))
      return
    db.execute(f"select * from \"Staff\" where \"ID\"={who.id}")
    a=db.fetchone()
    if a == None:
      await ctx.response.send_message(embed=embed(f"<@{who.id}> They arent staff!","stats"))
      return
    if a[5] == None:
      await ctx.response.send_message(embed=embed(f"<@{who.id}> is not on LOA","stats"))
      return
    await ctx.response.send_message(embed=embed(f"<@{who.id}>'s LOA expires <t:{a[5]}:R> on <t:{a[5]}:D>","stats"))

@ctr.command(name="ssustat",description="get logs on any ssu, 'ssu' is an integer and starts from 0 (0 being the first ssu logged)")
async def ssustat(ctx:discord.Interaction,ssu:int):
  db.execute(f"select * from ssu")
  try:
    v = db.fetchall()[ssu]
  except:
    await ctx.response.send_message(embed=embed("Doesnt exist",None))
    return
  await ctx.response.send_message(embed=embed(f"Started: <t:{v[0]}:R>\nHost: <@{v[1]}>\nMap: {v[2]}\nAccount: {v[3]}\nmax player count: {v[5]}\nlogs: {v[4]}",None))

@ctr.command(name="joke",description="get a random joke v2.jokeapi.dev")
async def joke(ctx:discord.Interaction):
  tx=requests.get("https://v2.jokeapi.dev/joke/Miscellaneous?blacklistFlags=nsfw,religious,political,racist,sexist,explicit&format=txt")
  if tx.status_code == 200:
    pass
  tx = tx.text
  await ctx.response.send_message(tx)

async def ontime(ctx:discord.Interaction,who:discord.Member=None):
  if who == None:
    db.execute(f'select * from "Staff" order by timeon DESC') #
    a=db.fetchmany(5)
    embed_ = discord.Embed(title="Leaderboard")
    for i in a:
      m:discord.Member = ctx.guild.get_member(i[0])
      if m == None:
        continue
      embed_.add_field(name="",value=f"\n{m.mention} at ``{strfdelta(datetime.timedelta(seconds=i[3]), '{hours}:{minutes}:{seconds}')}`` time online. <t:{i[2]}:R>",inline=False)
    await ctx.response.send_message(embed=embed_)
  else:
    db.execute(f'select * from "Staff" where "ID"={who.id}')
    a=db.fetchone()
    if a == None:
      await ctx.response.send_message(embed=embed("They arent staff!",None))
      return
    await ctx.response.send_message(embed=embed(f"{who.mention} at ``{strfdelta(datetime.timedelta(seconds=a[3]), '{hours}:{minutes}:{seconds}')}`` time online. <t:{a[2]}:R>",None))

#@ctr.command(name="shift",description="mange your shift")
async def online(ctx:discord.Interaction):
  if len(onlinec)==0:
    await ctx.response.send_message(embed=embed("Nobody is online!",None))
    return
  embed_ = discord.Embed(title="Currently online")
  for i in onlinec:
    embed_.add_field(name="",value=f"\n{i[2]} has been on for {datetime.timedelta(seconds=int(time.time())-i[1])}")
  await ctx.response.send_message(embed=embed_)

class loa_enum(enum.Enum):
  date=0
  start=1
  end=2
  extend=3

@ctr.command(name="loa",description="manage your LOA")
async def sloa(ctx:discord.Interaction,job:loa_enum,days:int=None):
  if ctx.user.get_role(1046984972340318259) == None:
    await ctx.response.send_message(embed=embed("You are not staff!",None),ephemeral=True)
    return
  db.execute(f'select * from "Staff" where "ID"={ctx.user.id}')
  a=db.fetchone()
  if a == None:
    await ctx.response.send_message(embed=embed("error .555w",None))
    return
  if job==loa_enum.date:
    expiry = a[5]
    if expiry == None:
      await ctx.response.send_message(embed=embed(f"Your not on LOA","LOA"))
      return
    await ctx.response.send_message(embed=embed(f"Your loa expires <t:{expiry}:R> on <t:{expiry}:D>","LOA"))
  if job==loa_enum.start:
    if a[5]!=None:
      await ctx.response.send_message(embed=embed("You are allready on LOA, /loa extend","LOA"))
      return
    try:
      v = int(days)
    except:
      await ctx.response.send_message(embed=embed("Days is not an integer","LOA"))
      return
    expiry = int(time.time())+(86400*v)
    db.execute(f'update "Staff" set loa={expiry} where "ID"={ctx.user.id}')
    await ctx.response.send_message(embed=embed(f"Your now on loa! expiry <t:{expiry}:R> on <t:{expiry}:D> ","LOA"))
    return
  if job == loa_enum.end:
    db.execute(f'update "Staff" set loa=null, laston={int(time.time())} where "ID"={ctx.user.id}')
    await ctx.response.send_message(embed=embed("Ended your LOA","LOA"))
    return
  if job == loa_enum.extend:
    try:
      v = int(days)
    except:
      await ctx.response.send_message(embed=embed("Days is not an integer","LOA"))
      return
    old = a[5]
    new = a[5]+(86400*v)
    db.execute(f'update "Staff" set loa={new} where "ID"={ctx.user.id}')
    await ctx.response.send_message(embed=embed(f"extended your LOA from <t:{old}:D> to <t:{new}:D>","LOA"))

class shift_enum(enum.Enum):
  clockin = 0
  clockout =1
  loa = 2

async def shift_real(ctx:discord.Interaction,do:shift_enum):
  if ctx.user.get_role(1046984972340318259)==None:
    await ctx.response.send_message(embed=embed("You are not staff! .",None),ephemeral=True)
    return
  if do == shift_enum.clockin:
    if ssugoing==False:
      await ctx.response.send_message(embed=embed("There is no ssu right now!",None),ephemeral=True)
      return
    db.execute(f'select * from "Staff" where "ID"={ctx.user.id}')
    a=db.fetchone()
    if a == None:
      db.execute(f"insert into \"Staff\" (\"ID\",staffsince) values ({ctx.user.id},{int(time.time())})")
      db.execute(f'select * from "Staff" where "ID"={ctx.user.id}')
      a=db.fetchone()
    if a[4]:
      db.execute(f'update "Staff" set wasautoclockedout=false where "ID"={a[0]}')
    onlinec.append((ctx.user.id,int(time.time()),ctx.user.mention,ctx.user.nick,ctx.channel)) 
    return
  elif do == shift_enum.clockout:
    db.execute(f'select * from "Staff" where "ID"={ctx.user.id}')
    a=db.fetchone()
    if a == None:
      await ctx.response.send_message(embed=embed("You arent staff!",None))
      return
    if a[4]:
      db.execute(f'update "Staff" set wasautoclockedout=false where "ID"={a[0]}')
      await ctx.response.send_message(embed=embed(f"You were clocked out automaticaly for being clocked in longer than 4 hours.",""))
      return
    for i in onlinec:
      if i[0] == ctx.user.id:
        db.execute(f'update "Staff" set timeon=timeon+{int(time.time())-i[1]} where "ID"={ctx.user.id}')
        db.execute(f'update "Staff" set laston={int(time.time())} where "ID"={ctx.user.id}')
        onlinec.remove(i)
        return int(time.time())-i[1]
    await ctx.response.send_message(embed=embed(f"You arent clocked in",None))
    return

@ctr.command(name="shift",description="mange your shift")
async def shift(ctx:discord.Interaction,do:shift_enum):
  ret = await shift_real(ctx,do)
  try: # area below errors intentionally
    if do == shift_enum.clockin:
      await ctx.response.send_message(embed=embed("Clocked you in",None))
    elif do == shift_enum.clockout:
      await ctx.response.send_message(embed=embed(f"Clocked you out, youve been on for {datetime.timedelta(seconds=ret)}",None))
  except:
    pass

@ctr.command(name="clockin",description="use /shift clockin")
async def clockin(ctx:discord.Interaction):
  await ctx.response.send_message(embed=embed(f"Use /shift clockin instead please",None),ephemeral=True)

@ctr.command(name="clockout",description="use /shift clockout")
async def clockout(ctx:discord.Interaction):
  await ctx.response.send_message(embed=embed(f"Use /shift clockout instead please",None),ephemeral=True)

class ssu_enum(enum.Enum):
  start=0
  end=1

@ctr.command(name="ssu",description="manage ssu stuff")
async def ssu(ctx:discord.Interaction,do:ssu_enum,map:str=None,account:str=None):
  global ssugoing
  global ssulog
  global ssumaxp
  if ctx.user.get_role(1056939668425420810)==None:
    await ctx.response.send_message(embed=embed("You are not a ssuh!",None))
    return
  if do == ssu_enum.start:
    if map == None:
      await ctx.response.send_message(embed=embed("map is not a optional parameter when starting a ssu!",None))
      return
    if account == None:
      await ctx.response.send_message(embed=embed("account is not a optional parameter when starting a ssu!",None))
      return
    if ssugoing!=False:
      await ctx.response.send_message(embed=embed("SSU already started!",None))
      return
    ssugoing=int(time.time())
    db.execute(f"insert into ssu (start,host,map,account) values ({ssugoing},{ctx.user.id},'{map}','{account}')")
    await shift_real(ctx,shift_enum.clockin)
    await ctx.response.send_message(embed=embed("Started the ssu, and clocked you in",None))
    return
  elif do == ssu_enum.end:
    # clock everyone out, log the ssu, so and so
    if ssugoing == False:
      await ctx.response.send_message(embed=embed("No.",None))
      return
    tmp = ""
    for i in ssulog:
      tmp+=i
      tmp+=chr(9)
    db.execute(f"update ssu set logs=\'{tmp}\' where start={ssugoing}")
    db.execute(f"update ssu set maxplayers={ssumaxp} where start={ssugoing}")
    ssugoing=False
    ssulog=[]
    ssumaxp=0
    for i in onlinec:
      db.execute(f'update "Staff" set timeon=timeon+{int(time.time())-i[1]} where "ID"={i[0]}')
      db.execute(f'update "Staff" set laston={int(time.time())} where "ID"={i[0]}')
      onlinec.remove(i)
    await ctx.response.send_message(embed=embed("Ended the SSU, everyone is clocked out",None))
    return

class logad_enum(enum.Enum):
  warn=0
  kick=1
  ban=2

@ctr.command(name="adminlog",description="log your administrative doings")
async def logad(ctx:discord.Interaction,what:logad_enum,exactusername:str,notes:str=""):
  pass

class log_enum(enum.Enum):
  log=0
  highestplrcount=1

@ctr.command(name="log",description="log ssu stuff")
async def log(ctx:discord.Interaction,_:log_enum,logvar:str=""):
  if ctx.user.get_role(1056939668425420810)==None:
    await ctx.response.send_message(embed=embed("You are not a ssuh!",None))
    return
  if ssugoing == False:
    await ctx.response.send_message(embed=embed("There isnt an ssu rn",None))
    return
  global ssulog 
  global ssumaxp
  if _ == log_enum.log:
    ssulog.append(logvar)
    await ctx.response.send_message(embed=embed("logged",None),ephemeral=True)
  if _ == log_enum.highestplrcount:
    ssumaxp = int(logvar)
    await ctx.response.send_message(embed=embed("logged",None),ephemeral=True)

@ctr.command(name="inactive",description="findout whos inactive")
async def forceclockout(ctx:discord.Interaction):
  db.execute(f'select * from "Staff" order by laston ASC')
  a=db.fetchmany(5)
  embed_ = discord.Embed(title="Inactivity finder")
  embed_.add_field(name="",value="Shows people with the longest time since last clockout")
  for i in a:
    m:discord.Member = ctx.guild.get_member(i[0])
    if m == None:
      continue
    embed_.add_field(name="",value=f"\n{m.mention} last clocked out <t:{int(time.time())}:R> ago",inline=False)
  await ctx.response.send_message(embed=embed_)

@ctr.command(name="codes",description="put in some fun codes to use")
async def dev(ctx:discord.Interaction,do:str):
  if ctx.user.id == 364514619232092170: # higanbana (me :) )
    if do == "stop":
      await cli.close()
    return
  ctx.response.send_message("Wrong code!")

cli.run(keys[1])
