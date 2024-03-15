import inquirer
import asyncio
from vger.attack import Attack
from vger.connection import Connection
import json
import base64
import tempfile


class Enumerate:
    def __init__(self, host_or_connection, secret=None):
        if isinstance(host_or_connection, Connection):
            self.connection = host_or_connection
        else:
            self.connection = Connection(host_or_connection, secret)
        try:
            from pyds_sum.summarize import summarizer

            self.summarizer = summarizer()
        except ImportError:
            self.summarizer = None

    def enumerate(self):
        if self.connection.first_time_in_menu["enumerate"]:
            self.connection.first_time_in_menu["enumerate"] = False
            self.connection.print_with_rule(
                """
                Use your access to the jupyter server to search and learn more about the environment.

                [bold red]Run shell commands[/bold red] like ls or pwd.
                [bold red]List directories[/bold red] and [bold red]get files[/bold red] from the server.
                [bold red]See running notebooks[/bold red].
                [bold red]Find models[/bold red] and [bold red]datasets[/bold red] in the environment.
                """,
                category="Enumerate",
            )
        enumerate_menu = [
            inquirer.List(
                "option",
                "How would you like to enumerate?",
                choices=[
                    "Run shell command",
                    "List dir or get file",
                    "See running notebooks",
                    "Find models",
                    "Find datasets",
                    "Back to main menu",
                ],
            )
        ]
        answer = inquirer.prompt(enumerate_menu)
        match answer["option"]:
            case "Run shell command":
                self.run_in_shell()
                self.enumerate()
            case "List dir or get file":
                self.list_dir()
                self.enumerate()
            case "See running notebooks":
                self.list_notebooks()
                self.enumerate()
            case "Find models":
                self.find_files_runner(file_type="model")
                if len(self.connection.model_paths) > 0:
                    self.connection.print_with_rule(
                        "\n".join(self.connection.model_paths)
                    )
                self.connection.model_paths = list(set(self.connection.model_paths))
                self.enumerate()
            case "Find datasets":
                self.find_files_runner(file_type="data")
                if len(self.connection.datasets) > 0:
                    self.connection.print_with_rule("\n".join(self.connection.datasets))
                self.connection.datasets = list(set(self.connection.datasets))
                self.enumerate()
            case "Back to main menu":
                self.connection.menu.menu()

    def pick_target(self):
        """
        Select a specific notebook to target on the server (required for some operations).
        """
        session_info = dict()
        self.connection.sessions = self.connection.list_running_jpy_sessions()
        if len(self.connection.sessions) == 0:
            self.connection.print_with_rule("No running notebooks to attach to")
        else:
            for s in self.connection.sessions:
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
            self.connection.target = session_info[answer["kernel"]]
        return len(self.connection.sessions)

    def run_in_shell(self, interactive=True, code=""):
        """
        Launches a Jupyter Terminal, runs the command, and deletes the Terminal.
        """
        if interactive:
            code = [inquirer.Text("code", "What shell command would you like to run?")]
            answers = inquirer.prompt(code)
            code = answers["code"]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(Attack(self.connection).run_ephemeral_terminal(code))

    def list_notebooks(self):
        """
        List running notebooks.
        """
        self.connection.sessions = self.connection.list_running_jpy_sessions()
        if len(self.connection.sessions) > 0:
            printable_sessions = [
                f"{self.connection.jpy_sessions[s]['name']:<20} Last Active: {self.connection.jpy_sessions[s]['kernel']['last_activity']:<30}"
                for s in self.connection.jpy_sessions
            ]
            if self.summarizer:
                summaries = list()
                for s in self.connection.jpy_sessions:
                    data = self.connection.list_dir(
                        self.connection.jpy_sessions[s]["path"]
                    )["content"]
                    with tempfile.NamedTemporaryFile(
                        mode="w+", suffix=".ipynb", delete=True
                    ) as temp_file:
                        json.dump(data, temp_file)
                        temp_file.flush()
                        summaries.append(self.summarizer.summarize(temp_file.name))
                for notebook, summary in zip(printable_sessions, summaries):
                    self.connection.print_with_rule(
                        notebook + "\n" + "\N{ROBOT FACE}" + " AI Summary:\n" + summary
                    )
            else:
                self.connection.print_with_rule("\n".join(printable_sessions))
        else:
            self.connection.print_with_rule("No running notebooks")

    def list_dir(self, interactive=True, dir="/"):
        """
        List directory contents.
        Can also be used to get file contents.
        """
        if interactive:
            dir = [
                inquirer.Text(
                    "dir",
                    "What directory or file would you like to list?",
                    default="/",
                )
            ]
            answers = inquirer.prompt(dir)
            dir = answers["dir"]
        results = self.connection.list_dir(dir)
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
                    and file["name"].split(".")[-1].lower() in file_extensions
                ):
                    self.connection.print_with_rule(f"Found {file['path']}")
                    tracker.append(file["path"])
                else:
                    pass
        except KeyError:
            pass

    def find_files_runner(self, file_type="model", interactive=True, path="/"):
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
            tracker = self.connection.model_paths
        elif file_type == "data":
            file_extensions = ["csv", "json", "jsonl", "parquet", "avro"]
            tracker = self.connection.datasets
        if interactive:
            answer = [
                inquirer.Text(
                    "path",
                    "What path would you like to recursively search?",
                    default="/",
                ),
                inquirer.Checkbox(
                    "extensions",
                    "What extensions would you like to search for?",
                    choices=file_extensions,
                    default=file_extensions,
                ),
            ]
            answer = inquirer.prompt(answer)
            file_extensions = answer["extensions"]
            path = answer["path"]
        with self.connection.con.status("Searching..."):
            self.find_files(file_extensions, tracker, path)
            self.connection.print_with_rule(f"Found {len(tracker)} {file_type} files")

    def download_files(self, tracker):
        """
        Download discovered artifacts.
        """
        if len(tracker) == 0:
            self.connection.print_with_rule(
                "You need to find some artifacts first.\nTry Enumerate -> Find [artifact]"
            )
            self.enumerate()
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
