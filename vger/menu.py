from vger.connection import Connection
import inquirer
from vger.enumerate import EnumerateMixin
from vger.exploit import ExploitMixin
from vger.persist import PersistMixin
from typing import List, Dict
from multiprocessing import Process


class Menu(EnumerateMixin, ExploitMixin, PersistMixin):
    def __init__(self):
        self.server: str = None
        self.secret: str = None
        self.sessions: List[str] = list()
        self.target: str = None
        self.connection: Connection = Connection()
        self.model_paths: List[str] = list()
        self.datasets: List[str] = list()
        self.jobs: Dict[str, Process] = dict()
        self.first_time_in_menu: Dict[str, bool] = {
            "enumerate": True,
            "exploit": True,
            "exploit_attack": True,
            "persist": True,
        }
        self.connection.print_with_rule(
            """
             .                      ,;           
             EK,        .Gt       f#i j.         
             .j;       j#W:     .E#t  EW,        
  t      .DD.        ;K#f      i#W,   E##j       
  EK:   ,WK.       .G#D.      L#D.    E###D.     
  E#t  i#D        j#K;      :K#Wfff;  E#jG#W;    
  E#t j#f       ,K#f   ,GD; i##WLLLLt E#t t##f   
  E#tL#i         j#Wi   E#t  .E#L     E#t  :K#E: 
  E#WW,           .G#D: E#t    f#E:   E#KDDDD###i
  E#K:              ,K#fK#t     ,WW;  E#f,t#Wi,,,
  ED.                 j###t      .D#; E#t  ;#W:  
  t                    .G#t        tt DWi   ,KK: 
                         ;;                      
              """,
            category="V'ger",
        )

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
                    "Export output",
                    "Quit",
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
            case "Export output":
                self.export_console()
                self.menu()
            case "Quit":
                for k, v in self.jobs.items():
                    v.kill()
                exit()

    def enumerate(self):
        if self.first_time_in_menu["enumerate"]:
            self.first_time_in_menu["enumerate"] = False
            self.connection.print_with_rule(
                """
                Use your access to the jupyter server to search and learn more about the environment.

                [bold red]Run shell commands[/bold red] like ls or pwd.
                [bold red]List directories[/bold red] and [bold red]get files[/bold red] from the server.
                [bold red]See running notebooks[/bold red] and [bold red]snoop on[/bold red] activity.
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
                    "Snoop on notebook session",
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
            case "Snoop on notebook session":
                self.snoop_for()
                self.enumerate()
            case "Find models":
                self.find_files_runner(file_type="model")
                if len(self.model_paths) > 0:
                    self.connection.print_with_rule("\n".join(self.model_paths))
                self.model_paths = list(set(self.model_paths))
                self.enumerate()
            case "Find datasets":
                self.find_files_runner(file_type="data")
                if len(self.datasets) > 0:
                    self.connection.print_with_rule("\n".join(self.datasets))
                self.datasets = list(set(self.datasets))
                self.enumerate()
            case "Back to main menu":
                self.menu()

    def exploit(self):
        if self.first_time_in_menu["exploit"]:
            self.first_time_in_menu["exploit"] = False
            self.connection.print_with_rule(
                """
                Expand your access into the jupyter server and start interacting with notebooks.
                [bold red]Run shell commands[/bold red] to change server state.
                [bold red]Upload[/bold red] and [bold red]Delete[/bold red] files to exfiltrate valuable artifacts or upload payloads.
                [bold red]Attack running notebooks[/bold red] to inject code or snoop on sessions.
                [bold red]Download models[/bold red] and [bold red]datasets[/bold red] to your local host.
                """,
                category="Exploit",
            )
        exploit_menu = [
            inquirer.List(
                "option",
                "How would you like to exploit?",
                choices=[
                    "Run shell command",
                    "Upload file",
                    "Delete file",
                    "Attack running notebook",
                    "Download models",
                    "Download datasets",
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
                    self.connection.print_with_rule("Returning to exploit menu")
                    self.exploit()
            case "Download models":
                self.download_files(self.model_paths)
                self.exploit()
            case "Download datasets":
                self.download_files(self.datasets)
                self.exploit()
            case "Back to main menu":
                self.menu()

    def exploit_attack(self):
        if self.first_time_in_menu["exploit_attack"]:
            self.first_time_in_menu["exploit_attack"] = False
            self.connection.print_with_rule(
                """
                Focus on a specific notebook session.
                [bold red]Show history[/bold red] of commands run in the notebook.
                [bold red]List imported modules[/bold red] in the notebook. Useful for identifying what imports you have available.
                [bold red]Inject code[/bold red] into the notebook runtime (just as if the user ran it). Great for poisoning.
                [bold red]Snoop[/bold red] on the notebook session to see what the user is doing.
                [bold red]Start and kill recurring jobs[/bold red] to inject code on your schedule.
                """,
                category="Exploit Notebook",
            )
        attack_menu = [
            inquirer.List(
                "option",
                "Show history or inject code?",
                choices=[
                    "Show history",
                    "List imported modules",
                    "Inject code",
                    "Snoop",
                    "Recurring job",
                    "Kill job",
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
            case "List imported modules":
                self.list_modules()
                self.exploit_attack()
            case "Inject code":
                self.inject()
                self.exploit_attack()
            case "Switch notebook":
                self.switch_target_notebook()
                self.exploit_attack()
            case "Snoop":
                self.snoop_for()
                self.exploit_attack()
            case "Recurring job":
                self.variable_stomp()
                self.exploit_attack()
            case "Kill job":
                if len(self.jobs) > 0:
                    self.kill_job()
                else:
                    self.connection.print_with_rule("No running jobs to kill")
                self.exploit_attack()
            case "Back to main menu":
                self.menu()

    def persist(self):
        if self.first_time_in_menu["persist"]:
            self.first_time_in_menu["persist"] = False
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

    def main(self):
        self.login()
        self.menu()


def cli():
    m = Menu()
    m.main()


if __name__ == "__main__":
    m = Menu()
    m.main()
