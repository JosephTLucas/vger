from vger.connection import Connection
import inquirer
from vger.enumerate import Enumerate
from vger.exploit import Exploit
from vger.persist import Persist
from typing import List, Dict
from vger.auth import TokenAuthStrategy, JupyterHubAuthStrategy, SageMakerIAMAuthStrategy, AuthStrategy


class Menu:
    def __init__(self, connection: Connection = Connection()):
        self.server: str = None
        self.connection: Connection = connection
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
        platform_question = [
            inquirer.List(
                "platform",
                message="Select the target platform:",
                choices=["JupyterLab (Token/Password)", "JupyterHub", "SageMaker"],
                default="JupyterLab (Token/Password)",
            )
        ]
        platform_answer = inquirer.prompt(platform_question)
        selected_platform = platform_answer["platform"]

        auth_strategy: AuthStrategy = None
        server_url_prompt = "What is the server hostname? (e.g., http://localhost:8888/)"

        if selected_platform == "JupyterLab (Token/Password)":
            login_questions = [
                inquirer.Text("server", message=server_url_prompt, default="http://localhost:8888/"),
                inquirer.Text("secret", message="What is the secret token or password?"),
            ]
            answers = inquirer.prompt(login_questions)
            self.server = answers["server"].strip()
            if self.server and self.server[-1] != "/": self.server += "/"
            auth_strategy = TokenAuthStrategy(answers["secret"])

        elif selected_platform == "JupyterHub":
            hub_questions = [
                inquirer.Text("hub_url", message="What is the JupyterHub URL? (e.g., https://myhub.com)", default="https://localhost:8000"),
                inquirer.Text("hub_token", message="What is your JupyterHub API token? (Leave blank for user/pass - NOT IMPLEMENTED YET)"),
            ]
            answers = inquirer.prompt(hub_questions)
            self.server = answers["hub_url"].strip()
            if self.server and self.server[-1] != "/": self.server += "/"
            auth_strategy = JupyterHubAuthStrategy(
                hub_url=self.server, 
                api_token=answers["hub_token"], 
                console_print_callback=self.connection.print_with_rule
            )

        elif selected_platform == "SageMaker":
            sagemaker_questions = [
                inquirer.Text("sagemaker_url", message="What is the SageMaker Notebook/Studio URL or App ARN?", default=""),
                inquirer.Text("aws_profile", message="AWS CLI profile (optional, default credentials otherwise):", default=""),
                inquirer.Text("aws_region", message="AWS Region (e.g., us-east-1):", default=""),
            ]
            answers = inquirer.prompt(sagemaker_questions)
            self.server = answers["sagemaker_url"].strip()
            auth_strategy = SageMakerIAMAuthStrategy(
                profile_name=answers["aws_profile"] or None,
                region_name=answers["aws_region"] or None,
                sagemaker_url_or_arn=self.server,
                console_print_callback=self.connection.print_with_rule
            )

        if not self.server or not auth_strategy:
            self.connection.print_with_rule("Login failed. Server URL or authentication details missing.", category="Error")
            self.login()
            return

        try:
            self.connection.update_connection_details(self.server, auth_strategy)
            user_sessions = self.connection.list_running_jpy_sessions()
            if selected_platform == "JupyterLab (Token/Password)" and not user_sessions and not self.connection.jpy_sessions:
                pass
            elif not user_sessions and not self.connection.jpy_sessions and (selected_platform == "JupyterHub" or selected_platform == "SageMaker"):
                if not self.connection.url or (not self.connection.jpy_sessions and selected_platform != "JupyterLab (Token/Password)"):
                    self.connection.print_with_rule("Failed to establish a connection or list sessions. Please check details and logs.", category="Error")
                    self.login()
                    return

        except Exception as e:
            self.connection.print_with_rule(f"Connection error: {e}. Please try again.", category="Error")
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
        if not self.connection.auth_strategy:
            self.connection.print_with_rule("Connection not configured. Please login first.", category="Error")
            self.main()
            return

        self.connection.menu = self
        match answer["option"]:
            case "Reset":
            self.connection = Connection()
            self.main()
            case "Enumerate":
                Enumerate(self.connection).enumerate()
                self.menu()
            case "Exploit":
                Exploit(self.connection).exploit()
                self.menu()
            case "Persist":
                Persist(self.connection).persist()
                self.menu()
            case "Export output":
                Persist(self.connection).export_console()
                self.menu()
            case "Quit":
                for k, v in self.connection.jobs.items():
                    v.kill()
                exit()

    def main(self):
        self.login()
        self.menu()


if __name__ == "__main__":
    Menu().main()
