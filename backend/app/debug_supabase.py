import os
from dotenv import load_dotenv
from supabase import create_client

# 1. Force load .env
load_dotenv(override=True)

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

print("--- CONFIG CHECK ---")
print("URL:", url)
print(
    "Key starts with:", key[:10] if key else "MISSING"
)  # Should start with 'eyJ...' (service_role)

# 2. Initialize client
supabase = create_client(url, key)

print("\n--- TESTING CONNECTION ---")
try:
  # Explicitly target the public schema and table
  res = supabase.table("map_coordinates").select("*").execute()
  print("Success! Data received:")
  print(res.data)
except Exception as e:
  print("ERROR caught during query:", e)