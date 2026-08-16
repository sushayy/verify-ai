"""Puts the service root on sys.path so tests import agents/, services/, models."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
