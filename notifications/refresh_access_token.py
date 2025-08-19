import base64
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

CLIENT_ID = "355V0WfCiJv8JrypgG"
CLIENT_SECRET = "3#!^j!YE2GI691N00g+&KGtinoiI7(JJ"
REDIRECT_URI = "http://localhost:3000"


class TickTickOAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle the OAuth redirect and capture authorization code."""
        if "?code=" in self.path:
            # Extract authorization code from redirect URL
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)

            if "code" in query_params:
                auth_code = query_params["code"][0]  # Get first element from list
                print(f"✅ Authorization code received: {auth_code}")

                # Exchange code for access token
                access_token = self.exchange_code_for_token(auth_code)

                if access_token:
                    # Save token to file for later use
                    token_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\notifications\ticktick_token.txt"
                    with open(token_path, "w") as f:
                        f.write(access_token)
                    print(f"✅ Access token saved to {token_path}")

                    # Send success response to browser
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"""
                    <html><body>
                    <h2>Authorization Successful!</h2>
                    <p>You can close this window and return to your Python script.</p>
                    <p>Access token has been saved for your farming app.</p>
                    <p><strong>Token expires in 180 days</strong></p>
                    </body></html>
                    """)
                else:
                    self.send_error(400, "Failed to get access token")
            else:
                self.send_error(400, "No authorization code found")
        else:
            self.send_error(404, "Invalid request")

    def exchange_code_for_token(self, auth_code):
        """Exchange authorization code for access token using Basic Auth."""
        try:
            # Create Basic Auth header
            credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {encoded_credentials}",
                "Accept": "application/json",
            }

            # Form-encoded data
            data = {
                "code": auth_code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
            }

            print("🔄 Exchanging authorization code for access token...")
            response = requests.post(
                "https://ticktick.com/oauth/token", data=data, headers=headers
            )

            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")
                print(f"✅ Access token obtained: {access_token[:20]}...")
                return access_token
            else:
                print(f"❌ Token exchange failed: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Error exchanging code for token: {e}")
            return None

    def log_message(self, format, *args):
        """Suppress default HTTP server logging."""
        pass


def start_oauth_flow():
    """Start the TickTick OAuth authorization flow."""

    # Build authorization URL
    auth_url = (
        f"https://ticktick.com/oauth/authorize?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI)}&"
        f"response_type=code&"
        f"scope=tasks:read%20tasks:write"
    )

    print("🚀 Starting TickTick OAuth flow...")
    print(f"📝 Client ID: {CLIENT_ID}")
    print(f"🔗 Redirect URI: {REDIRECT_URI}")
    print("🌐 Opening browser for authorization...")

    # Start local server to handle redirect
    server = HTTPServer(("localhost", 3000), TickTickOAuthHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    print("🔧 Local server started on port 3000")

    # Open browser for user authorization
    webbrowser.open(auth_url)

    print("⏳ Waiting for authorization... (authorize in your browser)")
    print(
        "💡 After authorization, the access token will be saved to 'ticktick_token.txt'"
    )
    print("📅 Token will be valid for 180 days")

    try:
        # Keep server running until user authorization is complete
        timeout_counter = 0
        while timeout_counter < 300:  # 5 minute timeout
            time.sleep(1)
            timeout_counter += 1

            # Check if token file was created (authorization complete)
            try:
                with open("ticktick_token.txt", "r") as f:
                    token = f.read().strip()
                    if token:
                        print("🎉 OAuth flow completed successfully!")
                        print("📁 Token saved to: ticktick_token.txt")
                        print(f"🔑 Token: {token[:30]}...")
                        server.shutdown()
                        return True
            except FileNotFoundError:
                continue

        print("⏰ Timeout: Authorization not completed within 5 minutes")
        server.shutdown()
        return False

    except KeyboardInterrupt:
        print("\n⏹️ OAuth flow cancelled by user")
        server.shutdown()
        return False


def test_token():
    """Test if the saved token works by making a simple API call."""
    try:
        with open("ticktick_token.txt", "r") as f:
            token = f.read().strip()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Test API call to get user profile
        response = requests.get(
            "https://api.ticktick.com/open/v1/user/profile", headers=headers
        )

        if response.status_code == 200:
            user_data = response.json()
            print("✅ Token test successful!")
            print(f"👤 Logged in as: {user_data.get('username', 'Unknown')}")
            return True
        else:
            print(f"❌ Token test failed: {response.status_code}")
            return False

    except FileNotFoundError:
        print("❌ No token file found. Run OAuth flow first.")
        return False
    except Exception as e:
        print(f"❌ Token test error: {e}")
        return False


if __name__ == "__main__":
    print("🎯 TickTick OAuth Setup for CS2 Farm Manager")
    print("=" * 50)

    # Check if we already have a token
    try:
        with open("ticktick_token.txt", "r") as f:
            existing_token = f.read().strip()
            if existing_token:
                print("✅ Existing access token found!")
                print(f"Token: {existing_token[:20]}...")

                # Test if token still works
                if test_token():
                    print("🔄 Token is valid. No need to re-authenticate.")
                    print("You're ready to use the farming script!")
                    exit()
                else:
                    print("🔄 Token expired or invalid. Getting new token...")
    except FileNotFoundError:
        print("📄 No existing token found. Starting OAuth flow...")

    print("\n📋 OAuth Setup Requirements:")
    print("   1. ✅ App registered with TickTick")
    print("   2. ✅ Redirect URI set to: http://localhost:3000")
    print("   3. ✅ Client credentials configured")

    print("\n🚦 Starting OAuth authorization...")
    success = start_oauth_flow()

    if success:
        print("\n🎉 Setup Complete!")
        print("✅ TickTick OAuth token saved successfully")
        print("🔄 Token valid for 180 days")
        print("📝 You can now run your farming script")

        # Test the token
        test_token()
    else:
        print("\n❌ OAuth setup failed")
        print("Please try running the script again")
