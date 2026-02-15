#!/usr/bin/env python3
"""SpecGuard CLI — API Schema Breaking Change Detection."""
import json
import typer
from rich.console import Console
from rich.table import Table
from specguard import load_spec, diff_specs, lint_spec, score_spec, has_breaking

app = typer.Typer(name="specguard",
                  help="Shield API schema breaking changes & enforce design rules")
console = Console()
COLORS = {'breaking': 'red', 'deprecation': 'yellow', 'compatible': 'green',
          'error': 'red', 'warning': 'yellow'}


@app.command()
def diff(old: str = typer.Argument(..., help="Old spec path"),
        new: str = typer.Argument(..., help="New spec path"),
        block: bool = typer.Option(True, help="Exit 1 on breaking changes"),
        output: str = typer.Option("table", help="table|json")):
    """Detect breaking changes between two API specs."""
    changes = diff_specs(load_spec(old), load_spec(new))
    if output == "json":
        rows = [dict(zip(('severity', 'type', 'location', 'detail'), c))
                for c in changes]
        typer.echo(json.dumps(rows, indent=2))
    else:
        if not changes:
            console.print("[green]No changes detected[/green]")
            return
        tbl = Table(title="SpecGuard Diff Report")
        for col in ("Severity", "Type", "Location", "Detail"):
            tbl.add_column(col)
        for sev, typ, loc, det in changes:
            tbl.add_row(f"[{COLORS.get(sev, 'white')}]{sev}[/]",
                        typ, loc, det)
        console.print(tbl)
        b = sum(1 for s, *_ in changes if s == 'breaking')
        d = sum(1 for s, *_ in changes if s == 'deprecation')
        g = sum(1 for s, *_ in changes if s == 'compatible')
        console.print(f"\n  {b} breaking | {d} deprecation | {g} compatible")
    if block and has_breaking(changes):
        console.print("\n[bold red]BLOCKED: breaking changes detected[/]")
        raise typer.Exit(1)


@app.command()
def lint(spec_path: str = typer.Argument(..., help="Spec path"),
        output: str = typer.Option("table", help="table|json")):
    """Enforce API design rules."""
    issues = lint_spec(load_spec(spec_path))
    if output == "json":
        rows = [dict(zip(('level', 'rule', 'location', 'detail'), i))
                for i in issues]
        typer.echo(json.dumps(rows, indent=2))
    else:
        if not issues:
            console.print("[green]All design rules pass[/green]")
            return
        tbl = Table(title="SpecGuard Lint Report")
        for col in ("Level", "Rule", "Location", "Detail"):
            tbl.add_column(col)
        for lev, rule, loc, det in issues:
            tbl.add_row(f"[{COLORS.get(lev, 'white')}]{lev}[/]",
                        rule, loc, det)
        console.print(tbl)
    if any(l == 'error' for l, *_ in issues):
        raise typer.Exit(1)


@app.command()
def score(spec_path: str = typer.Argument(..., help="Spec path")):
    """Calculate API design consistency score (0-100)."""
    s = score_spec(load_spec(spec_path))
    color = "green" if s >= 80 else "yellow" if s >= 60 else "red"
    console.print(f"API Design Score: [{color}]{s}/100[/]")
    if s < 60:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
