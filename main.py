import os
import asyncio
import logging
from telethon import TelegramClient, events, functions, errors
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

if not API_ID or not API_HASH:
    logger.error("Missing API_ID or API_HASH! Please check your environment variables.")
    exit(1)

# Initialize the Client
# If SESSION_STRING is provided, use it (Userbot mode)
# If not, and BOT_TOKEN is used, we can use a local session file (or memory) but Render wipes local files.
# Ideally for Bot mode, we don't need a StringSession if we pass bot_token to start(),
# but Telethon needs a session storage. We'll use 'bot_session' which creates a file.
# On Render, this file is lost on restart, which is fine for Bots (stateless login).
session = StringSession(SESSION_STRING) if SESSION_STRING else 'bot_session'

client = TelegramClient(session, API_ID, API_HASH)

async def check_auth(event):
    """
    Verifies if the command sender is authorized.
    """
    sender_id = event.sender_id
    
    # 1. Bot Mode: Only allow the ADMIN_ID
    if BOT_TOKEN:
        if sender_id == ADMIN_ID:
            return True
        else:
            # Optional: Log or reply to unauthorized users?
            # await event.reply(f"⛔ Unauthorized. Your ID: `{sender_id}`")
            return False
            
    # 2. Userbot Mode: Only allow the User themselves
    else:
        me = await client.get_me()
        return sender_id == me.id

@client.on(events.NewMessage(pattern=r'^\.status$'))
async def status_handler(event):
    """Check if the bot is running."""
    if not await check_auth(event):
        return

    mode = "Bot" if BOT_TOKEN else "Userbot"
    await event.reply(f"✅ **{mode}** is running and ready on Render!")

@client.on(events.NewMessage(pattern=r'^\.scrape (\S+) (\S+)$'))
async def scrape_handler(event):
    """
    Command: .scrape source_channel target_channel
    Example: .scrape @source @target
    """
    if not await check_auth(event):
        return

    args = event.pattern_match.groups()
    source_username = args[0]
    target_username = args[1]

    status_msg = await event.reply(f"🔄 Starting scrape from {source_username} to {target_username}...")

    try:
        # Resolve entities
        source_entity = await client.get_entity(source_username)
        target_entity = await client.get_entity(target_username)
    except Exception as e:
        await status_msg.edit(f"❌ Error resolving channels: {str(e)}")
        return

    try:
        # Note: Bots usually cannot get participants from groups they are not admin in.
        members = await client.get_participants(source_entity)
    except Exception as e:
        await status_msg.edit(f"❌ Error fetching members: {str(e)}\n\n(Note: Bots can often only see members if they are Admins in the group).")
        return

    added_count = 0
    failed_count = 0

    await status_msg.edit(f"Found {len(members)} members. Starting to add...")

    me = await client.get_me()

    for member in members:
        if member.bot:
            continue
        if member.deleted:
            continue
        if member.id == me.id:
            continue

        try:
            await client(functions.channels.InviteToChannelRequest(
                channel=target_entity,
                users=[member]
            ))
            
            added_count += 1
            logger.info(f"Added {member.id}")
            
            if added_count % 10 == 0:
                await status_msg.edit(f"Progress: Added {added_count} members...")
            
            await asyncio.sleep(2) 

        except errors.PeerFloodError:
            logger.warning("Getting Flood Error. Waiting 60s.")
            await status_msg.edit(f"⚠️ FloodWait triggered. Pausing for 60s... (Added: {added_count})")
            await asyncio.sleep(60)
        except errors.UserPrivacyRestrictedError:
            failed_count += 1
        except errors.UserBotError:
            failed_count += 1
        except errors.UserAlreadyParticipantError:
            pass
        except errors.ChatAdminRequiredError:
             await status_msg.edit("❌ Error: You need to be an admin in the target channel to add members!")
             return
        except Exception as e:
            logger.error(f"Error adding {member.id}: {e}")
            failed_count += 1
            await asyncio.sleep(1)

    await status_msg.edit(f"✅ **Scraping Completed!**\n\nSuccessful: {added_count}\nFailed/Privacy: {failed_count}")

print("Starting Client...")

if BOT_TOKEN:
    client.start(bot_token=BOT_TOKEN)
else:
    client.start()

client.run_until_disconnected()

