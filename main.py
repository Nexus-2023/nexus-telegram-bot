import re
import logging
from telethon import TelegramClient, events, Button
from database import Database
from dotenv import load_dotenv
import os
import asyncio

# Load environment variables from .config file
load_dotenv('.config')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch variables from environment
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
admin_id = os.getenv("ADMIN_ID")
database_url = os.getenv("DATABASE_URL")
db_username = os.getenv("DB_USERNAME")
db_password = os.getenv("DB_PASSWORD")

# Ensure that environment variables are loaded correctly
if not all([api_id, api_hash, bot_token, admin_id, database_url, db_username, db_password]):
    logger.error("Some environment variables are missing. Please check your .config file.")
    exit(1)

# Convert numeric environment variables to integers
api_id = int(api_id)
admin_id = int(admin_id)

# Initialize client and database
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)
db = Database(database_url)

def authenticate_user(username, password):
    return db.authenticate(username, password)

@client.on(events.ChatAction())
async def handle_new_group(event):
    try:
        if event.user_added or event.user_joined:
            if event.user_id == (await client.get_me()).id:
                group_id = event.chat_id
                db.temp_store(admin_id, {"group_id": group_id, "step": "name"})
                message = (f"I've been added to a new group (ID: {group_id}). "
                           "Please provide a name for this group.")
                await client.send_message(admin_id, message)
    except Exception as e:
        logger.error(f"Error in handle_new_group: {e}")
        await client.send_message(admin_id, f"Error in handle_new_group: {e}")

@client.on(events.NewMessage(from_users=admin_id))
async def admin_interaction(event):
    try:
        session = db.temp_retrieve(admin_id)
        if not session:
            return

        if session.get("step") == "name":
            group_name = event.raw_text.strip()
            db.temp_store(admin_id, {"group_id": session["group_id"], "group_name": group_name, "step": "list"})
            await event.reply(f"Group named '{group_name}'. Do you want to add it to an existing list or create a new list?",
                              buttons=[
                                  [Button.inline("Add to existing list", b"add_existing")],
                                  [Button.inline("Create new list", b"create_new")]
                              ])
        elif session.get("step") == "new_list_name":
            list_name = event.raw_text.strip()
            group_id = session["group_id"]
            group_name = session["group_name"]
            if db.add_group(group_id, group_name, list_name):
                await event.reply(f"Group '{group_name}' added to new list '{list_name}' successfully!")
            else:
                await event.reply(f"Failed to add group '{group_name}' to the list '{list_name}'. It might already be added.")
            db.clear_session(admin_id)
    except Exception as e:
        logger.error(f"Error in admin_interaction: {e}")
        await client.send_message(admin_id, f"Error in admin_interaction: {e}")

@client.on(events.CallbackQuery)
async def handle_callback(event):
    try:
        data = event.data.decode()
        session = db.temp_retrieve(admin_id)

        if data == "add_existing" and session.get("step") == "list":
            list_names = db.get_all_list_names()
            if not list_names:
                await event.reply("No existing lists found. Please create a new list.")
            else:
                buttons = [[Button.inline(name, f"add_to_list:{name}") for name in list_names]]
                await event.reply("Select an existing list:", buttons=buttons)

        elif data == "create_new" and session.get("step") == "list":
            db.temp_store(admin_id, {"group_id": session["group_id"], "group_name": session["group_name"], "step": "new_list_name"})
            await event.reply("Please provide a name for the new list.")

        elif data.startswith("add_to_list:") and session.get("step") == "list":
            list_name = data.split(":")[1]
            group_id = session["group_id"]
            group_name = session["group_name"]
            if db.add_group(group_id, group_name, list_name):
                await event.reply(f"Group '{group_name}' added to list '{list_name}' successfully!")
            else:
                await event.reply(f"Failed to add group '{group_name}' to the list '{list_name}'. It might already be added.")
            db.clear_session(admin_id)

        elif data.startswith("show_groups:"):
            list_name = data.split(":")[1]
            groups = db.get_group_names(list_name)
            if groups:
                group_list = '\n'.join(groups)
                await event.reply(f"Groups in list '{list_name}':\n{group_list}")
            else:
                await event.reply(f"No groups found in the list '{list_name}'.")
    except Exception as e:
        logger.error(f"Error in handle_callback: {e}")
        await client.send_message(admin_id, f"Error in handle_callback: {e}")

