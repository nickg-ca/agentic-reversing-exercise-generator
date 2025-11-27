import os
import json
import urllib.request
import urllib.error
import subprocess
import sys

def generate_content(api_key, conversation_history):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    # Construct the payload from conversation history
    # The API expects "contents": [{ "role": "user"|"model", "parts": [{ "text": "..." }] }]
    payload = {
        "contents": conversation_history
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body)
    except urllib.error.HTTPError as e:
        print(f"Error calling Gemini API: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

def extract_code(text):
    # Simple extraction: look for ```c ... ``` or just take the whole text if no blocks
    if "```c" in text:
        start = text.find("```c") + 4
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    elif "```" in text: # Fallback for unspecified language
        start = text.find("```") + 3
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    return text.strip()

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)

    # Initial prompt
    prompt = "Create a simple C program for a reverse engineering exercise. Do not explain. Output only code."
    
    conversation_history = [
        {"role": "user", "parts": [{"text": prompt}]}
    ]

    max_retries = 5
    for attempt in range(max_retries):
        print(f"Attempt {attempt + 1}/{max_retries}: Generating code...")
        
        response_json = generate_content(api_key, conversation_history)
        
        try:
            model_response_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            print("Error: Unexpected response format from API.")
            print(json.dumps(response_json, indent=2))
            sys.exit(1)

        # Add model response to history
        conversation_history.append({"role": "model", "parts": [{"text": model_response_text}]})
        
        c_code = extract_code(model_response_text)
        
        # Write to file
        with open("out.c", "w") as f:
            f.write(c_code)
        
        print("Compiling...")
        # Try to compile
        # Using clang as default, fallback to gcc if needed, or just try one. User mentioned 'compiled to "out"'
        compiler = "clang" # Default on macOS
        compile_cmd = [compiler, "out.c", "-o", "out"]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Success! compiled to 'out'")
            break
        else:
            print("Compilation failed.")
            error_message = result.stderr
            print(f"Errors:\n{error_message}")
            
            # Feed error back to model
            feedback_prompt = f"The code failed to compile with the following error:\n{error_message}\nPlease fix the code. Output only the fixed C code."
            conversation_history.append({"role": "user", "parts": [{"text": feedback_prompt}]})
    else:
        print("Failed to generate valid code after maximum retries.")
        sys.exit(1)

if __name__ == "__main__":
    main()
