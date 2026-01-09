from google import genai
import time

# Use the same key you have in your app.py
client = genai.Client(
    api_key="AIzaSyASTY6GxK3ub16GQZynprie8fkdctOuTho",
    http_options={'timeout': 0.0} 
)

try:
    print("⏳ Starting deep-read test (waiting up to 10 mins)...")
    # This prompt forces the AI to think longer and generate a detailed response
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents="Please provide a very long, detailed 10-paragraph essay on the history of AI."
    )
    print("✅ SUCCESS: Detailed response received!")
    print(response.text[:150] + "...") 
except Exception as e:
    print(f"❌ READ ERROR: {e}")