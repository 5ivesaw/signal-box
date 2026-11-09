"""Stable frontend-neutral entry points for a desktop or future web job worker.
Do not expose user-supplied server filesystem paths directly over HTTP.
"""
from dataclasses import asdict
from .catalog import CATALOG
from .model import Project,Setting
from .media import Job,Cancelled
from .render import render,preview,preflight
from .analysis import analyze,apply_auto,chaos,select_all,apply_preset


def catalog():
    return [asdict(effect) for effect in CATALOG]

__all__=['Project','Setting','Job','Cancelled','catalog','render','preview','preflight',
         'analyze','apply_auto','chaos','select_all','apply_preset']
