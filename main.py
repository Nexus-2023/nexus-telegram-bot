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

api_id = ""
api_hash = ""
bot_token = ""
admin_id = 

# Convert numeric environment variables to integers
api_id = int(api_id)
admin_id = int(admin_id)

# Initialize client and database
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)
db = Database('data.db')

@client.on(events.ChatAction())
async def handle_new_group(event):
    if event.user_added or event.user_joined:
        if event.user_id == (await client.get_me()).id:
            group_id = event.chat_id
            db.temp_store(admin_id, {"group_id": group_id, "step": "name"})
            message = (f"I've been added to a new group (ID: {group_id}). "
                       "Please provide a name for this group.")
            await client.send_message(admin_id, message)

@client.on(events.NewMessage(from_users=admin_id))
async def admin_interaction(event):
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

@client.on(events.CallbackQuery)
async def handle_callback(event):
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

@client.on(events.NewMessage(pattern='/broadcast (.*)', from_users=admin_id))
async def broadcast(event):
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

@client.on(events.NewMessage(pattern='/deletelist (.+)', from_users=admin_id))
async def delete_list(event):
    list_name = event.pattern_match.group(1).strip()
    if db.delete_list(list_name):
        await event.reply(f"List '{list_name}' deleted successfully!")
    else:
        await event.reply(f"Failed to delete list '{list_name}'. It might not exist.")

@client.on(events.NewMessage(pattern='/removegroup (.+) (.+)', from_users=admin_id))
async def remove_group(event):
    list_name = event.pattern_match.group(1).strip()
    group_name = event.pattern_match.group(2).strip()
    if db.remove_group_from_list(group_name, list_name):
        await event.reply(f"Group '{group_name}' removed from list '{list_name}' successfully!")
    else:
        await event.reply(f"Failed to remove group '{group_name}' from list '{list_name}'. It might not exist.")

@client.on(events.NewMessage(pattern='/help', from_users=admin_id))
async def help_command(event):
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

@client.on(events.NewMessage(pattern='/listgroups (.+)', from_users=admin_id))
async def list_groups(event):
    list_name = event.pattern_match.group(1).strip()
    groups = db.get_group_names(list_name)
    if groups:
        group_list = '\n'.join(groups)
        await event.reply(f"Groups in list '{list_name}':\n{group_list}")
    else:
        await event.reply(f"No groups found in the list '{list_name}'.")

@client.on(events.NewMessage(pattern='/lists', from_users=admin_id))
async def show_lists(event):
    list_names = db.get_all_list_names()
    if not list_names:
        await event.reply("No lists found.")
    else:
        buttons = [[Button.inline(name, f"show_groups:{name}") for name in list_names]]
        await event.reply("Select a list to see its groups:", buttons=buttons)

async def check_server():
    while True:
        await asyncio.sleep(60)  # Check every minute
        try:
            # Simulate a server check, replace with actual logic
            # If server check fails, it will raise an exception
            pass
        except Exception as e:
            await client.send_message(admin_id, "Server is down")
            logger.error(f"Server is down: {e}")

def main():
    client.loop.create_task(check_server())
    client.run_until_disconnected()

if __name__ == '__main__':
    main()
