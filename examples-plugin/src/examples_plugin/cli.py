"""
Echo CLI Commands
=================
"""

import typer

app = typer.Typer(name="echo", help="Echo plugin commands")


@app.command()
def send(message: str):
    """Send an echo message

    Args:
        message: Message to echo
    """
    from acorn_core import Task, Acorn

    acorn = Acorn()
    acorn.load_plugins()

    task = Task(command="echo", args={"message": message})
    response = acorn.execute(task)

    if response.success:
        typer.echo(f"✓ {response.data}")
    else:
        typer.echo(f"✗ Error: {response.error.message}")


@app.command()
def test(message: str = "Hello, Echo!"):
    """Test echo command

    Args:
        message: Test message
    """
    typer.echo(f"Testing echo: {message}")
