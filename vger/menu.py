from vger.connection import Connection
import inquirer
from vger.enumerate import Enumerate
from vger.exploit import Exploit
from vger.persist import Persist
from typing import List, Dict


class Menu:
    def __init__(self, connection: Connection = Connection()):
        self.server: str = None
        self.secret: str = None
        self.sessions: List[str] = list()
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
        self.connection.menu = self
        match answer["option"]:
            case "Reset":
                self.__init__()
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
