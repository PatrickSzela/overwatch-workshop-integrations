# Overwatch Workshop Integrations

A proof-of-concept application enabling control of Custom Games from external sources

> [!NOTE]
> This application is still in very early stages of development

### Currently supported integrations:

- Twitch

## Requirements

> [!WARNING]
> Starting with Season 11, the _Enable Workshop Inspector Log File_ setting has been removed. If you haven't enabled it before Season 11 release, **you won't be able to use this application**

- PC with Windows or Linux operating system
- Python 3.13 or higher installed
- Overwatch account with both _Enable Workshop Inspector_ and _Enable Workshop Inspector Log File_ enabled
- Good knowledge of Python and virtual environments
- Having an Overwatch client continuously focused after starting a Custom Game and not interacting with it
- Being an **owner** and **spectator** of the Custom Game lobby, and having properly set your keybinds (under Controls -> Spectate):

| Section         | Name                    | Keybind                             |
| --------------- | ----------------------- | ----------------------------------- |
| Spectate        | Spectate Lock On        | Left Mouse Button                   |
| User Interface  | Modify FOV              | **F** **(not assigned by default)** |
| Camera Movement | Disable Camera Blending | Z                                   |
| Camera Movement | Move Fast               | Left Shift                          |
| Camera Movement | Move Slow               | Left Ctrl                           |
| Camera Movement | Move Down               | Q                                   |
| Camera Movement | Move Up                 | E                                   |

> [!IMPORTANT]
> Except for _Modify FOV_, **which doesn't have any key assigned**, the keybinds above should match the default in-game keybinds
>
> These keys are currently hardcoded in the tool and there's no way to change them, so for now you're going to have to match them in-game. In the future that should change

## Installation

1. Clone this repository
2. Create and activate Python virtual environment
3. Install dependencies:
   `pip install -r requirements.txt`
4. **For Linux users:** Install [ydotool](https://github.com/ReimuNotMoe/ydotool) (and, optionally, [configure it to not require root privileges](https://github.com/ideasman42/nerd-dictation/blob/main/readme-ydotool.rst#configuring-ydotool))

Additionally:

1. **For Twitch integration** you'll need to [register your application on Twitch](https://dev.twitch.tv/console/apps/create):
   1. Fill out the **Name**, **Category** and **Client type** fields as desired
   2. Under **OAuth Redirect URLs** provide this URL: `http://localhost:17563`
   3. Create the application
   4. Save the generated **Client ID** and **Client secret** somewhere safe

## Usage

1. Activate the Python virtual environment if not active already
2. Execute the `main.py` script
3. If this is your first time running this application, you'll need to provide the necessary information:
   1. Path to the Overwatch directory in your Documents folder
      - **Windows users:** for majority of users, you won't have to provide this information, unless you've changed the location of your Documents or Overwatch folders
      - **Linux users:** will need to provide a path to the `Documents/Overwatch` folder in their Proton/Wine prefix:
        - For Proton (Steam): `{STEAM_LIBRARY_FOLDER}/compatdata/2357570/pfx/drive_c/users/steamuser/Documents/Overwatch`
        - For Wine: the location depends on how you've set up your game, so you're on your own here
   2. **For Twitch integration** provide the following keys generated during registration of your application:
      - **Client ID** as `application ID`
      - **Client secret** as `application secret key`
4. **For Linux users:** start Ydotool daemon `ydotoold`
5. Start a Custom Game that supports this application (for example [Mystery Modifiers](https://workshop.codes/mystery-modifiers)). Don't forget to move yourself to a spectator slot!

## How does this app works?

This application serves as a "bridge" between external services and the Workshop mode.

To achieve this, this application encodes and forwards all data to the game, by sending virtual inputs to the game's client. For this reason, **the game's client must be continuously focused** and **the user must not interact with it** while inputs are being sent. It's also required that the owner of the lobby must be a spectator.

To receive information from the game and forward it to an external service, this application continuously reads and parses a Workshop log file, generated by currently hosted Custom Game. Every message (that's supposed to be forwarded to this application) is (internally) being converted to a JSON array of key-pair values by the Workshop mode, and then appended the log file, which is later being parsed by this application. Invalid messages are ignored to allow debugging of the Workshop mode.

The application automatically detects when the log file is being created, modified and closed. Once a log file is created, the application will start monitoring it for any changes. Creation of the log file also means that the Custom Game has started. Once the Custom Game finishes or is restarted, the game's client closes the log file.

More information about how it works will be provided in the future.
