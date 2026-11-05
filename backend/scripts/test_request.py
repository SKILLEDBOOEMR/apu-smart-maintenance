import requests

url = "http://127.0.0.1:8000/analyze"

# Path to an image file on your laptop
image_path = "backend/test_files/images (3).jfif"

# Form fields matching your endpoint parameters
data = {
    "text": "Leaking in the room",
    "building": "Tower B",
    "room": "2",
    "latitude": 3.055305,
    "longitude": 101.699984,
}

# Open and attach the image file
with open(image_path, "rb") as f:
    files = {"image": ("image.jpg", f, "image/jpeg")}
    response = requests.post(url, data=data, files=files)

print("Status Code:", response.status_code)
print("Response JSON:", response.json())