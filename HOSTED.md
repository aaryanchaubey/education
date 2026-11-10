# Running it in Hoplite (no PC needed)

The skills, Chrome, the voice and speech-to-text models, and `social-mcp` are installed in the Hoplite sandbox for this
thread. Hoplite makes the videos there and posts them with the `social-mcp` CLI:
```
social-mcp check video.mp4
social-mcp youtube-upload video.mp4 --title "..." --description "... #shorts" --tags a,b,c --category 27 --privacy private
social-mcp instagram-publish video.mp4 --caption "... #tags"
```
Every post still needs your OK in the chat first.

## Connect YouTube (once)
1. Create a YouTube channel on the Google account you want to use (youtube.com → Create a channel).
2. Do [SETUP.md](SETUP.md) step 3, items 1–4: Google Cloud project, the 2 APIs, the consent screen **In production**, and a **Desktop app** client.
3. Give Hoplite the client JSON. The safest way is a project variable named `SOCIAL_MCP_GOOGLE_CLIENT` whose value is the
   JSON file's contents. Attaching the file in chat also works, but then it's stored with the conversation.
4. Hoplite runs `social-mcp auth google --manual` and sends you a link. Open it, pick the channel and allow access.
   Your browser ends on a `http://localhost:8765/?...` page that fails to load. That's expected: copy the full address
   and paste it in the chat. It contains a one-time code that expires within minutes, and Hoplite uses it immediately.

## Connect a new Instagram account (once)
1. Create the account in the Instagram app, then switch it to a professional account: Settings → Account type and tools
   → **Switch to professional account** (Creator or Business).
2. At developers.facebook.com, open **My Apps → Create app**. Choose the use case **"Manage messaging & content on Instagram"**.
3. In the app, open **App roles → Roles → Add people → Instagram Tester**, and enter the new account's username. In Instagram, accept the invite under
   Settings → Website permissions → Apps and websites → **Tester invites**.
4. Back in the app, open **API setup with Instagram login → Generate access tokens → Add account**, log in as the new account, then copy the token.
5. Save the token as a project variable named `SOCIAL_MCP_INSTAGRAM_TOKEN`. Don't paste it in chat: it's a 60-day key to the account.
   Then tell Hoplite it's added. It checks the connection with `social-mcp status`.

With this login type, Instagram downloads the video from a link, so YouTube/Google (above) must be connected first.
The server shares the file from your Drive only while Instagram processes it.

## Limits
- The sandbox has no GPU. 2D styles (Stick Story, Inside Out, Paper Atlas) render a 35 s short in about 7–8 minutes.
  The 3D styles (Deep Dive, Night File, Tall Tale) take much longer here, so they're best rendered on a PC.
- The logins are stored in this thread's sandbox. Scheduled automations run in new threads, so they need the tokens as
  project variables (`SOCIAL_MCP_GOOGLE_TOKEN` holds the contents of `~/.config/social-mcp/google_token.json`, and
  `SOCIAL_MCP_INSTAGRAM_TOKEN`). Set these up after the first successful post.
