"""
Clipboard utilities for Textual app.
"""

import subprocess
from typing import Optional


class Clipboard:
    """Handle system clipboard operations."""
    
    @staticmethod
    def copy(text: str) -> bool:
        """Copy text to system clipboard."""
        try:
            # macOS
            process = subprocess.Popen(
                ['pbcopy'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(input=text.encode('utf-8'))
            return process.returncode == 0
        except FileNotFoundError:
            try:
                # Linux with xclip
                process = subprocess.Popen(
                    ['xclip', '-selection', 'clipboard'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                process.communicate(input=text.encode('utf-8'))
                return process.returncode == 0
            except FileNotFoundError:
                try:
                    # Windows
                    process = subprocess.Popen(
                        ['clip'],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    process.communicate(input=text.encode('utf-8'))
                    return process.returncode == 0
                except FileNotFoundError:
                    return False
    
    @staticmethod
    def paste() -> Optional[str]:
        """Paste text from system clipboard."""
        try:
            # macOS
            result = subprocess.run(['pbpaste'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
        except FileNotFoundError:
            try:
                # Linux with xclip
                result = subprocess.run(
                    ['xclip', '-selection', 'clipboard', '-o'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout
            except FileNotFoundError:
                try:
                    # Windows
                    result = subprocess.run(['powershell', '-Command', 'Get-Clipboard'], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        return result.stdout
                except FileNotFoundError:
                    pass
        
        return None
