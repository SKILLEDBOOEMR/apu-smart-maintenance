import requests

url = "http://127.0.0.1:8000/analyze"

def the_correct_request():
    # Path to an image file on your laptop
    image_path = "backend/test_files/images (3).jfif"

    data = {
        "text": "Leaking in the room",
        "building": "Tower B",
        "room": "2",
        "latitude": 3.055305,
        "longitude": 101.699984,
    }

    with open(image_path, "rb") as f:
        files = {"image": ("image.jpg", f, "image/jpeg")}
        response = requests.post(url, data=data, files=files)

    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

def no_image_request():
    data = {
        "text": "Leaking in the room",
        "building": "Tower B",
        "room": "2",
        "latitude": 3.055305,
        "longitude": 101.699984,
    }

    response = requests.post(url, data=data)
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

def invalid_location_request():
    image_path = "backend/test_files/images (3).jfif"

    data = {
        "text": "Leaking in the room",
        "building": "Tower B",
        "room": "2",
        "latitude": 3.000000,  # Invalid latitude
        "longitude": 101.000000,  # Invalid longitude
    }

    with open(image_path, "rb") as f:
        files = {"image": ("image.jpg", f, "image/jpeg")}
        response = requests.post(url, data=data, files=files)

    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

def just_regular_picture_nothing_wrong():
    image_path = "backend/test_files/images (9).jfif"

    data = {
        "text": "There is a pipe leaking!",
        "building": "Tower B",
        "room": "2",
        "latitude": 3.055305,
        "longitude": 101.699984,
    }

    with open(image_path, "rb") as f:
        files = {"image": ("image.jpg", f, "image/jpeg")}
        response = requests.post(url, data=data, files=files)

    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

if __name__ == "__main__":
    print("----- Correct Request -----")
    the_correct_request()
    print("\n----- No Image Request -----")
    no_image_request()
    print("\n----- Invalid Location Request -----")
    invalid_location_request()
    print("\n----- Just Regular Picture, Nothing Wrong -----")
    just_regular_picture_nothing_wrong()