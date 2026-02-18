"""Browser-based authentication manager for Membria."""

import asyncio
import hashlib
import os
import secrets
import base64
import webbrowser
from typing import Optional
import keyring
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn
from rich.console import Console

console = Console()

class AuthManager:
    """Manages OAuth2 + PKCE flow and secure token storage."""
    
    SERVICE_NAME = "membria"
    TOKEN_KEY = "auth_token"
    
    def __init__(self, client_id: str = "membria-cli-ext"):
        self.client_id = client_id
        self.code_verifier = ""
        self.code_challenge = ""
        self.state = ""
        self.auth_url_base = "https://auth.membria.ai/login" # Mock URL for now
        
    def _generate_pkce(self):
        """Generate PKCE verifier and challenge."""
        self.code_verifier = secrets.token_urlsafe(64)
        hashed = hashlib.sha256(self.code_verifier.encode('ascii')).digest()
        self.code_challenge = base64.urlsafe_b64encode(hashed).decode('ascii').replace('=', '')
        self.state = secrets.token_urlsafe(16)

    def get_token(self) -> Optional[str]:
        """Retrieve token from secure system keyring."""
        return keyring.get_password(self.SERVICE_NAME, self.TOKEN_KEY)

    def save_token(self, token: str):
        """Save token to secure system keyring."""
        keyring.set_password(self.SERVICE_NAME, self.TOKEN_KEY, token)

    def logout(self):
        """Remove token from keyring."""
        try:
            keyring.delete_password(self.SERVICE_NAME, self.TOKEN_KEY)
            console.print("[green]✓ Successfully logged out.[/green]")
        except keyring.errors.PasswordDeleteError:
            pass

    async def login(self) -> bool:
        """Execute the browser-based login flow."""
        self._generate_pkce()
        
        # Start local callback server
        app = FastAPI()
        loop = asyncio.get_event_loop()
        stop_event = asyncio.Event()
        captured_token = [None]

        @app.get("/callback")
        async def callback(code: str, state: str):
            if state != self.state:
                return HTMLResponse("Invalid state", status_code=400)
            
            # In a real app, we'd exchange 'code' for a real token here.
            # Mocking token generation for now
            mock_token = f"membria_plus_{secrets.token_hex(16)}"
            captured_token[0] = mock_token
            
            stop_event.set()
            return HTMLResponse("""
                <html>
                    <body style="font-family: sans-serif; text-align: center; padding-top: 50px; background: #0d1117; color: white;">
                        <h1 style="color: #58a6ff;">✓ Authenticated</h1>
                        <p>You can close this window and return to the terminal.</p>
                    </body>
                </html>
            """)

        config = uvicorn.Config(app, host="127.0.0.1", port=5678, log_level="error")
        server = uvicorn.Server(config)

        # Launch server in background
        server_task = loop.create_task(server.serve())
        
        # Construct login URL
        auth_url = (
            f"{self.auth_url_base}?response_type=code&client_id={self.client_id}"
            f"&code_challenge={self.code_challenge}&code_challenge_method=S256"
            f"&state={self.state}&redirect_uri=http://127.0.0.1:5678/callback"
        )
        
        console.print(f"[bold cyan]🚀 Opening browser for secure login...[/bold cyan]")
        webbrowser.open(auth_url)
        
        # Wait for the callback to trigger or timeout
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60)
            if captured_token[0]:
                self.save_token(captured_token[0])
                console.print("[green]✓ Login successful! Token secured in system keyring.[/green]")
                return True
        except asyncio.TimeoutError:
            console.print("[red]✗ Login timed out. Please try again.[/red]")
        finally:
            server.should_exit = True
            await server_task
            
        return False
