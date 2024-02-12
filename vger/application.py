from vger.menu import Menu
from vger.enumerate import Enumerate
from vger.exploit import Exploit
from vger.persist import Persist
import typer

app = typer.Typer()


@app.command()
def interactive():
    """
    Interactive execution for maximum functionality
    """
    return Menu().main()


@app.command()
def terminal(host: str, secret: str, code: str):
    """
    Run a shell command on the server
    """
    return Enumerate(host, secret).run_in_shell(interactive=False, code=code)


@app.command()
def nb_list(host: str, secret: str):
    """
    List notebooks on the server
    """
    return Enumerate(host, secret).list_notebooks()


@app.command()
def file_list(host: str, secret: str, dir_path: str = "/"):
    """
    List directories or file contents
    """
    return Enumerate(host, secret).list_dir(interactive=False, dir=dir_path)


@app.command()
def find_models(host: str, secret: str, dir_path: str = "/"):
    """
    Find models based on common file extensions
    """
    return Enumerate(host, secret).find_files_runner(
        file_type="model", interactive=False, dir_path=dir_path
    )


@app.command()
def find_datasets(host: str, secret: str, dir_path: str = "/"):
    """
    Find datasets based on common file extensions
    """
    return Enumerate(host, secret).find_files_runner(
        file_type="data", interactive=False, path=dir_path
    )


@app.command()
def file_upload(host: str, secret: str, local_path: str, remote_path: str):
    """
    Upload a file to the server
    """
    return Exploit(host, secret).upload_file(
        interactive=False, in_path=local_path, out_path=remote_path
    )


@app.command()
def file_delete(host: str, secret: str, file_path: str):
    """
    Delete a file on the server
    """
    return Exploit(host, secret).delete_file(interactive=False, path=file_path)


@app.command()
def backdoor_jupyter(host: str, secret: str, port: int = 7777, new_secret: str = ""):
    """
    Launch a backdoor Jupyter server
    """
    return Persist(host, secret).jupyter_backdoor(
        interactive=False, port=port, secret=new_secret
    )


@app.command()
def nb_inject(host: str, secret: str, notebook: str, code_path: str):
    """
    Inject code into a notebook
    """
    return Exploit(host, secret, notebook).inject(
        interactive=False, payload_path=code_path
    )


@app.command()
def nb_history(host: str, secret: str, notebook: str):
    """
    Dump the history of a notebook
    """
    return Exploit(host, secret, notebook).dump_history()


@app.command()
def nb_snoop(host: str, secret: str, notebook: str, seconds: int = 60):
    """
    Snoop on a notebook for a specified duration
    """
    return Exploit(host, secret, notebook).snoop_for(interactive=False, timeout=seconds)


@app.command()
def nb_modules(host: str, secret: str, notebook: str):
    """
    List all available modules in a given notebook context
    """
    return Exploit(host, secret, notebook).list_modules()