@client.on(events.NewMessage(pattern='/broadcast (.*)', from_users=admin_id))
async def broadcast(event):
    try:
        if authenticate_user(db_username, db_password):
            parts = event.raw_text.split(maxsplit=2)
            if len(parts) < 3:
                await event.reply("Usage: /broadcast [list_name] [message]")
                return

            list_name, message_text = parts[1], parts[2]
            logger.info(f"Broadcasting to list: {list_name} - Message: {message_text}")
            groups = db.get_groups(list_name)
            logger.info(f"Groups fetched: {groups}")
            if not groups:
                await event.reply("No groups found in this list.")
                return

            for group_id in groups:
                try:
                    await client.send_message(group_id, message_text)
                    logger.info(f"Message sent to: {group_id}")
                except Exception as e:
                    logger.error(f"Failed to send message to {group_id}: {e}")
                    await client.send_message(admin_id, f"Failed to send message to {group_id}: {e}")
        else:
            await client.send_message(admin_id, "User is not authenticated")
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await client.send_message(admin_id, f"Error in broadcast: {e}")

@client.on(events.NewMessage(pattern='/deletelist (.+)', from_users=admin_id))
async def delete_list(event):
    try:
        if authenticate_user(db_username, db_password):
            list_name = event.pattern_match.group(1).strip()
            if db.delete_list(list_name):
                await event.reply(f"List '{list_name}' deleted successfully!")
            else:
                await event.reply(f"Failed to delete list '{list_name}'. It might not exist.")
        else:
            await client.send_message(admin_id, "User is not authenticated")
    except Exception as e:
        logger.error(f"Error in delete_list: {e}")
        await client.send_message(admin_id, f"Error in delete_list: {e}")

@client.on(events.NewMessage(pattern='/removegroup (.+) (.+)', from_users=admin_id))
async def remove_group(event):
    try:
        if authenticate_user(db_username, db_password):
            list_name = event.pattern_match.group(1).strip()
            group_name = event.pattern_match.group(2).strip()
            if db.remove_group_from_list(group_name, list_name):
                await event.reply(f"Group '{group_name}' removed from list '{list_name}' successfully!")
            else:
                await event.reply(f"Failed to remove group '{group_name}' from list '{list_name}'. It might not exist.")
        else:
            await client.send_message(admin_id, "User is not authenticated")
    except Exception as e:
        logger.error(f"Error in remove_group: {e}")
        await client.send_message(admin_id, f"Error in remove_group: {e}")

@client.on(events.NewMessage(pattern='/help', from_users=admin_id))
async def help_command(event):
    try:
        help_text = (
            "/start - Initialize the bot.\n"
            "/broadcast [list_name] [message] - Broadcast a message to a list.\n"
            "/deletelist [list_name] - Delete a specific list.\n"
            "/removegroup [list_name] [group_name] - Remove a group from a specific list.\n"
            "/listgroups [list_name] - List all group names in a specific list.\n"
            "/lists - Show all lists with inline buttons to see their groups.\n"
            "/help - Show this help message.\n"
        )
        await event.reply(help_text)
    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        await client.send_message(admin_id, f"Error in help_command: {e}")

@client.on(events.NewMessage(pattern='/listgroups (.+)', from_users=admin_id))
async def list_groups(event):
    try:
        list_name = event.pattern_match.group(1).strip()
        groups = db.get_group_names(list_name)
        if groups:
            group_list = '\n'.join(groups)
            await event.reply(f"Groups in list '{list_name}':\n{group_list}")
        else:
            await event.reply(f"No groups found in the list '{list_name}'.")
    except Exception as e:
        logger.error(f"Error in list_groups: {e}")
        await client.send_message(admin_id, f"Error in list_groups: {e}")

@client.on(events.NewMessage(pattern='/lists', from_users=admin_id))
async def show_lists(event):
    try:
        list_names = db.get_all_list_names()
        if not list_names:
            await event.reply("No lists found.")
        else:
            buttons = [[Button.inline(name, f"show_groups:{name}") for name in list_names]]
            await event.reply("Select a list to see its groups:", buttons=buttons)
    except Exception as e:
        logger.error(f"Error in show_lists: {e}")
        await client.send_message(admin_id, f"Error in show_lists: {e}")

def main():
    while True:
        try:
            client.run_until_disconnected()
        except Exception as e:
            logger.error(f"Bot encountered an error: {e}")
            asyncio.run(client.send_message(admin_id, f"Bot encountered an error: {e}"))

if __name__ == '__main__':
    main()
