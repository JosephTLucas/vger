# V'ger

![](static/vger.jpg)

V'ger is an interactive command-line application for interacting with authenticated Jupyter instances.

## Usage

![](static/usage.gif)

## Initial Setup

Upon opening the application, users will be prompted for connection information.
1. Provide the full target host including the port and trailing slash (such as `http://172.0.0.1:8888/`).
2. Provide the token or password.

## Commands

Once a connection is established, users drop into a nested set of menus.

The top level menu is:
- **Reset**: Configure a different host.
- **Enumerate**: Utilities to learn more about the host.
- **Exploit**: Utilities to perform direct action and manipulation of the host and artifacts.
- **Persist**: Utilities to establish persistence mechanisms.
- **Export**: Save output to a text file.
- **Quit**: No one likes quitters.

These menus contain the following functionality:
- **List modules**: Identify imported modules in target notebooks to determine what libraries are available for injected code.
- **Inject**: Execute code in the context of the selected notebook. Code can be provided in a text editor or by specifying a local `.py` file. Either input is processed as a string and executed in runtime of the notebook.
- **Backdoor**: Launch a new JupyterLab instance open to `0.0.0.0`, with `allow-root` on a user-specified `port` with a user-specified `password`.
- **Check History**: See ipython commands recently run in the target notebook.
- **Run shell command**: Spawn a terminal, run the command, return the output, and delete the terminal.
- **List dir or get file**: List directories relative to the Jupyter directory. If you don't know, start with `/`.
- **Upload file**: Upload file from localhost to the target. Specify paths in the same format as List dir (relative to the Jupyter directory). Provide a full path including filename and extension.
- **Delete file**: Delete a file. Specify paths in the same format as List dir (relative to the Jupyter directory).
- **Find models**: Find models based on common file formats.
- **Download models**: Download discovered models.
- **Snoop**: Monitor notebook execution and results until timeout.
- **Recurring jobs**: Launch/Kill recurring snippets of code silently run in the target environment.
