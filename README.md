# nexus-telegram-bot

This is a Telegram bot designed for managing groups, broadcasting messages, and handling list-based group management efficiently. The bot is built using Telethon and Python, and it supports features such as adding/removing groups to/from lists, broadcasting messages to groups, and more.

## Features

- **Add Group to List**: Automatically prompts the admin to name and add the group to a list when the bot is added to a new group.
- **Remove Group from List**: Allows the admin to remove a group from a specified list.
- **Delete List**: Allows the admin to delete an entire list.
- **Broadcast Message**: Allows the admin to broadcast a message to all groups in a specified list.
- **List All Groups in a List**: Allows the admin to list all group names in a specified list.
- **Show All Lists**: Displays all lists with inline buttons and allows the admin to view all groups in a selected list.
- **Help Command**: Provides detailed information about all available commands.
- **Server Down Notification**: Notifies the admin if the server goes down.

## Commands

- `/broadcast [list_name] [message]`: Broadcast a message to a list.
- `/deletelist [list_name]`: Delete a specific list.
- `/removegroup [list_name] [group_name]`: Remove a group from a specific list.
- `/listgroups [list_name]`: List all group names in a specific list.
- `/lists`: Show all lists with inline buttons to see their groups.
- `/help`: Show this help message.

## Setup

### Prerequisites

- Python 3.6+
- [Telethon](https://github.com/LonamiWebs/Telethon)

### Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/telegram-group-management-bot.git
    cd telegram-group-management-bot
    ```

2. Create a virtual environment and activate it:

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the dependencies:

    ```bash
    pip install telethon
    ```

4. Create a `.gitignore` file in the root directory to exclude unnecessary files:

    ```gitignore
    # Byte-compiled / optimized / DLL files
    __pycache__/
    *.py[cod]
    *$py.class



### Running the Bot

Run the bot using the following command:

```bash
python main.py
