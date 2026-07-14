# Rootless component installation and SSH stdio

The add-on build creates a relocatable Linux user archive containing the
Python bridge zipapp, protocol package, bundled MessagePack, Lua plugin,
configuration, and installer. The exact archive is embedded in the add-on;
installation performs no external download.

`NVDA menu → Tools → Neovim Access Link: Install or update components...`
offers “This computer” and saved Linux connections as initially clear
checkboxes. Selected targets run in a background worker with bounded upload and
install times. Spoken progress and a non-blocking final summary report every
success and failure.

Linux files install under `~/.local/bin`, `~/.local/share/nvim/site/pack`, and
`~/.local/share/nvim-nvda` without root. The bridge is a Python zipapp; target
Python 3 is required, but target MessagePack and pynvim packages are not.

Local installation atomically replaces the plugin in
`%LOCALAPPDATA%\nvim-data\site\pack\nvim-nvda\start\nvim-nvda`. Running Neovim
instances must be restarted after an update.

The packaged JSON configuration keeps the Neovim claim key and NVDA gesture
consistent. Changing only one installed copy is unsupported; rebuild and
update both sides together.
