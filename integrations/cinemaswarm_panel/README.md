# CinemaSwarm panel for ChatGPT

The panel opens a shot board with reference IDs, first-frame previews,
approvals, Wan queue controls and render status. Without production plans
it opens a read-only two-shot Echo Gate example.

Run from the repository root with Python 3.11 or later.

```bash
python -m pip install 'mcp>=1.29,<2'
CINEMASWARM_WORKSPACE=private/panel COMFYUI_URL=http://127.0.0.1:8188 \
  python -m integrations.cinemaswarm_panel.server
```

The local MCP endpoint is `http://127.0.0.1:8000/mcp`. To connect from
ChatGPT, deploy the server behind an authenticated HTTPS MCP endpoint
and follow [Connect and test your plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt).
Add the endpoint in ChatGPT developer mode and call `open_production`.
The server is a single-workspace process with no built-in authentication.
Keep it bound to loopback behind your access layer. A publicly callable
endpoint would expose production information and allow render submissions.

Put the output of `python -m scripts.wan_shots plan` in the workspace's
`plans/` directory. Add a top-level `preview` field with a PNG, JPEG, or WebP
data URL of the exact first frame uploaded to ComfyUI. Keep the plans and
frames private. The operator reviews the supplied preview. The server
keys approval to the complete plan, so any edit invalidates that approval.
Each render uses the Wan adapter's duplicate-submission ledger.

For in-panel video playback, use a browser-reachable HTTPS ComfyUI media
origin whose output URLs the reviewer is authorized to access. Configure
that URL as `COMFYUI_URL`. On loopback the panel still tracks render
status, and clips can be reviewed in ComfyUI.
