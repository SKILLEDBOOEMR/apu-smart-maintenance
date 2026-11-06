import requests

url = "http://127.0.0.1:8000/analyze"
base_url = "http://127.0.0.1:8000"

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

def test_signup():
    test_email = "warrenwinarko@gmail.com"
    test_password = "securepassword123"
    
    # 1. Test Signup Endpoint
    print("Testing /signup...")
    signup_payload = {
        "email": test_email,
        "password": test_password,
        "full_name": "Python Test User"
    }
    
    try:
        response = requests.post(f"{base_url}/signup", json=signup_payload)
        print(f"Signup Status: {response.status_code}")
        print(f"Signup Response: {response.json()}")
    except Exception as e:
        print(f"Signup failed to connect: {e}")
        return
    
def test_login():
    test_email = "warrenwinarko@gmail.com"
    test_password = "securepassword123"

    # 2. Test Login Endpoint
    print("\nTesting /login...")
    login_payload = {
        "email": test_email,
        "password": test_password
    }
    
    try:
        response = requests.post(f"{base_url}/login", json=login_payload)
        print(f"Login Status: {response.status_code}")
        print(f"Login Response: {response.json()}")
    except Exception as e:
        print(f"Login failed to connect: {e}")

if __name__ == "__main__":
    # print("----- Correct Request -----")
    # the_correct_request()
    # print("\n----- No Image Request -----")
    # no_image_request()
    # print("\n----- Invalid Location Request -----")
    # invalid_location_request()
    # print("\n----- Just Regular Picture, Nothing Wrong -----")
    # just_regular_picture_nothing_wrong()
    print("\n----- Testing Signup -----")
    test_signup()

    print("\n----- Testing Login -----")
    test_login()
    pass