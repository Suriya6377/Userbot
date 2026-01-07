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

if not API_ID or not API_HASH or not SESSION_STRING:
    logger.error("Missing Environment Variables! Please set API_ID, API_HASH, and SESSION_STRING.")
    exit(1)

# Initialize the Client
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage(pattern=r'^\.status$'))
async def status_handler(event):
    """Check if the bot is running."""
    if not event.sender_id == (await client.get_me()).id:
        return
    await event.reply("✅ Userbot is running and ready on Render!")

@client.on(events.NewMessage(pattern=r'^\.scrape (\S+) (\S+)$'))
async def scrape_handler(event):
    """
    Command: .scrape source_channel target_channel
    Example: .scrape @source @target
    """
    # Security check: Only allow the owner to trigger this
    me = await client.get_me()
    if event.sender_id != me.id:
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
        members = await client.get_participants(source_entity)
    except Exception as e:
        await status_msg.edit(f"❌ Error fetching members: {str(e)}")
        return

    added_count = 0
    failed_count = 0

    await status_msg.edit(f"Found {len(members)} members. Starting to add...")

    for member in members:
        if member.bot:
            continue
        if member.deleted:
            continue
        
        # Don't try to add yourself
        if member.id == me.id:
            continue

        try:
            # Check privacy settings? 
            # Unfortunately Telethon's InviteToChannelRequest handles the invite.
            # We must handle FloodWait and Privacy errors.
            
            await client(functions.channels.InviteToChannelRequest(
                channel=target_entity,
                users=[member]
            ))
            
            added_count += 1
            logger.info(f"Added {member.id}")
            
            # Update status every 10 members to avoid flood
            if added_count % 10 == 0:
                await status_msg.edit(f"Progress: Added {added_count} members...")
            
            # Sleep to avoid rate limits
            await asyncio.sleep(2) # 2 seconds is safer than 1

        except errors.PeerFloodError:
            logger.warning("Getting Flood Error from Telegram. Waiting for 60 seconds.")
            await status_msg.edit(f"⚠️ FloodWait triggered. Pausing for 60s... (Added: {added_count})")
            await asyncio.sleep(60)
        except errors.UserPrivacyRestrictedError:
            # User's privacy settings prevent adding
            failed_count += 1
        except errors.UserBotError:
            failed_count += 1
        except errors.UserAlreadyParticipantError:
            # Already in group
            pass
        except errors.ChatAdminRequiredError:
             await status_msg.edit("❌ Error: You need to be an admin in the target channel to add members!")
             return
        except Exception as e:
            logger.error(f"Error adding {member.id}: {e}")
            failed_count += 1
            await asyncio.sleep(1)

    await status_msg.edit(f"✅ **Scraping Completed!**\n\nSuccessful: {added_count}\nFailed/Privacy: {failed_count}")

print("Bot is starting...")
with client:
    client.run_until_disconnected()
