# V'ger

![](static/vger.jpg)

_"…On its journey back, it amassed so much knowledge, it achieved consciousness itself. It became a living thing."_

V'ger is an interactive command-line application for interacting with authenticated Jupyter instances.

## Usage

![](static/usage.gif)

## Initial Setup

Upon opening the application, users will be prompted for connection information.
1. Provide the full target host including the port and trailing slash (such as `http://172.0.0.1:8888/`).
2. Provide the token or password.

If prompt returns back to `hostname`, either the connection failed or there were no open notebook sessions running on that host.

3. Attach to a specific notebook session based on `.ipynb` filename and `Last Active` timestamp.

## Commands

Once a connection is established, users can execute a variety of commands.

- **Reset**: Configure a different host.
- **Switch Notebooks**: Select a different notebook to target.
- **Inject**: Execute code in the context of the selected notebook. Code can be provided in a text editor or by specifying a local `.py` file. Either input is processed as a string and executed in runtime of the notebook. Output will be transparent to other notebook users by specifying `Noisy` or `Stealthy` when prompted. This selection will also dictate how much information is returned to the user about their execution.
- **Backdoor**: Launch a new JupyterLab instance open to `0.0.0.0`, with `allow-root` on a user-specified `port` with a user-specified `password`.
- **Check History**: See ipython commands recently run in the target notebook.
- **Run shell command**: Spawn a terminal, run the command, return the output, and delete the terminal.
- **List dir or get file**: List directories relative to the Jupyter directory. If you don't know, start with `/`.
- **Upload file**: Upload file from localhost to the target. Specify paths in the same format as List dir (relative to the Jupyter directory). Provide a full path including filename and extension.
- **Delete file**: Delete a file. Specify paths in the same format as List dir (relative to the Jupyter directory).