# ComfyUI workflow contract

The application uses a user-managed ComfyUI API-format workflow.
No model or checkpoint is hard-coded in Python.

## 1. Create the workflow in ComfyUI

Build and validate the image workflow in the ComfyUI UI first.

The workflow should produce one final image output for each queued prompt.
If multiple output nodes produce images, configure
`COMFYUI_OUTPUT_NODE_ID` with the final image node ID.

## 2. Export API-format JSON

Export the workflow in ComfyUI's API format and save it at the path
configured by:

```
COMFYUI_WORKFLOW_PATH=config/comfyui/workflow_api.json
```

Do not commit private/local workflow files if they contain machine-specific
paths or other information you do not want in source control.

## 3. Replace workflow inputs with placeholders

Required placeholders:

- `__PROMPT__`
- `__WIDTH__`
- `__HEIGHT__`

Optional placeholders:

- `__NEGATIVE_PROMPT__`
- `__SEED__`
- `__OUTPUT_PREFIX__`

Example fragments:

```json
{
  "positive-node": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "__PROMPT__"
    }
  },
  "negative-node": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "__NEGATIVE_PROMPT__"
    }
  },
  "latent-node": {
    "inputs": {
      "width": "__WIDTH__",
      "height": "__HEIGHT__"
    }
  },
  "sampler-node": {
    "inputs": {
      "seed": "__SEED__"
    }
  },
  "save-node": {
    "inputs": {
      "filename_prefix": "__OUTPUT_PREFIX__"
    }
  }
}
```

Keep all other workflow-specific values, including checkpoint/model names,
sampler configuration, VAE selection, steps, CFG/guidance values, and node
connections, in the exported workflow.

## Runtime behavior

The provider:

1. Loads the workflow JSON.
2. Replaces configured placeholders.
3. Creates a deterministic seed from the prompt, dimensions, model label,
   and workflow fingerprint when `__SEED__` is present.
4. Queues the graph through the local ComfyUI server.
5. Polls the workflow history until completion.
6. Downloads the final image output.
7. Validates the image with Pillow.
8. Fits it to the exact requested social-media dimensions.
9. Returns a JPEG to the existing generated-asset pipeline.

If the workflow does not contain `__NEGATIVE_PROMPT__`, a non-empty
negative prompt is appended to the positive prompt as an "Avoid" instruction
instead of being silently discarded.

## Local server configuration

Typical local configuration:

```
COMFYUI_BASE_URL=http://127.0.0.1:8188
IMAGE_GENERATION_ENABLED=true
IMAGE_PROVIDER=comfyui
```

The application does not start or install ComfyUI. ComfyUI must already be
running and reachable at `COMFYUI_BASE_URL`.
