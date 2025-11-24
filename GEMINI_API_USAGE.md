# How to Use Gemini API Key

Quick guide for using Google Gemini API with curl and Python.

## Get Your API Key

1. Visit https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy your key (format: `AIzaSy...`)

---

## Using with Curl

### Basic Request

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
  -H 'Content-Type: application/json' \
  -H "x-goog-api-key: YOUR_API_KEY" \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Explain how AI works in a few words"
          }
        ]
      }
    ]
  }'
```

### PowerShell (Windows)

```powershell
$headers = @{
    "x-goog-api-key" = "YOUR_API_KEY"
    "Content-Type" = "application/json"
}

$body = @{
    contents = @(
        @{
            parts = @(
                @{ text = "Explain how AI works" }
            )
        }
    )
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod `
    -Uri "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" `
    -Method Post `
    -Headers $headers `
    -Body $body

# Get the response text
$response.candidates[0].content.parts[0].text
```

### With Configuration Options

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
  -H 'Content-Type: application/json' \
  -H "x-goog-api-key: YOUR_API_KEY" \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Write a story about a robot"
          }
        ]
      }
    ],
    "generationConfig": {
      "temperature": 0.7,
      "topP": 0.8,
      "topK": 40,
      "maxOutputTokens": 1024,
      "stopSequences": []
    }
  }'
```

---

## Using with Python

### Method 1: Using Official SDK (Recommended)

Install the SDK:
```bash
pip install google-generativeai
```

Basic usage:
```python
import google.generativeai as genai

# Configure with your API key
genai.configure(api_key="YOUR_API_KEY")

# Create model instance
model = genai.GenerativeModel("gemini-2.5-flash")

# Generate content
response = model.generate_content("Explain quantum computing")
print(response.text)
```

### Method 2: Using Requests (REST API)

Install requests:
```bash
pip install requests
```

Basic usage:
```python
import requests
import json

API_KEY = "YOUR_API_KEY"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

headers = {
    "x-goog-api-key": API_KEY,
    "Content-Type": "application/json"
}

data = {
    "contents": [
        {
            "parts": [
                {"text": "What is machine learning?"}
            ]
        }
    ]
}

response = requests.post(url, headers=headers, json=data)
result = response.json()

# Extract the text
print(result["candidates"][0]["content"]["parts"][0]["text"])
```

### With Configuration

```python
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")

model = genai.GenerativeModel("gemini-2.5-flash")

# Configure generation parameters
generation_config = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 40,
    "max_output_tokens": 2048,
}

response = model.generate_content(
    "Write a haiku about programming",
    generation_config=generation_config
)
print(response.text)
```

### Chat/Conversation

```python
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")

model = genai.GenerativeModel("gemini-2.5-flash")
chat = model.start_chat(history=[])

# First message
response = chat.send_message("Hello! What can you help me with?")
print(response.text)

# Continue conversation
response = chat.send_message("Tell me about Python programming")
print(response.text)

# View chat history
for message in chat.history:
    print(f"{message.role}: {message.parts[0].text}")
```

### Stream Responses

```python
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")

model = genai.GenerativeModel("gemini-2.5-flash")

# Stream the response
response = model.generate_content(
    "Write a long story about a space adventure",
    stream=True
)

for chunk in response:
    print(chunk.text, end="", flush=True)
```

---

## Response Format

The API returns JSON in this format:

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "text": "AI learns patterns from data to make predictions..."
          }
        ],
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 8,
    "candidatesTokenCount": 10,
    "totalTokenCount": 18
  }
}
```

Access the response text:
- **curl/requests**: `response["candidates"][0]["content"]["parts"][0]["text"]`
- **SDK**: `response.text`

---

## Available Models

- `gemini-2.5-flash` - Latest, fast, recommended
- `gemini-1.5-flash` - Previous version
- `gemini-1.5-pro` - More capable, slower
- `gemini-2.0-flash-exp` - Experimental

---

## Rate Limits (Free Tier)

- **15 requests per minute**
- **1,500 requests per day**
- **1 million tokens per minute**

---

## Error Handling

### Python with Requests

```python
import requests

API_KEY = "YOUR_API_KEY"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

headers = {
    "x-goog-api-key": API_KEY,
    "Content-Type": "application/json"
}

data = {
    "contents": [{"parts": [{"text": "Hello"}]}]
}

try:
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()  # Raises exception for 4xx/5xx
    result = response.json()
    print(result["candidates"][0]["content"]["parts"][0]["text"])
except requests.exceptions.HTTPError as e:
    print(f"HTTP Error: {e}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
```

### Python with SDK

```python
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel("gemini-2.5-flash")

try:
    response = model.generate_content("Hello")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
```

---

## Common Issues

### 404 Not Found
- **Wrong model name** - Use `gemini-2.5-flash` not `gemini-2.5-flash-live`
- **Invalid endpoint** - Check the URL is correct

### 400 Bad Request
- **Invalid API key** - Verify at https://aistudio.google.com/app/apikey
- **Wrong authentication** - Must use `x-goog-api-key` header

### 429 Too Many Requests
- **Rate limit exceeded** - Wait before making more requests
- Add delays between requests:
  ```python
  import time
  time.sleep(4)  # Wait 4 seconds between requests
  ```

---

## Quick Test

**Bash/Linux:**
```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
  -H 'Content-Type: application/json' \
  -H "x-goog-api-key: YOUR_API_KEY" \
  -X POST \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

**PowerShell:**
```powershell
$headers = @{ "x-goog-api-key" = "YOUR_API_KEY"; "Content-Type" = "application/json" }
$body = '{"contents":[{"parts":[{"text":"Hello"}]}]}'
Invoke-RestMethod -Uri "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" -Method Post -Headers $headers -Body $body
```

**Python:**
```python
import google.generativeai as genai
genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel("gemini-2.5-flash")
print(model.generate_content("Hello").text)
```

---

## Documentation

- Official Docs: https://ai.google.dev/gemini-api/docs
- API Reference: https://ai.google.dev/api
- Python SDK: https://pypi.org/project/google-generativeai/
- Get API Key: https://aistudio.google.com/app/apikey
